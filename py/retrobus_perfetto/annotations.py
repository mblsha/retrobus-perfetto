"""Helper classes for building Perfetto debug annotations."""

from typing import Dict, Any


_POINTER_SUFFIXES = ("_addr", "_address", "_pc", "_sp", "_pointer")


def _is_pointer_field(name: str) -> bool:
    """Return True if the annotation name is likely to represent a pointer."""
    return name.lower().endswith(_POINTER_SUFFIXES)


def _set_annotation_value(entry, name: str, value: Any) -> None:
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
        entry.string_value = value
    else:
        entry.string_value = str(value)


class DebugAnnotationBuilder:
    """Builder for Perfetto debug annotations with type-safe value handling."""

    def __init__(self, annotation):
        """
        Initialize with a protobuf DebugAnnotation object.

        Args:
            annotation: The protobuf DebugAnnotation to populate
        """
        self.annotation = annotation

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _create_entry(self, name: str):
        """Create a new dictionary entry for nested annotations."""
        entry = self.annotation.dict_entries.add()
        entry.name = name
        return entry

    def pointer(self, name: str, value: int) -> None:
        """Add a pointer value (displayed as hex in UI)."""
        entry = self._create_entry(name)
        entry.pointer_value = value

    def string(self, name: str, value: str) -> None:
        """Add a string value."""
        entry = self._create_entry(name)
        entry.string_value = value

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
        _set_annotation_value(entry, name, value)


class TrackEventWrapper:
    """Wrapper for TrackEvent with convenient annotation methods."""

    def __init__(self, event):
        """
        Initialize with a protobuf TrackEvent object.

        Args:
            event: The protobuf TrackEvent to wrap
        """
        self.event = event

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
        ann.name = name
        return DebugAnnotationBuilder(ann)

    def add_annotations(self, data: Dict[str, Any]) -> None:
        """
        Add multiple annotations from a dictionary.

        Args:
            data: Dictionary of key-value pairs to add as annotations
        """
        for key, value in data.items():
            ann = self.event.debug_annotations.add()
            ann.name = key
            _set_annotation_value(ann, key, value)
