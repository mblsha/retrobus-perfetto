"""Helper classes for building Perfetto debug annotations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Dict, Optional

from .interning import InterningState
from .models import InlineFrame, Pointer, SourceLocation, StackFrame, UInt


_POINTER_SUFFIXES = ("_addr", "_address", "_pc", "_sp", "_pointer")


class DebugAnnotationError(ValueError):
    """Base class for structured debug-annotation encoding errors."""


class DebugAnnotationCycleError(DebugAnnotationError):
    """Raised when a dictionary or array contains itself recursively."""


class DebugAnnotationDepthError(DebugAnnotationError):
    """Raised when structured annotations exceed the configured depth."""


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


def _validate_annotation_value(
    value: Any,
    *,
    max_depth: int,
    name: str = "",
    depth: int = 0,
    active: Optional[set[int]] = None,
) -> None:
    """Validate a value before mutating a protobuf message."""
    if isinstance(value, (bool, UInt, Pointer, int, float, str)):
        if isinstance(value, int) and not isinstance(value, bool):
            if _is_pointer_field(name):
                if not 0 <= value <= 0xFFFF_FFFF_FFFF_FFFF:
                    raise OverflowError("pointer debug annotation must fit in uint64")
            elif not -0x8000_0000_0000_0000 <= value <= 0x7FFF_FFFF_FFFF_FFFF:
                raise OverflowError("signed debug annotation must fit in int64; use UInt")
        return

    is_mapping = isinstance(value, Mapping)
    is_array = isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )
    if not is_mapping and not is_array:
        raise TypeError(
            "debug annotations support bool, int, UInt, float, str, Pointer, "
            "dictionaries, and arrays"
        )
    if depth >= max_depth:
        raise DebugAnnotationDepthError(
            f"debug annotation nesting exceeds max_depth={max_depth}"
        )

    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        raise DebugAnnotationCycleError("debug annotation contains a cycle")
    active.add(identity)
    try:
        if is_mapping:
            for key, child in value.items():
                if not isinstance(key, str):
                    raise TypeError("debug annotation dictionary keys must be strings")
                _validate_annotation_value(
                    child,
                    max_depth=max_depth,
                    name=key,
                    depth=depth + 1,
                    active=active,
                )
        else:
            for child in value:
                _validate_annotation_value(
                    child,
                    max_depth=max_depth,
                    name="",
                    depth=depth + 1,
                    active=active,
                )
    finally:
        active.remove(identity)


def _set_annotation_value(
    entry,
    name: str,
    value: Any,
    *,
    packet=None,
    interning_state: Optional[InterningState] = None,
    max_depth: int = 64,
) -> None:
    """Populate a debug annotation entry with a value based on its type."""
    _validate_annotation_value(value, max_depth=max_depth, name=name)
    _encode_annotation_value(
        entry,
        name,
        value,
        packet=packet,
        interning_state=interning_state,
        max_depth=max_depth,
        depth=0,
    )


def _encode_annotation_value(
    entry,
    name: str,
    value: Any,
    *,
    packet=None,
    interning_state: Optional[InterningState] = None,
    max_depth: int,
    depth: int,
) -> None:
    if isinstance(value, bool):
        entry.bool_value = value
    elif isinstance(value, UInt):
        entry.uint_value = value.value
    elif isinstance(value, Pointer):
        entry.pointer_value = value.value
    elif isinstance(value, int):
        if _is_pointer_field(name):
            if value < 0:
                raise OverflowError("pointer debug annotations cannot be negative")
            entry.pointer_value = value
        else:
            entry.int_value = value
    elif isinstance(value, float):
        entry.double_value = value
    elif isinstance(value, str):
        _set_annotation_string_value(entry, value, packet, interning_state)
    elif isinstance(value, Mapping):
        for key, child in value.items():
            child_entry = entry.dict_entries.add()
            _set_annotation_name(child_entry, key, packet, interning_state)
            _encode_annotation_value(
                child_entry,
                key,
                child,
                packet=packet,
                interning_state=interning_state,
                max_depth=max_depth,
                depth=depth + 1,
            )
    else:
        for child in value:
            child_entry = entry.array_values.add()
            _encode_annotation_value(
                child_entry,
                "",
                child,
                packet=packet,
                interning_state=interning_state,
                max_depth=max_depth,
                depth=depth + 1,
            )


class DebugAnnotationBuilder:
    """Builder for Perfetto debug annotations with type-safe value handling."""

    def __init__(
        self,
        annotation,
        *,
        packet=None,
        interning_state: Optional[InterningState] = None,
        max_depth: int = 64,
    ):
        """
        Initialize with a protobuf DebugAnnotation object.

        Args:
            annotation: The protobuf DebugAnnotation to populate
        """
        self.annotation = annotation
        self._packet = packet
        self._interning_state = interning_state
        self._max_depth = max_depth

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

    def uint(self, name: str, value: int) -> None:
        """Add an unsigned integer value."""
        entry = self._create_entry(name)
        entry.uint_value = UInt(value).value

    def double(self, name: str, value: float) -> None:
        """Add a floating point value."""
        entry = self._create_entry(name)
        entry.double_value = value

    def auto(self, name: str, value: Any) -> None:
        """Encode a scalar, dictionary, or array without losing type information."""
        _validate_annotation_value(value, max_depth=self._max_depth, name=name)
        entry = self._create_entry(name)
        _set_annotation_value(
            entry,
            name,
            value,
            packet=self._packet,
            interning_state=self._interning_state,
            max_depth=self._max_depth,
        )

    def dictionary(self, name: str, value: Mapping[str, Any]) -> None:
        """Add a recursively encoded dictionary."""
        self.auto(name, value)

    def array(self, name: str, value: Sequence[Any]) -> None:
        """Add a recursively encoded array."""
        self.auto(name, value)


class TrackEventWrapper:
    """Wrapper for TrackEvent with convenient annotation methods."""

    def __init__(
        self,
        event,
        *,
        packet=None,
        interning_state: Optional[InterningState] = None,
        max_depth: int = 64,
    ):
        """
        Initialize with a protobuf TrackEvent object.

        Args:
            event: The protobuf TrackEvent to wrap
        """
        self.event = event
        self._packet = packet
        self._interning_state = interning_state
        self._max_depth = max_depth

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
            ann,
            packet=self._packet,
            interning_state=self._interning_state,
            max_depth=self._max_depth,
        )

    def add_category(self, category: str) -> "TrackEventWrapper":
        """Add one category, interning it when writer interning is enabled."""
        if self._interning_state is not None and self._packet is not None:
            self.event.category_iids.append(
                self._interning_state.intern_event_category(category, self._packet)
            )
        else:
            self.event.categories.append(category)
        return self

    def add_categories(self, *categories: str) -> "TrackEventWrapper":
        """Add one or more event categories."""
        for category in categories:
            self.add_category(category)
        return self

    def set_source_location(
        self, location: SourceLocation, *, intern: bool = True
    ) -> "TrackEventWrapper":
        """Attach an inline or interned source location to the event."""
        if intern and self._interning_state is not None and self._packet is not None:
            self.event.source_location_iid = self._interning_state.intern_source_location(
                location, self._packet
            )
        else:
            target = self.event.source_location
            if location.file_name:
                target.file_name = location.file_name
            if location.function_name:
                target.function_name = location.function_name
            if location.line_number is not None:
                target.line_number = location.line_number
        return self

    def set_inline_callstack(
        self, frames: Sequence[InlineFrame]
    ) -> "TrackEventWrapper":
        """Attach a bottom-to-top, already-symbolized inline callstack."""
        target = self.event.callstack
        for frame in frames:
            proto_frame = target.frames.add()
            proto_frame.function_name = frame.function_name
            if frame.source_file is not None:
                proto_frame.source_file = frame.source_file
            if frame.line_number is not None:
                proto_frame.line_number = frame.line_number
        return self

    def set_callstack(self, frames: Sequence[StackFrame]) -> "TrackEventWrapper":
        """Attach an interned native callstack with mappings and symbols."""
        if self._interning_state is None or self._packet is None:
            raise DebugAnnotationError(
                "native callstacks require encoding='interned'; use set_inline_callstack "
                "for inline encoding"
            )
        self.event.callstack_iid = self._interning_state.intern_callstack(
            frames, self._packet
        )
        return self

    def add_annotations(self, data: Dict[str, Any]) -> None:
        """
        Add multiple annotations from a dictionary.

        Args:
            data: Dictionary of key-value pairs to add as annotations
        """
        for key, value in data.items():
            if not isinstance(key, str):
                raise TypeError("debug annotation names must be strings")
            _validate_annotation_value(value, max_depth=self._max_depth, name=key)
        for key, value in data.items():
            ann = self.event.debug_annotations.add()
            _set_annotation_name(ann, key, self._packet, self._interning_state)
            _set_annotation_value(
                ann,
                key,
                value,
                packet=self._packet,
                interning_state=self._interning_state,
                max_depth=self._max_depth,
            )
