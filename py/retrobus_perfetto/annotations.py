"""Helper classes for building Perfetto debug annotations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .interning import InterningState


_POINTER_SUFFIXES = ("_addr", "_address", "_pc", "_sp", "_pointer")


def _is_pointer_field(name: str) -> bool:
    """Return True if the annotation name is likely to represent a pointer."""
    return name.lower().endswith(_POINTER_SUFFIXES)


def _set_annotation_name(
    entry, name: str, packet, interning_state: Optional[InterningState]
) -> None:
    if interning_state is not None and packet is not None:
        entry.name_iid = interning_state.intern_debug_annotation_name(name, packet)
    else:
        entry.name = name


def _set_annotation_string_value(
    entry, value: str, packet, interning_state: Optional[InterningState]
) -> None:
    if interning_state is not None and packet is not None:
        entry.string_value_iid = interning_state.intern_debug_annotation_string_value(
            value, packet
        )
    else:
        entry.string_value = value


def _set_annotation_value(
    entry,
    name: str,
    value: Any,
    *,
    packet=None,
    interning_state: Optional[InterningState] = None,
) -> None:
    """Populate a debug annotation entry with a value based on its type."""
    if isinstance(value, bool):
        entry.bool_value = value
    elif isinstance(value, int):
        if _is_pointer_field(name):
            entry.pointer_value = value
        else:
            entry.int_value = value
    elif isinstance(value, float):
        entry.double_value = value
    elif isinstance(value, str):
        _set_annotation_string_value(entry, value, packet, interning_state)
    else:
        _set_annotation_string_value(entry, str(value), packet, interning_state)


class DebugAnnotationBuilder:
    """Builder for Perfetto debug annotations with type-safe value handling."""

    def __init__(
        self,
        annotation,
        *,
        packet=None,
        interning_state: Optional[InterningState] = None,
    ):
        """
        Initialize with a protobuf DebugAnnotation object.

        Args:
            annotation: The protobuf DebugAnnotation to populate
        """
        self.annotation = annotation
        self._packet = packet
        self._interning_state = interning_state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _create_entry(self, name: str):
        """Create a new dictionary entry for nested annotations."""
        entry = self.annotation.dict_entries.add()
        _set_annotation_name(entry, name, self._packet, self._interning_state)
        return entry

    def pointer(self, name: str, value: int) -> None:
        """Add a pointer value (displayed as hex in UI)."""
        entry = self._create_entry(name)
        entry.pointer_value = value

    def string(self, name: str, value: str) -> None:
        """Add a string value."""
        entry = self._create_entry(name)
        _set_annotation_string_value(entry, value, self._packet, self._interning_state)

    def bool(self, name: str, value: bool) -> None:
        """Add a boolean value."""
        entry = self._create_entry(name)
        entry.bool_value = value

    def integer(self, name: str, value: int) -> None:
        """Add an integer value."""
        entry = self._create_entry(name)
        entry.int_value = value

    def double(self, name: str, value: float) -> None:
        """Add a floating point value."""
        entry = self._create_entry(name)
        entry.double_value = value

    def auto(self, name: str, value: Any) -> None:
        """Automatically detect type and add value."""
        entry = self._create_entry(name)
        _set_annotation_value(
            entry, name, value, packet=self._packet, interning_state=self._interning_state
        )


class TrackEventWrapper:
    """Wrapper for TrackEvent with convenient annotation methods."""

    def __init__(
        self,
        event,
        *,
        packet=None,
        interning_state: Optional[InterningState] = None,
    ):
        """
        Initialize with a protobuf TrackEvent object.

        Args:
            event: The protobuf TrackEvent to wrap
        """
        self.event = event
        self._packet = packet
        self._interning_state = interning_state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def annotation(self, name: str) -> DebugAnnotationBuilder:
        """
        Create a new debug annotation with the given name.

        Args:
            name: The name of the annotation group

        Returns:
            DebugAnnotationBuilder for adding values
        """
        ann = self.event.debug_annotations.add()
        _set_annotation_name(ann, name, self._packet, self._interning_state)
        return DebugAnnotationBuilder(
            ann, packet=self._packet, interning_state=self._interning_state
        )

    def add_annotations(self, data: Dict[str, Any]) -> None:
        """
        Add multiple annotations from a dictionary.

        Args:
            data: Dictionary of key-value pairs to add as annotations
        """
        for key, value in data.items():
            ann = self.event.debug_annotations.add()
            _set_annotation_name(ann, key, self._packet, self._interning_state)
            _set_annotation_value(
                ann, key, value, packet=self._packet, interning_state=self._interning_state
            )
