# Compact v4 packing audit

## What “better” means

Host decode speed and complexity are deliberately free. A packing scheme is
better when it reduces target payload bits without adding mutable target memory,
allocation, target-side training, phrase buffering, or expensive per-event
arithmetic. It must preserve semantic records and immediate crash-prefix
publication. ROM tables are acceptable, but every corpus-specific choice must
be explicit and hash-bound.

## Reproducible historical diagnostic

The historical Zire 31 and Tungsten T3 `RDXTRC1` cold-boot captures are useful
diagnostics, not an acceptance corpus. The complete reproduction bundle is in
[`audit/v4-redux-historical`](audit/v4-redux-historical/README.md). Its manifest
pins both raw captures and the current Redux schema by SHA-256, declares the
parser, training inputs, lack of a train/test split, state IDs, and container
accounting. It preserves both generated profile JSON files and exact model
results, including every modeled chunk cursor.

The replay independently decodes each raw record as event identity, timestamp
delta, schema duration, and stored arguments. It then repacks the same ordered
logical stream into fresh v3 and v4 chunks. The shared profiles are trained on
the union of both complete captures with explicit state events `(218, 83)` and
evaluated on those same captures. These are therefore in-sample packing results,
not generalization results.

| Wire model | Capture | Records | Payload bits | Byte-rounded payload | Payload B/record | Hits | Misses | Chunks | Total container |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v3 | Zire 31 | 115,925 | 2,785,256 | 348,157 | 3.003295 | — | — | 87 | 356,512 |
| v3 | T3 | 269,073 | 6,468,104 | 808,513 | 3.004809 | — | — | 200 | 819,360 |
| v4 shared-128 | Zire 31 | 115,925 | 662,835 | 82,864 | 0.714807 | 108,306 | 7,619 | 21 | 86,208 |
| v4 shared-128 | T3 | 269,073 | 1,488,568 | 186,086 | 0.691582 | 252,294 | 16,779 | 46 | 188,608 |
| v4 shared-247 | Zire 31 | 115,925 | 589,210 | 73,656 | 0.635376 | 112,278 | 3,647 | 19 | 78,016 |
| v4 shared-247 | T3 | 269,073 | 1,344,502 | 168,074 | 0.624641 | 260,097 | 8,976 | 42 | 172,224 |

“Byte-rounded payload” is the sum of `ceil(committed_bits / 8)` for each
modeled chunk, not `ceil(total_bits / 8)`. “Total container” is the 160-byte v3
or 192-byte v4 file header plus complete 4,096-byte chunks. It therefore includes
48 bytes of header and all slack in every chunk. The historical source
containers use a different 96-byte/32-byte `RDXTRC1` layout and are reported
separately in the preserved results.

The corrected v3 attribution is:

| Capture | Identity bytes | Delta bytes | Duration bytes | Stored-argument bytes | V3 payload bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Zire 31 | 115,925 | 116,128 | 116,090 | 14 | 348,157 |
| T3 | 269,073 | 269,073 | 269,610 | 269,816 | 14 | 808,513 |

The earlier four-byte attribution was wrong because it counted schema-restored
`entry` annotations even though they occupy no target record bytes.

The exact implemented v4 bit attribution is:

| Profile/capture | Hit codes | Miss escapes | Literal kind | Identity | Delta | Duration | Arguments | Total bits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| shared-128 Zire 31 | 437,064 | 24,613 | 15,238 | 60,952 | 62,584 | 62,272 | 112 | 662,835 |
| shared-128 T3 | 987,923 | 54,039 | 33,558 | 134,232 | 138,528 | 140,176 | 112 | 1,488,568 |
| shared-247 Zire 31 | 475,791 | 15,533 | 7,294 | 29,176 | 30,808 | 30,496 | 112 | 589,210 |
| shared-247 T3 | 1,062,073 | 38,701 | 17,952 | 71,808 | 76,104 | 77,752 | 112 | 1,344,502 |

The literal-kind column is exactly two bits per miss. This was absent from the
earlier experimental table and explains the density mismatch that prompted the
follow-up audit.

The general trainer’s automatic context selection is bounded rather than
“entropy-optimal.” It takes the 12 most frequent semantic event IDs, ordered by
descending frequency with semantic ID as the tie-breaker, exhaustively evaluates
all 66 unordered pairs, and chooses the first minimum estimated length-limited
Huffman prefix cost. That selection score does not include literal bodies or
their two kind bits. The historical headline fixes `(218, 83)` explicitly, so
regeneration does not depend on automatic selection.

These exact tuples are clock-domain-sensitive. Rescaling the historical host
clock to the PXA 3,686,400 Hz domain previously produced no useful exact tuple
matches. No historical profile is built into the writer or Redux. Current QEMU
plumbing captures and a real PXA OSCR corpus must train and validate a production
profile.

