# Compact v3 density audit

This is the corrected v3 baseline. The subsequent static-profile experiments
and current writer are documented in `V4_CODEC_AUDIT.md`.

This audit defines “better” as all of the following at once:

- direct Redux records are never larger than v1 and remove v2's structural
  publication-byte overhead;
- interrupted-write recovery returns exactly a prefix of fully published
  logical records;
- semantic event IDs, argument order, and v1/v2 host-reader compatibility stay
  stable;
- the allocation-free target writer remains within the ARMv5TE text and stack
  budgets; and
- density claims come from replaying representative corpora, not only a
  producer-blind best case.

## Selected encoding

`RBCTRC3` uses a schema-derived semantic opcode as the publication byte. Events
sorted by semantic ID receive ordinary opcodes `1..251`; any remaining events
use the `0xff` extended escape. Unused ordinary slots are assigned in pairs to
eligible no-stored-argument instants for implicit delta zero and one. Controls
remain `0xfc` loss, `0xfd` clock sync, `0xfe` tracked event, and `0xff` extended
event. The tracked-event opcode commits its track ID, inner opcode, and event
body as one transaction.

For the current Redux schema, semantic IDs `0..236` map to opcodes
`0x01..0xed`. Screen mutation, semantic ID 229, keeps ordinary opcode `0xe6`
and receives delta-zero/one aliases `0xee` and `0xef`. Opcodes `0xf0..0xfb`
remain unused. This map is derived from the existing canonical schema, so Redux
does not need a producer-schema version or hash change. `RBCTRC3` distinguishes
the wire grammar.

The public generic C/C++ begin and emit APIs cannot know a producer's schema
rank, so they remain a valid extended-event fallback. Generated schema emitters
call the opcode-aware APIs and produce the dense form.

## Density results

The regression matrix establishes these exact payload costs:

| Record | v1 | v2 | v3 |
| --- | ---: | ---: | ---: |
| Redux-like direct slice, delta 2, duration 1 | 3 B | 4 B | 3 B |
| Argument-bearing direct event, delta 0 or 1 | same body cost | same total cost | same total cost |
| Eligible no-argument instant, delta 0 or 1 | 2 B | 1 B | 1 B |

A 4048-byte chunk payload therefore holds 1349 representative Redux slices in
v3 versus 1012 in v2, a 33.30% capacity gain. It also retains 4048 eligible
one-byte instants.

Historical host-clock boot traces were decoded from their raw obsolete
`RDXTRC1` record streams and replayed by logical event ID, delta, duration, and
wire-stored arguments. They use earlier Redux instrumentation
container, so these numbers are diagnostic and are not the v3 acceptance
corpus:

| Capture | Records | Version | Framing | Identity | Delta | Duration | Arguments | Payload | B/record |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Zire 31 cold boot | 115,925 | v1 | 0 | 115,925 | 116,129 | 116,090 | 14 | 348,158 | 3.0033 |
| Zire 31 cold boot | 115,925 | v2 | 115,925 | 115,925 | 66,472 | 116,090 | 14 | 414,426 | 3.5749 |
| Zire 31 cold boot | 115,925 | v3 | 0 | 115,925 | 116,128 | 116,090 | 14 | 348,157 | 3.0033 |
| Tungsten T3 cold boot | 269,073 | v1 | 0 | 269,073 | 269,610 | 269,816 | 14 | 808,513 | 3.0048 |
| Tungsten T3 cold boot | 269,073 | v2 | 269,073 | 269,073 | 157,761 | 269,816 | 14 | 965,737 | 3.5891 |
| Tungsten T3 cold boot | 269,073 | v3 | 0 | 269,073 | 269,610 | 269,816 | 14 | 808,513 | 3.0048 |

V2 had zero inline hits. V3 had one historical Zire screen-mutation alias hit
and no T3 hit; its important result is eliminating the extra byte from ordinary
records. More than 99.8% of historical deltas and durations were already
one-byte varints. The 32 most frequent exact tuples covered 80.38% of Zire and
77.61% of T3 records, but no host-clock tuple profile is embedded in v3.

