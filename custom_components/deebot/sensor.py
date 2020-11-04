"""Support for Deebot Sensor."""
from typing import Optional

from deebotozmo import *
from homeassistant.const import (STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity

from . import HUB as hub

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
)

STATE_CODE_TO_STATE = {
    'STATE_IDLE': STATE_IDLE,
    'STATE_CLEANING': STATE_CLEANING,
    'STATE_RETURNING': STATE_RETURNING,
    'STATE_DOCKED': STATE_DOCKED,
    'STATE_ERROR': STATE_ERROR,
    'STATE_PAUSED': STATE_PAUSED,
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Deebot sensor."""
    hub.update()

    for vacbot in hub.vacbots:
        # General
        add_devices([DeebotLastCleanImageSensor(vacbot, "last_clean_image")], True)
        add_devices([DeebotWaterLevelSensor(vacbot, "water_level")], True)

        # Components
        add_devices([DeebotComponentSensor(vacbot, COMPONENT_MAIN_BRUSH)], True)
        add_devices([DeebotComponentSensor(vacbot, COMPONENT_SIDE_BRUSH)], True)
        add_devices([DeebotComponentSensor(vacbot, COMPONENT_FILTER)], True)

        # Stats
        add_devices([DeebotStatsSensor(vacbot, "stats_area")], True)
        add_devices([DeebotStatsSensor(vacbot, "stats_time")], True)
        add_devices([DeebotStatsSensor(vacbot, "stats_type")], True)

        # Rooms
        typeRooms = vacbot.getTypeRooms()

        for v in typeRooms:
            _LOGGER.debug("New room type found: " + typeRooms[v])
            add_devices([DeebotRoomSensor(vacbot, v, typeRooms[v])], True)


class DeebotLastCleanImageSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_last_clean_image"

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        if self._vacbot.last_clean_image is not None:
            return self._vacbot.last_clean_image

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return "mdi:image-search"


class DeebotWaterLevelSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_water_level"

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""

        if self._vacbot.water_level is not None:
            return self._vacbot.water_level

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return "mdi:water"


class DeebotComponentSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_" + device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return '%'

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""

        for key, val in self._vacbot.components.items():
            if key == self._id:
                return int(val)

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        if self._id == COMPONENT_MAIN_BRUSH or self._id == COMPONENT_SIDE_BRUSH:
            return "mdi:broom"
        elif self._id == COMPONENT_FILTER:
            return "mdi:air-filter"


class DeebotStatsSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_" + device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._id == 'stats_area':
            return "mq"
        elif self._id == 'stats_time':
            return "min"

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        
        if self._id == 'stats_area' and self._vacbot.stats_area is not None:
            return int(self._vacbot.stats_area)
        elif self._id == 'stats_time'  and self._vacbot.stats_time is not None:
            return int(self._vacbot.stats_time/60)
        elif self._id == 'stats_type':
            return self._vacbot.stats_type
        else:
            return STATE_UNKNOWN

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        if self._id == 'stats_area':
            return "mdi:floor-plan"
        elif self._id == 'stats_time':
            return "mdi:timer-outline"
        elif self._id == 'stats_type':
            return "mdi:cog"

class DeebotRoomSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, roomId, roomDesc):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = roomId
        self._desc = roomDesc

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_" + roomDesc

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        room = None

        for v in self._vacbot.getSavedRooms():
            if v['subtype'] == self._desc:
                if room is None:
                    room = v['id']
                else:
                    room = room + "," + v['id']

        return room