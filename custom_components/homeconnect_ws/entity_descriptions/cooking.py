"""Description for Cooking Entities."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.const import UnitOfTime

from .descriptions_definitions import (
    HCSensorEntityDescription,
    _EntityDescriptionsType,
)

COOKING_ENTITY_DESCRIPTIONS: _EntityDescriptionsType = {
    "sensor": [
        HCSensorEntityDescription(
            key="sensor_interval_time_off",
            entity="Cooking.Hood.Setting.IntervalTimeOff",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
        ),
        HCSensorEntityDescription(
            key="sensor_interval_time_on",
            entity="Cooking.Hood.Setting.IntervalTimeOn",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
        ),
        HCSensorEntityDescription(
            key="sensor_delayed_shutoff_time",
            entity="Cooking.Hood.Setting.DelayedShutOffTime",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
        ),
    ]
}
