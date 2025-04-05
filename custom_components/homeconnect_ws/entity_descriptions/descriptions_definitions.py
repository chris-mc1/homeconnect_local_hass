"""Definitions for Entity Description."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, NotRequired, TypedDict

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
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


_EntityDescriptionsType = dict[
    str, list[HCEntityDescription | Callable[[HomeAppliance], HCEntityDescription | None]]
]


class EntityDescriptions(TypedDict):
    """Entity descriptions by type."""

    abort_button: list[HCButtonEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    active_program: list[HCSensorEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    binary_sensor: list[
        HCBinarySensorEntityDescription | Callable[[HomeAppliance], HCEntityDescription]
    ]
    event_sensor: list[HCSensorEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    number: list[HCNumberEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    power_switch: list[HCSwitchEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    program: list[HCSelectEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    select: list[HCSelectEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    sensor: list[HCSensorEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    start_button: list[HCButtonEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    start_in: list[HCSelectEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
    switch: list[HCSwitchEntityDescription | Callable[[HomeAppliance], HCEntityDescription]]
