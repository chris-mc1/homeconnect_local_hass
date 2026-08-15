"""Button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeconnect_websocket.entities import Execution

from .entity import HCEntity
from .helpers import _agent_dbg, create_entities, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import ActiveProgram, Command

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

PARALLEL_UPDATES = 0

# Thermador/BSH appliances often leave Abort/Pause `available=True` after the program
# ends. POST then returns 400 BadRequest. Gate on OperationState only.
_ABORT_OPERATION_STATES = frozenset({"Run", "Pause", "ActionRequired", "Aborting"})
_PAUSE_OPERATION_STATES = frozenset({"Run"})
_RESUME_OPERATION_STATES = frozenset({"Pause"})
_PROGRAM_STATE_ENTITIES = (
    "BSH.Common.Status.OperationState",
    "BSH.Common.Root.ActiveProgram",
)


def program_button_is_available(key: str, appliance: HomeAppliance) -> bool:
    """Return whether a program-control button is valid for the current cycle."""
    operation = appliance.entities.get("BSH.Common.Status.OperationState")
    op_value = getattr(operation, "value", None)
    if key == "button_abort_program":
        return op_value in _ABORT_OPERATION_STATES
    if key == "button_pause_program":
        return op_value in _PAUSE_OPERATION_STATES
    if key == "button_resume_program":
        return op_value in _RESUME_OPERATION_STATES
    return True


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up button platform."""
    entities = create_entities(
        {"button": HCButton, "start_button": HCStartButton}, config_entry.runtime_data
    )
    async_add_entites(entities)


class HCButton(HCEntity, ButtonEntity):
    """Abort Button Entity."""

    _entity: Command
    entity_description: HCButtonEntityDescription

    def __init__(
        self,
        entity_description: HCButtonEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        for name in _PROGRAM_STATE_ENTITIES:
            entity = runtime_data.appliance.entities.get(name)
            if entity is not None and entity not in self._entities:
                self._entities.append(entity)

    @property
    def available(self) -> bool:
        return super().available and program_button_is_available(
            self.entity_description.key, self._runtime_data.appliance
        )

    @error_decorator
    async def async_press(self) -> None:
        # #region agent log
        _agent_dbg(
            "H4",
            "button.py:HCButton.async_press",
            "press start",
            {
                "key": self.entity_description.key,
                "entity": getattr(self._entity, "name", None),
                "entity_avail": getattr(self._entity, "available", None),
                "entity_access": str(getattr(self._entity, "access", None)),
                "ha_available": self.available,
                "session_connected": bool(
                    getattr(self._runtime_data.appliance.session, "connected", False)
                ),
                "connection_state": str(
                    getattr(self._runtime_data.appliance.session, "connection_state", None)
                ),
                "operation": getattr(
                    self._runtime_data.appliance.entities.get("BSH.Common.Status.OperationState"),
                    "value",
                    None,
                ),
                "remote_start": getattr(
                    self._runtime_data.appliance.entities.get(
                        "BSH.Common.Status.RemoteControlStartAllowed"
                    ),
                    "value",
                    None,
                ),
            },
        )
        # #endregion
        try:
            await self._entity.set_value(True)
        except Exception as exc:
            # #region agent log
            _agent_dbg(
                "H4",
                "button.py:HCButton.async_press",
                "press failed",
                {
                    "key": self.entity_description.key,
                    "entity": getattr(self._entity, "name", None),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            # #endregion
            raise


class HCStartButton(HCEntity, ButtonEntity):
    """Start Button Entity."""

    _entity: ActiveProgram
    entity_description: HCButtonEntityDescription

    @property
    def available(self) -> bool:
        available = super().available
        available &= self._runtime_data.appliance.selected_program is not None
        if self._runtime_data.appliance.selected_program is not None:
            available &= (
                self._runtime_data.appliance.selected_program.execution
                == Execution.SELECT_AND_START
            )
        return available

    @error_decorator
    async def async_press(self) -> None:
        await self._runtime_data.appliance.selected_program.start()
