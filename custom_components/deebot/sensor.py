"""Sensor module."""
import logging
from enum import Enum
from typing import Any, Dict, Optional, Union

from deebotozmo.commands.life_span import LifeSpan
from deebotozmo.event_emitter import EventListener
from deebotozmo.events import (
    CleanLogEvent,
    ErrorEvent,
    LifeSpanEvent,
    StatsEvent,
    StatusEvent,
    TotalStatsEvent,
    WaterInfoEvent,
)
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DESCRIPTION, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LAST_ERROR
from .helpers import get_device_info
from .hub import DeebotHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub: DeebotHub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacuum_bots:
        # General
        new_devices.append(DeebotLastCleanImageSensor(vacbot))
        new_devices.append(DeebotWaterLevelSensor(vacbot))
        new_devices.append(DeebotLastErrorSensor(vacbot))

        # Components
        new_devices.append(DeebotComponentSensor(vacbot, LifeSpan.BRUSH))
        new_devices.append(DeebotComponentSensor(vacbot, LifeSpan.SIDE_BRUSH))
        new_devices.append(DeebotComponentSensor(vacbot, LifeSpan.FILTER))

        # Stats
        new_devices.append(
            DeebotStatsSensor(
                vacbot, StatsType.CLEANING, "area", "mdi:floor-plan", "m²"
            )
        )
        new_devices.append(
            DeebotStatsSensor(
                vacbot, StatsType.CLEANING, "time", "mdi:timer-outline", "min"
            )
        )
        new_devices.append(
            DeebotStatsSensor(vacbot, StatsType.CLEANING, "type", "mdi:cog")
        )
        new_devices.append(DeebotStatsSensor(vacbot, StatsType.CLEANING, "cid"))
        new_devices.append(DeebotStatsSensor(vacbot, StatsType.CLEANING, "start"))

        # TotalStats
        new_devices.append(
            DeebotStatsSensor(vacbot, StatsType.TOTAL, "area", "mdi:floor-plan", "m²")
        )
        new_devices.append(
            DeebotStatsSensor(vacbot, StatsType.TOTAL, "time", "mdi:timer-outline", "h")
        )
        new_devices.append(
            DeebotStatsSensor(vacbot, StatsType.TOTAL, "cleanings", "mdi:counter")
        )

    if new_devices:
        async_add_entities(new_devices)


class DeebotBaseSensor(SensorEntity):  # type: ignore
    """Deebot base sensor."""

    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the Sensor."""
        self._vacuum_bot: VacuumBot = vacuum_bot

        if self._vacuum_bot.device_info.nick is not None:
            name: str = self._vacuum_bot.device_info.nick
        else:
            # In case there is no nickname defined, use the device id
            name = self._vacuum_bot.device_info.did

        self._attr_name = f"{name}_{device_id}"
        self._attr_unique_id = f"{self._vacuum_bot.device_info.did}_{device_id}"

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return device specific attributes."""
        return get_device_info(self._vacuum_bot)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: StatusEvent) -> None:
            if not event.available:
                self._attr_native_value = STATE_UNKNOWN
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.status.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotLastCleanImageSensor(DeebotBaseSensor):
    """Deebot last clean image sensor."""

    _attr_icon = "mdi:image-search"

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        super().__init__(vacuum_bot, "last_clean_image")

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: CleanLogEvent) -> None:
            if event.logs:
                self._attr_native_value = event.logs[0].image_url
            else:
                self._attr_native_value = STATE_UNKNOWN
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.clean_logs.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotWaterLevelSensor(DeebotBaseSensor):
    """Deebot water level sensor."""

    _attr_icon = "mdi:water"

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        super().__init__(vacuum_bot, "water_level")

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: WaterInfoEvent) -> None:
            if event.amount:
                self._attr_native_value = event.amount
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.water_info.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotComponentSensor(DeebotBaseSensor):
    """Deebot component sensor."""

    _attr_native_unit_of_measurement = "%"

    def __init__(self, vacuum_bot: VacuumBot, component: LifeSpan):
        """Initialize the Sensor."""
        device_id = component.value
        super().__init__(vacuum_bot, device_id)
        self._attr_icon = (
            "mdi:air-filter" if component == LifeSpan.FILTER else "mdi:broom"
        )
        self._id: str = device_id

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: LifeSpanEvent) -> None:
            value = event.get(self._id, None)
            if value:
                self._attr_native_value = value
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.lifespan.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class StatsType(str, Enum):
    """Different stats type."""

    CLEANING = "stats"
    TOTAL = "total_stats"


class DeebotStatsSensor(DeebotBaseSensor):
    """Deebot stats sensor."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        vacuum_bot: VacuumBot,
        stats_type: StatsType,
        attribute: str,
        icon: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
    ):
        """Initialize the Sensor."""
        prefix = "stats"
        if stats_type == StatsType.TOTAL:
            prefix += "_total"

        super().__init__(vacuum_bot, f"{prefix}_{attribute}")
        self._stats_type = stats_type
        self._attribute = attribute
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit_of_measurement

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: Union[StatsEvent, TotalStatsEvent]) -> None:
            if hasattr(event, self._attribute):
                value = getattr(event, self._attribute)

                if value is None:
                    return

                if self._attribute == "time":
                    if self._attr_native_unit_of_measurement == "h":
                        self._attr_native_value = round(value / 3600)
                    else:
                        self._attr_native_value = round(value / 60)
                else:
                    self._attr_native_value = value

                self.async_write_ha_state()

        listener: EventListener = getattr(
            self._vacuum_bot.events, self._stats_type.value
        ).subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotLastErrorSensor(DeebotBaseSensor):
    """Deebot last error sensor."""

    _attr_icon = "mdi:alert-circle"

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        super().__init__(vacuum_bot, LAST_ERROR)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: ErrorEvent) -> None:
            self._attr_native_value = event.code
            self._attr_extra_state_attributes = {CONF_DESCRIPTION: event.description}
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.error.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)
