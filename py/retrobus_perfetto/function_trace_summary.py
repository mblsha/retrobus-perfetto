"""Summarize Perfetto function-trace slices into a compact YAML call graph."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .proto import perfetto_pb2
from .reader import resolve_interned_trace


@dataclass
class CallNode:
    name: str
    count: int = 0
    args: Dict[Tuple[Tuple[str, object], ...], int] = field(default_factory=dict)
    children: Dict[str, "CallNode"] = field(default_factory=dict)


@dataclass
class SliceEvent:
    track: str
    name: str
    event_type: int
    timestamp: int
    annotations: Dict[str, object]


def _annotation_value(annotation: perfetto_pb2.DebugAnnotation) -> object | None:
    if annotation.dict_entries:
        return {entry.name: _annotation_value(entry) for entry in annotation.dict_entries}
    if annotation.array_values:
        return [_annotation_value(entry) for entry in annotation.array_values]
    if annotation.HasField("int_value"):
        return annotation.int_value
    if annotation.HasField("uint_value"):
        return annotation.uint_value
    if annotation.HasField("pointer_value"):
        return annotation.pointer_value
    if annotation.HasField("double_value"):
        return annotation.double_value
    if annotation.HasField("bool_value"):
        return annotation.bool_value
    if annotation.HasField("string_value"):
        return annotation.string_value
    if annotation.HasField("legacy_json_value"):
        return annotation.legacy_json_value
    return None


def _extract_annotations(event: perfetto_pb2.TrackEvent) -> Dict[str, object]:
    return {
        ann.name: _annotation_value(ann)
        for ann in event.debug_annotations
        if ann.name
    }


def _normalize_value(value: object, *, int_format: str) -> object:
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    if isinstance(value, list):
        return json.dumps(value, separators=(",", ":"))
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if int_format == "hex":
            return f"0x{value:X}"
        return value
    if isinstance(value, float):
        return float(f"{value:.6f}")
    return value


def _normalize_payload(
    payload: Dict[str, object], *, ignore_keys: Iterable[str], int_format: str
) -> Tuple[Tuple[str, object], ...]:
    ignore = set(ignore_keys)
    items: List[Tuple[str, object]] = []
    for key in sorted(payload):
        if key in ignore:
            continue
        items.append((key, _normalize_value(payload[key], int_format=int_format)))
    return tuple(items)


def _format_yaml_key(text: str) -> str:
    safe = text.replace("'", "''")
    if not text or any(c in text for c in ":#{}[]&*?|-<>=!%@\\\""):
        return f"'{safe}'"
    if text[0].isdigit():
        return f"'{safe}'"
    return text


def _format_yaml_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    safe = text.replace("'", "''")
    if not text or any(c in text for c in ":#{}[]&*?|-<>=!%@\\\""):
        return f"'{safe}'"
    if text.lower() in {"null", "true", "false"}:
        return f"'{safe}'"
    return text


def _emit_node(node: CallNode, indent: str, lines: List[str]) -> None:
    lines.append(f"{indent}count: {node.count}")
    if node.args:
        lines.append(f"{indent}args:")
        rows = sorted(node.args.items(), key=lambda kv: (-kv[1], kv[0]))
        for payload_items, count in rows:
            lines.append(f"{indent}  - count: {count}")
            for key, value in payload_items:
                lines.append(
                    f"{indent}    {_format_yaml_key(key)}: {_format_yaml_value(value)}"
                )
    if node.children:
        lines.append(f"{indent}children:")
        for child_name, child in sorted(
            node.children.items(), key=lambda kv: (-kv[1].count, kv[0])
        ):
            lines.append(f"{indent}  {_format_yaml_key(child_name)}:")
            _emit_node(child, indent + "    ", lines)


def _parse_address(text: str) -> Optional[int]:
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(text, 10)
    except ValueError:
        return None


def load_name_map(path: Path) -> Dict[int, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "names" in data and isinstance(data["names"], dict):
        raw_map = data["names"]
    elif isinstance(data, dict):
        raw_map = data
    else:
        raw_map = {}

    name_map: Dict[int, str] = {}
    for key, value in raw_map.items():
        addr = _parse_address(str(key))
        if addr is None or not isinstance(value, str):
            continue
        name_map[addr] = value
    return name_map


def load_slice_events(trace_path: Path) -> List[SliceEvent]:
    trace = perfetto_pb2.Trace()
    trace.ParseFromString(trace_path.read_bytes())
    trace = resolve_interned_trace(trace, inplace=False)

    track_names: Dict[int, str] = {}
    events: List[SliceEvent] = []

    for index, packet in enumerate(trace.packet):
        if packet.HasField("track_descriptor"):
            desc = packet.track_descriptor
            name = (
                desc.thread.thread_name
                or desc.name
                or desc.process.process_name
                or f"track_{desc.uuid}"
            )
            track_names[desc.uuid] = name

        if not packet.HasField("track_event"):
            continue

        event = packet.track_event
        if event.type not in (
            perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN,
            perfetto_pb2.TrackEvent.TYPE_SLICE_END,
        ):
            continue

        track_uuid = event.track_uuid
        track_name = track_names.get(track_uuid, f"track_{track_uuid}")
        annotations = _extract_annotations(event)
        timestamp = packet.timestamp or index
        events.append(
            SliceEvent(
                track=track_name,
                name=event.name or "",
                event_type=event.type,
                timestamp=timestamp,
                annotations=annotations,
            )
        )

    events.sort(key=lambda evt: (evt.timestamp, evt.track, evt.event_type))
    return events


def build_call_graph(
    events: Sequence[SliceEvent],
    *,
    ignore_keys: Iterable[str],
    include_tracks: Optional[Sequence[str]] = None,
    exclude_tracks: Optional[Sequence[str]] = None,
    name_map: Optional[Dict[int, str]] = None,
    name_format: str = "name@addr",
    int_format: str = "hex",
) -> CallNode:
    root = CallNode(name="<root>")
    include_filter = set(include_tracks) if include_tracks else None
    exclude_filter = set(exclude_tracks) if exclude_tracks else set()

    @dataclass
    class Frame:
        node: CallNode
        start_ts: int
        track: str

    track_stacks: Dict[str, List[Frame]] = {}
    active: List[Frame] = []

    for event in events:
        if include_filter and event.track not in include_filter:
            continue
        if event.track in exclude_filter:
            continue
        if event.event_type == perfetto_pb2.TrackEvent.TYPE_SLICE_BEGIN:
            if active:
                parent_frame = max(active, key=lambda frame: frame.start_ts)
                parent_node = parent_frame.node
            else:
                parent_node = root

            resolved_name = event.name
            if name_map and event.track == "Functions":
                match = re.search(r"0x[0-9A-Fa-f]+", event.name)
                if match:
                    addr = int(match.group(0), 16)
                    mapped = name_map.get(addr)
                    if mapped:
                        if name_format == "name":
                            resolved_name = mapped
                        else:
                            resolved_name = f"{mapped}@0x{addr:06X}"

            func_name = f"{event.track}::{resolved_name}"
            child = parent_node.children.get(func_name)
            if child is None:
                child = CallNode(name=func_name)
                parent_node.children[func_name] = child
            child.count += 1
            payload_key = _normalize_payload(
                event.annotations, ignore_keys=ignore_keys, int_format=int_format
            )
            if payload_key:
                child.args[payload_key] = child.args.get(payload_key, 0) + 1

            frame = Frame(node=child, start_ts=event.timestamp, track=event.track)
            track_stacks.setdefault(event.track, []).append(frame)
            active.append(frame)
        elif event.event_type == perfetto_pb2.TrackEvent.TYPE_SLICE_END:
            if track_stacks.get(event.track):
                frame = track_stacks[event.track].pop()
                if frame in active:
                    active.remove(frame)

    return root


def render_call_graph_yaml(root: CallNode) -> str:
    lines: List[str] = ["functions:"]
    for name, node in sorted(
        root.children.items(), key=lambda kv: (-kv[1].count, kv[0])
    ):
        lines.append(f"  {_format_yaml_key(name)}:")
        _emit_node(node, "    ", lines)
    return "\n".join(lines) + "\n"


def summarize_trace_to_yaml(
    trace_path: Path,
    *,
    ignore_keys: Optional[Sequence[str]] = None,
    include_tracks: Optional[Sequence[str]] = None,
    exclude_tracks: Optional[Sequence[str]] = None,
    name_map: Optional[Dict[int, str]] = None,
    name_format: str = "name@addr",
    int_format: str = "hex",
) -> str:
    ignore = list(ignore_keys or [])
    if "depth" not in ignore:
        ignore.append("depth")

    events = load_slice_events(trace_path)
    graph = build_call_graph(
        events,
        ignore_keys=ignore,
        include_tracks=include_tracks,
        exclude_tracks=exclude_tracks,
        name_map=name_map,
        name_format=name_format,
        int_format=int_format,
    )
    return render_call_graph_yaml(graph)
