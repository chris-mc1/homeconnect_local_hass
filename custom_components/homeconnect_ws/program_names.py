"""Resolve favourite labels from current appliance settings, not startup state."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.entities import Setting

PREFIX = "BSH.Common.Program.Favorite."


def favorite_name_entities(appliance: HomeAppliance, mapping: Mapping[str, str]) -> list[Setting]:
    """Return settings to observe through the integration's existing callback lifecycle."""
    return [
        appliance.settings[key]
        for program in mapping
        if program.startswith(PREFIX)
        if (key := f"BSH.Common.Setting.Favorite.{program[len(PREFIX) :]}.Name")
        in appliance.settings
    ]


def program_labels(appliance: HomeAppliance, mapping: Mapping[str, str]) -> dict[str, str]:
    """Keep ordinary program IDs and resolve unique, current favourite labels."""
    labels = dict(mapping)
    for program in labels:
        if program.startswith(PREFIX):
            slot = program[len(PREFIX) :]
            setting = appliance.settings.get(f"BSH.Common.Setting.Favorite.{slot}.Name")
            value = setting.value if setting is not None else None
            labels[program] = (
                value if isinstance(value, str) and value.strip() else f"favorite_{slot}"
            )
    # Keep every label unique so selecting one cannot start the wrong favourite.
    counts = Counter(labels.values())
    reserved = set(labels.values())
    for program, label in list(labels.items()):
        if program.startswith(PREFIX) and counts[label] > 1:
            candidate = f"{label} ({program[len(PREFIX) :]})"
            while candidate in reserved:
                candidate += f" ({program[len(PREFIX) :]})"
            labels[program] = candidate
            reserved.add(candidate)
    return labels


def favorite_settings(appliance: HomeAppliance, mapping: Mapping[str, str]) -> list[Setting]:
    """Observe names and saved-state flags for favourite option updates."""
    result = favorite_name_entities(appliance, mapping)
    for program in mapping:
        if program.startswith(PREFIX):
            key = f"BSH.Common.Setting.Favorite.{program[len(PREFIX) :]}.Functionality"
            if key in appliance.settings:
                result.append(appliance.settings[key])
    return result


def selectable_program_labels(
    appliance: HomeAppliance, mapping: Mapping[str, str]
) -> dict[str, str]:
    """Hide explicitly empty slots; use a nonblank name if no flag is supplied."""
    labels = program_labels(appliance, mapping)
    for program in list(labels):
        if not program.startswith(PREFIX):
            continue
        slot = program[len(PREFIX) :]
        setting = appliance.settings.get(f"BSH.Common.Setting.Favorite.{slot}.Functionality")
        flag = setting.value if setting is not None else None
        name = appliance.settings.get(f"BSH.Common.Setting.Favorite.{slot}.Name")
        value = name.value if name is not None else None
        saved = flag == "Program" or (
            flag is None and isinstance(value, str) and bool(value.strip())
        )
        if not saved:
            del labels[program]
    return labels
