"""Update entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature

from .entity import HCEntity
from .helpers import create_entities, error_decorator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import Command

    from . import HCConfigEntry, HCData
    from .entity_descriptions.descriptions_definitions import HCUpdateEntityDescription

PARALLEL_UPDATES = 0

# The protocol only reports whether an update exists, not which version it
# would install, so this is shown in place of a real version number.
_LATEST_VERSION_PLACEHOLDER = "New Version"


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up update platform."""
    entities = create_entities({"update": HCUpdate}, config_entry.runtime_data)
    async_add_entites(entities)


class HCUpdate(HCEntity, UpdateEntity):
    """Update Entity."""

    entity_description: HCUpdateEntityDescription
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _command_entity: Command | None = None

    def __init__(
        self,
        entity_description: HCUpdateEntityDescription,
        runtime_data: HCData,
    ) -> None:
        super().__init__(entity_description, runtime_data)
        if entity_description.command_entity is not None:
            self._command_entity = self._runtime_data.appliance.entities[
                entity_description.command_entity
            ]

    @property
    def installed_version(self) -> str | None:
        return self._runtime_data.appliance.info.get("swVersion")

    @property
    def latest_version(self) -> str | None:
        if self._entity.value in ("Present", "Confirmed"):
            return _LATEST_VERSION_PLACEHOLDER
        return self.installed_version

    @error_decorator
    async def async_install(
        self,
        version: str | None,
        backup: bool,  # noqa: FBT001
        **kwargs: Any,
    ) -> None:
        if self._command_entity is not None:
            await self._command_entity.set_value(True)
