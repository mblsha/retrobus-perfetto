# Historical Redux v4 density reproduction

This directory preserves the exact inputs, generated profiles, and modeled
outputs behind the historical Redux numbers in
[`../../V4_CODEC_AUDIT.md`](../../V4_CODEC_AUDIT.md).

The raw captures are not copied into this repository. Obtain the checksum-pinned
files named by `manifest.json`, place them in one directory, and provide the
checksum-pinned Redux schema separately. From the repository root, reproduce and
verify every preserved byte with:

```sh
py/.venv/bin/python tools/compact_v4_historical_replay.py \
  compact/audit/v4-redux-historical/manifest.json \
  --corpus-root /path/to/qemu-trace-analysis \
  --schema /path/to/repalm-redux/schemas/redux-trace-v1.json \
  --verify
```

Use `--write` instead of `--verify` to regenerate `profile-128.json`,
`profile-247.json`, and `results.json`. The manifest declares the exact shared
training set, its no-split in-sample policy, explicit state IDs, parser, wire
cost, and payload/container accounting. `results.json` preserves logical-stream
digests, all v3 byte cursors, all v4 bit and byte cursors, profile hits/misses,
bit attribution, payload-only cost, and total container cost.

`ARTIFACTS.sha256` checks the four hand/pipeline artifacts. Profile SHA-256
values inside `results.json` hash canonical JSON without the trailing newline;
the artifact checksums hash the files as stored.
