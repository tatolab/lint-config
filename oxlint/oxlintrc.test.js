import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, test } from "node:test";
import { fileURLToPath } from "node:url";

const SHARED_CONFIG = fileURLToPath(new URL("./oxlintrc.json", import.meta.url));
const OXLINT = fileURLToPath(new URL("../node_modules/.bin/oxlint", import.meta.url));

/** A consumer's folder whose own `.oxlintrc.json` extends the shared config by a relative path, as a pinned repository's does. */
const consumerFolder = mkdtempSync(path.join(tmpdir(), "tatolab-oxlint-"));
writeFileSync(path.join(consumerFolder, ".oxlintrc.json"), JSON.stringify({ extends: [path.relative(consumerFolder, SHARED_CONFIG)] }));
after(() => rmSync(consumerFolder, { recursive: true, force: true }));

/** Oxlint's JSON report for `code` written at `filename` in the consumer's folder. */
function oxlintReport(code, filename) {
  const filePath = path.join(consumerFolder, filename);
  mkdirSync(path.dirname(filePath), { recursive: true });
  writeFileSync(filePath, code);
  const run = spawnSync(OXLINT, ["--format", "json", filename], { cwd: consumerFolder, encoding: "utf8" });
  rmSync(filePath);
  return JSON.parse(run.stdout);
}

/** The rule codes oxlint reports for `code` in a file named `filename`, such as `typescript(no-explicit-any)`. */
function ruleCodesReported(code, filename) {
  return oxlintReport(code, filename).diagnostics.map((diagnostic) => diagnostic.code);
}

test("the config turns on the six rules and no others", () => {
  assert.equal(oxlintReport("export const quiet = 1;\n", "src/quiet.ts").number_of_rules, 6);
});

test("a source file with no any, assertion, non-null, ts comment or console passes, as const and a described ts-expect-error included", () => {
  const code = "export const sizes = [1, 2] as const;\n// @ts-expect-error: the reason it is expected\nexport function width(size: number): number { return size * 2; }\n";
  assert.deepEqual(ruleCodesReported(code, "src/sizes.ts"), []);
});

test("any, a type assertion, a non-null assertion, a ts comment, console and debugger are each refused in source", () => {
  const code = "// @ts-ignore\nexport function f(value: any) { const text = value as string; const size = <number>value; debugger; console.log(text!.length, size); }\n";
  assert.deepEqual(
    new Set(ruleCodesReported(code, "src/f.ts")),
    new Set(["typescript(ban-ts-comment)", "typescript(no-explicit-any)", "typescript(consistent-type-assertions)", "eslint(no-debugger)", "eslint(no-console)", "typescript(no-non-null-assertion)"]),
  );
});

test("a ts-expect-error without a description is refused", () => {
  assert.deepEqual(ruleCodesReported("// @ts-expect-error\nexport const planted = 1;\n", "src/f.ts"), ["typescript(ban-ts-comment)"]);
});

test("a test file may log and stop in the debugger, but holds the type rules", () => {
  assert.deepEqual(ruleCodesReported('console.log("seen");\ndebugger;\nexport const planted = JSON.parse("1") as number;\n', "src/f.test.ts"), ["typescript(consistent-type-assertions)"]);
});

test("the rules hold in a .tsx file", () => {
  assert.deepEqual(ruleCodesReported("export const Planted = (props: any) => <span>{props.label}</span>;\n", "src/f.tsx"), ["typescript(no-explicit-any)"]);
});
