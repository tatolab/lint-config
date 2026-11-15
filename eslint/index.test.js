import assert from "node:assert/strict";
import { test } from "node:test";
import { Linter } from "eslint";
import { tatolabTypeScriptLintConfig } from "./index.js";

const config = tatolabTypeScriptLintConfig({ files: ["**/*.ts"], testFiles: ["**/*.test.ts"] });

/** The rule ids ESLint reports for `code` in a file named `filename`. */
function ruleIdsReported(code, filename) {
  return new Linter({ configType: "flat" }).verify(code, config, filename).map((message) => message.ruleId);
}

test("a source file with no any, assertion, non-null, ts comment or console passes", () => {
  assert.deepEqual(ruleIdsReported("export const sizes = [1, 2] as const;\nexport function width(size: number): number { return size * 2; }\n", "src/sizes.ts"), []);
});

test("any, a type assertion, a non-null assertion, a ts comment, console and debugger are each refused in source", () => {
  const code = "// @ts-ignore\nexport function f(value: any) { const text = value as string; debugger; console.log(text!.length); }\n";
  assert.deepEqual(new Set(ruleIdsReported(code, "src/f.ts")), new Set(["@typescript-eslint/ban-ts-comment", "@typescript-eslint/no-explicit-any", "@typescript-eslint/consistent-type-assertions", "no-debugger", "no-console", "@typescript-eslint/no-non-null-assertion"]));
});

test("a test file may log but may not focus or skip a test", () => {
  assert.deepEqual(ruleIdsReported('console.log("seen");\ntest.only("one", () => {});\nit.skip("two", () => {});\n', "src/f.test.ts"), ["tatolab/no-focused-or-skipped-test", "tatolab/no-focused-or-skipped-test"]);
});

test("a disable directive that disables nothing is reported", () => {
  assert.deepEqual(ruleIdsReported("// eslint-disable-next-line no-console\nexport const quiet = 1;\n", "src/quiet.ts"), [null]);
});
