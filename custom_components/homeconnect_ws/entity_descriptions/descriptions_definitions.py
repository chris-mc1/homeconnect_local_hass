"""Definitions for Entity Description."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.fan import FanEntityDescription
from homeassistant.components.light import LightEntityDescription
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.helpers.entity import EntityDescription
from homeconnect_websocket import HomeAppliance
from homeconnect_websocket.entities import Access

if TYPE_CHECKING:
    from homeassistant.helpers.typing import StateType
    from homeconnect_websocket.entities import Entity as HcEntity


class ExtraAttributeDict(TypedDict):
    """Dict for extra Attributes."""

    name: str
    entity: str
    value_fn: NotRequired[Callable[[HcEntity], StateType]]


class HCEntityDescription(EntityDescription, frozen_or_thawed=True):
    """Description for Base Entity."""

    entity: str | None = None
    entities: list[str] | None = None
    available_access: tuple[Access] | None = None
    extra_attributes: list[ExtraAttributeDict] = None


class HCSelectEntityDescription(
    HCEntityDescription, SelectEntityDescription, frozen_or_thawed=True
):
    """Description for Select Entity."""

    available_access: tuple[Access] = (Access.READ_WRITE, Access.WRITE_ONLY)
    has_state_translation: bool = False
    mapping: dict[str, str] = None
    # Program select: do not select another program while a program is running, for appliances
    # of these brands (in capitals, as the appliance reports them). Gaggenau ovens accept the
    # selection while a program runs, but ignore it until the program has ended.
    block_change_while_running_for_brands: set[str] | None = None
    # Program select: show the active program (when there is one) instead of the selected
    # program, for appliances of these brands. A Gaggenau oven changes the active program
    # when it is operated on the oven itself, but keeps the program that was selected before.
    prefer_active_program_for_brands: set[str] | None = None


class HCSwitchEntityDescription(
    HCEntityDescription, SwitchEntityDescription, frozen_or_thawed=True
):
    """Description for Switch Entity."""

    value_mapping: tuple[str, str] | None = None
    available_access: tuple[Access] = (Access.READ_WRITE, Access.WRITE_ONLY)


class HCSensorEntityDescription(
    HCEntityDescription, SensorEntityDescription, frozen_or_thawed=True
):
    """Description for Sensor Entity."""

    available_access: tuple[Access] = (Access.READ, Access.READ_WRITE)
    has_state_translation: bool = False
    mapping: dict[str, str] = None


class HCBinarySensorEntityDescription(
    HCEntityDescription,
    BinarySensorEntityDescription,
    frozen_or_thawed=True,
):
    """Description for Binary Sensor Entity."""

    value_on: set[str] | None = None
    value_off: set[str] | None = None
    available_access: tuple[Access] = (Access.READ, Access.READ_WRITE)


class HCButtonEntityDescription(
    HCEntityDescription, ButtonEntityDescription, frozen_or_thawed=True
):
    """Description for Button Entity."""

    available_access: tuple[Access] = (Access.READ_WRITE, Access.WRITE_ONLY)


class HCNumberEntityDescription(
    HCEntityDescription, NumberEntityDescription, frozen_or_thawed=True
):
    """Description for Number Entity."""

    available_access: tuple[Access] = (Access.READ_WRITE, Access.WRITE_ONLY)


class HCLightEntityDescription(HCEntityDescription, LightEntityDescription, frozen_or_thawed=True):
    """Description for Number Entity."""

    available_access: tuple[Access] = (Access.READ_WRITE, Access.WRITE_ONLY)
    brightness_entity: str | None = None
    color_temperature_entity: str | None = None
    color_entity: str | None = None
    color_mode_entity: str | None = None


class HCFanEntityDescription(HCEntityDescription, FanEntityDescription, frozen_or_thawed=True):
    """Description for Fan Entity."""

    available_access: tuple[Access] = (Access.READ_WRITE,)


class EntityDescriptions(TypedDict):
    """Entity descriptions by type."""

    button: list[HCButtonEntityDescription]
    active_program: list[HCSensorEntityDescription]
    binary_sensor: list[HCBinarySensorEntityDescription]
    event_sensor: list[HCSensorEntityDescription]
    number: list[HCNumberEntityDescription]
    program: list[HCSelectEntityDescription]
    select: list[HCSelectEntityDescription]
    sensor: list[HCSensorEntityDescription]
    start_button: list[HCButtonEntityDescription]
    switch: list[HCSwitchEntityDescription]
    wifi: list[HCSensorEntityDescription]
    light: list[HCLightEntityDescription]
    fan: list[HCFanEntityDescription]


_EntityDescriptionsDefinitionsType = dict[
    Literal[
        "button",
        "active_program",
        "binary_sensor",
        "event_sensor",
        "number",
        "program",
        "select",
        "sensor",
        "start_button",
        "switch",
        "wifi",
        "light",
        "fan",
        "dynamic",
    ],
    list[
        HCEntityDescription
        | Callable[[HomeAppliance], HCEntityDescription | EntityDescriptions | None]
    ],
]

_EntityDescriptionsType = dict[
    Literal[
        "button",
        "active_program",
        "binary_sensor",
        "event_sensor",
        "number",
        "program",
        "select",
        "sensor",
        "start_button",
        "switch",
        "wifi",
        "light",
        "fan",
    ],
    list[HCEntityDescription],
]