The earlier attribution accidentally counted schema-restored `entry`
annotations as stored arguments. Those annotations consume no wire bytes; the
table above is the corrected raw-record attribution. The obsolete containers
used 348,158 payload bytes plus 1,346 bytes
of slack across 86 Zire chunks, and 808,513 payload bytes plus 4,287 bytes of
slack across 200 T3 chunks. Those container costs are not comparable to RBCT
v1/v2/v3 record attribution.

## Replay profiler

`tools/compact_trace_profile.py` reads finalized or explicitly allowed live
RBCT captures plus their exact schema, replays the ordered union of records and
clock synchronizations through v1, v2, and v3, and emits JSON containing:

- mutually exclusive framing, identity, delta, duration, argument,
  track/control, clock-sync, file-header, chunk-header, and slack attribution;
- bytes/record, records/payload-KiB, expanded events/payload-KiB, per-event
  frequency and cost, and varint-width histograms;
- specialized/extended opcode hit rates, physical chunk sequence and used
  lengths, exact wraps, and actual/modelled overwritten records; and
- an exact v2 per-chunk used-length comparison for complete non-wrapped v2
  captures.

Corpus manifests retain arbitrary scenario and device provenance. Wrapped
captures are marked retained-only because the overwritten logical records are
not available to replay.

## Recovery proof and limitation

At payload offset `p`, the writer leaves `p` zero, stores the complete body at
`p+1`, executes the platform publication barrier, and then atomically stores the
nonzero opcode at `p`. Before that last store a reader stops at zero and returns
the preceding prefix. After it, the body is visible. The single writer never
starts a later record first, and updates cursor/count metadata only afterward.
Induction over records gives exactly a prefix of committed logical records.
`0xfe` commits track selection and event together. Re-encoding after a chunk
wrap accounts for the reset timestamp and default track before publication.

Chunk reuse still invalidates `RBCK` before replacement and publishes its `R`
last. Interrupted finalization ignores unadvertised partial v3 CRC fields;
after the chunk-CRC flag is advertised, the reader validates them. Tests cover
every body-store prefix, commit-before-metadata, torn two-byte cursors and
counts, older-chunk slack followed by a newer chunk, full payloads without a
sentinel, ring reuse, invalid committed data, and each payload/chunk/header CRC
and final-bit publication stage.

Removing the v2 length envelope weakens arbitrary-corruption isolation, not
crash publication. A valid-looking corruption in a live, unchecksummed v3 body
can misparse the rest of that 4048-byte payload. Finalized CRCs detect it; the
next chunk header is the amortized restart point. Adding finer restart metadata
would spend bytes and CPU and requires corpus/device evidence first.

## Acceptance corpus and physical measurement

No current-schema full Redux RBCT cold/restored boot, input, display, storage,
network, or long-idle corpus was available in this checkout. No PXA OSCR device
or ARM/QEMU runtime was available on the audit host. Consequently, this change
does not claim current-workload or physical-device timing acceptance.

Acceptance still requires current Zire 31 and T3 cold/restored captures, the
named scenarios, long-idle coverage, and at least one real PXA OSCR capture.
QEMU validates plumbing only. At 3,686,400 Hz, a 32-bit generation's half-range
is about 582.5 seconds; Redux must insert a periodic synchronization or change
generation before a longer idle gap.

Physical overhead must use a coarse OSCR-bracketed replay loop: bracket a large
fixed batch once, compare otherwise identical traced and untraced batches, and
divide the difference by accepted records. Per-event PMU or timer reads would
measure the benchmark instrumentation rather than the compact event path.

## Redux integration

Redux must update its retrobus-perfetto submodule pin, regenerate
`include/redux/generated/compact_trace_schema.h`, and pass generated opcode
metadata from the centralized dynamic calls in `src/compact_trace.cpp` to
`rbct_writer_begin_opcode` and `rbct_writer_emit_opcode`. Because Redux IDs are
dense, the ordinary opcode is `event_id + 1`; only semantic ID 229 needs the
`0xee/0xef` aliases. Public `TraceEventId`, trace call sites, semantic IDs,
argument types/order, and `redux-trace-v1.json` remain unchanged. Tests and
format reporting must expect `RBCTRC3` / `retrobus-compact-v3` while upstream
v1/v2 decoder fixtures remain intact.
