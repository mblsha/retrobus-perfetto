import assert from "node:assert/strict";
import test from "node:test";

import { perfetto } from "../src/index.js";

const { protos } = perfetto;

test("generated bindings round-trip profiler fidelity fields", () => {
  const trace = protos.Trace.create({
    packet: [
      {
        trustedPacketSequenceId: 7,
        sequenceFlags: 1,
        internedData: {
          eventCategories: [{ iid: 1, name: "cuda" }],
          debugAnnotationNames: [
            { iid: 1, name: "launch" },
            { iid: 2, name: "grid" },
          ],
          debugAnnotationStringValues: [
            { iid: 1, str: new TextEncoder().encode("vector_add") },
          ],
          sourceLocations: [
            {
              iid: 1,
              fileName: "/src/cuda.ts",
              functionName: "launch",
              lineNumber: 88,
            },
          ],
          buildIds: [{ iid: 1, str: Uint8Array.from([1, 2, 3]) }],
          mappingPaths: [
            { iid: 1, str: new TextEncoder().encode("libcuda.so") },
          ],
          sourcePaths: [
            { iid: 1, str: new TextEncoder().encode("/src/cuda.ts") },
          ],
          functionNames: [
            { iid: 1, str: new TextEncoder().encode("launch") },
          ],
          mappings: [
            {
              iid: 1,
              buildId: 1,
              start: 0x1000,
              end: 0x9000,
              pathStringIds: [1],
            },
          ],
          frames: [
            {
              iid: 1,
              functionNameId: 1,
              mappingId: 1,
              relPc: 0x123,
              sourcePathIid: 1,
              lineNumber: 88,
              kind: protos.Frame.Kind.KIND_NATIVE,
            },
          ],
          callstacks: [{ iid: 1, frameIds: [1] }],
        },
      },
      {
        trackDescriptor: {
          uuid: 2,
          parentUuid: 1,
          name: "Kernel lane",
          siblingMergeBehavior:
            protos.TrackDescriptor.SiblingMergeBehavior
              .SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY,
          siblingMergeKey: "kernels",
        },
      },
      {
        timestamp: 100,
        timestampClockId: 65,
        trackEvent: {
          type: protos.TrackEvent.Type.TYPE_INSTANT,
          trackUuid: 2,
          categoryIids: [1],
          sourceLocationIid: 1,
          callstackIid: 1,
          debugAnnotations: [
            {
              nameIid: 1,
              dictEntries: [
                {
                  nameIid: 2,
                  arrayValues: [
                    { uintValue: 128 },
                    { uintValue: 2 },
                    { uintValue: 1 },
                  ],
                },
                { name: "stream", pointerValue: 0xfeed },
                { name: "kernel", stringValueIid: 1 },
              ],
            },
          ],
        },
      },
      {
        timestamp: 110,
        trackEvent: {
          type: protos.TrackEvent.Type.TYPE_INSTANT,
          trackUuid: 2,
          sourceLocation: {
            fileName: "/src/cuda.ts",
            functionName: "launch",
            lineNumber: 88,
          },
          callstack: {
            frames: [
              {
                functionName: "launch",
                sourceFile: "/src/cuda.ts",
                lineNumber: 88,
              },
            ],
          },
        },
      },
      {
        timestamp: 120,
        trackEvent: {
          trackUuid: 2,
          legacyEvent: {
            phase: "X".charCodeAt(0),
            durationUs: 20,
            threadDurationUs: 10,
            threadInstructionDelta: 7,
            globalId: 0x123,
            idScope: "scope",
            useAsyncTts: true,
            bindId: 0x456,
            bindToEnclosing: true,
            flowDirection: protos.TrackEvent.LegacyEvent.FlowDirection.FLOW_INOUT,
            instantEventScope:
              protos.TrackEvent.LegacyEvent.InstantEventScope.SCOPE_PROCESS,
            pidOverride: 10,
            tidOverride: 11,
          },
        },
      },
      {
        tracePacketDefaults: { timestampClockId: 65 },
      },
      {
        clockSnapshot: {
          primaryTraceClock: protos.BuiltinClock.BUILTIN_CLOCK_MONOTONIC,
          clocks: [
            {
              clockId: 65,
              timestamp: 1_000,
              isIncremental: true,
              unitMultiplierNs: 10,
            },
            {
              clockId: protos.BuiltinClock.BUILTIN_CLOCK_MONOTONIC,
              timestamp: 20_000,
            },
          ],
        },
      },
    ],
  });

  const verificationError = protos.Trace.verify(trace);
  assert.equal(verificationError, null);

  const decoded = protos.Trace.decode(protos.Trace.encode(trace).finish());
  assert.equal(decoded.packet[0].internedData.eventCategories[0].name, "cuda");
  assert.equal(
    decoded.packet[1].trackDescriptor.siblingMergeBehavior,
    protos.TrackDescriptor.SiblingMergeBehavior
      .SIBLING_MERGE_BEHAVIOR_BY_SIBLING_MERGE_KEY,
  );
  assert.equal(decoded.packet[1].trackDescriptor.siblingMergeKey, "kernels");
  assert.equal(
    Number(
      decoded.packet[2].trackEvent.debugAnnotations[0].dictEntries[0]
        .arrayValues[0].uintValue,
    ),
    128,
  );
  assert.equal(
    Number(
      decoded.packet[2].trackEvent.debugAnnotations[0].dictEntries[1]
        .pointerValue,
    ),
    0xfeed,
  );
  assert.equal(Number(decoded.packet[2].trackEvent.callstackIid), 1);
  assert.equal(
    decoded.packet[3].trackEvent.callstack.frames[0].functionName,
    "launch",
  );
  assert.equal(decoded.packet[4].trackEvent.legacyEvent.phase, 88);
  assert.equal(decoded.packet[5].tracePacketDefaults.timestampClockId, 65);
  assert.equal(
    Number(decoded.packet[6].clockSnapshot.clocks[0].unitMultiplierNs),
    10,
  );
});