## Selected wire mechanism

`RBCTRC4` uses an explicit external static profile with either 128 or 247 tuple
entries. Each entry maps `(model state, semantic event ID, timestamp delta,
duration)` to a canonical, least-significant-bit-first Huffman code of at most
12 bits. Only same-track, zero-stored-argument completed slices whose identity,
delta, and duration each fit in one byte can hit. Every other shape uses a
per-state escape, two literal-kind bits, and a lossless schema-shaped literal.

The target profile is generated as read-only displacement, key, and packed-code
arrays. The writer stores one profile pointer and reuses two spare bits in its
existing state byte. A hit performs two multiplies, table reads, one comparison,
and a short bit append. It performs no target-side adaptation or buffering.

The 192-byte v4 file header carries the profile SHA-256. The canonical profile
also carries the semantic schema SHA-256. Profiles can change without changing
the producer schema because they affect only wire packing. A zero profile hash
selects a universal literal-only v4 stream.

## Publication and recovery

The low and high 16-bit fields at chunk offsets 28 and 30 form one aligned
little-endian atomic publication word: committed payload bits and committed
data-record count. Payload bits beyond the published cursor are invisible. The
writer fills the suffix, executes the platform publication barrier, and stores
the new word once. It never changes a committed bit and never begins a later
record first.

Inductively, a reader sees either the old cursor and exactly the old complete
prefix, or the new cursor after every body bit is visible. Clock sync publication
uses the same cursor but leaves the data-record half unchanged. Chunk reuse
still invalidates `RBCK` before reuse and publishes its leading `R` last. The
guarantee assumes one writer, a stable snapshot, an aligned atomic 32-bit store,
the documented platform barrier, and coherent or explicitly persisted stores.

An unfinalized v4 chunk whose published bit cursor exceeds its 4,048-byte
payload is discarded during recovery. It is never allowed to extend a logical
read into the next physical chunk. A sequence gap then bounds recovery to the
contiguous older prefix.

The bit cursor is not a corruption checksum. A valid-looking bit flip in an
unfinalized committed stream can desynchronize the rest of that chunk. Finalized
payload and header CRCs detect corruption; 4,096-byte chunks remain amortized
restart points.

## Implemented tooling and tests

- `tools/compact_codec_profile.py` trains deterministic 128/247-entry profiles,
  performs the documented bounded context search or accepts explicit context
  IDs, length-limits Huffman codes, constructs the CHD table, and writes
  canonical JSON or a target C header.
- `tools/compact_trace_profile.py` reports exact v1-v4 payload use, v4 committed
  bits, byte-rounded chunk use, bit attribution including literal-kind bits,
  hits/misses, wraps, overwritten records, and actual non-wrapped v4 cursor
  verification.
- `tools/compact_v4_historical_replay.py` verifies the pinned historical inputs,
  decodes `RDXTRC1`, regenerates both shared profiles, and byte-compares the
  preserved results.
- Regression tests assert exact v4 hit/miss bit attribution, byte rounding,
  wrap re-encoding, per-chunk bit and byte cursors, C/Python semantic equality,
  profile-hash refusal, and v1/v2/v3 decoder preservation.
- The maximum-literal test reconstructs 71 physical payload-prefix snapshots:
  the old shared partial byte followed by each prefix through all 70 touched
  bytes. These snapshots are not claimed to enumerate the C function’s actual
  repeated writes to a shared byte. Every snapshot retains the old 27-bit cursor
  and exposes exactly the old logical record; the 582-bit cursor exposes both.
- The resource regression fills exactly 32,384 payload bits with 32,383 profiled
  slices: the initial tuple costs two bits and steady state costs one.
- The complete ARMv5TE soft-float `-Os -ffixed-r9` object measures 8,360 bytes
  of text, has no undefined symbols, and reports 168 bytes maximum stack. The
  current gates are 8,500 and 192 bytes. Writer and scope objects are capped at
  144/120 bytes (64/32-bit hosts) and 88 bytes respectively. Generated
  128/247-entry profiles occupy 936/1,768 bytes of read-only ARM ROM including
  their descriptor.

## Remaining acceptance work

No current Redux cold/restored, input, display, storage, network, or long-idle
RBCT corpus and no real PXA OSCR capture exists in this checkout. The historical
captures also embed no source revision or schema hash. Consequently v4 ships a
codec mechanism and deterministic tools, not a Redux production profile.

The ARM writer remains above the old 7,000-byte text gate. This work retains an
8,500-byte gate for the measured 8,360-byte object; that larger code budget
still requires explicit acceptance. Real target overhead must be measured with
a coarse OSCR-bracketed replay loop, not per-event reads.
