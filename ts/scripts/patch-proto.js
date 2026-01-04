import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const targetPath = resolve(__dirname, "../src/proto/perfetto_pb.js");

const source = fs.readFileSync(targetPath, "utf8");
if (source.includes("const $protobuf = $protobufModule.default ?? $protobufModule")) {
  process.exit(0);
}

const pattern = /import \\* as \\$protobuf from \"protobufjs\\/minimal\";/;
if (!pattern.test(source)) {
  throw new Error("Expected protobufjs import not found in generated file.");
}

const patched = source.replace(
  pattern,
  "import * as $protobufModule from \\\"protobufjs/minimal\\\";\\n\\nconst $protobuf = $protobufModule.default ?? $protobufModule;"
);

fs.writeFileSync(targetPath, patched, "utf8");
