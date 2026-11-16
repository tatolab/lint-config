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
  assert.deepEqual(ruleIdsReported("// eslint-disable-next-line no-console -- the line logs\nexport const quiet = 1;\n", "src/quiet.ts"), [null]);
});

test("a described disable directive silences its line", () => {
  assert.deepEqual(ruleIdsReported("// eslint-disable-next-line no-console -- the one line that reports to the terminal\nconsole.log(1);\n", "src/f.ts"), []);
});

test("a disable or enable directive without a description is refused", () => {
  const code = "/* eslint-disable no-console */\nconsole.log(1);\n/* eslint-enable no-console */\n// eslint-disable-next-line no-debugger\ndebugger;\n";
  assert.deepEqual(ruleIdsReported(code, "src/f.ts"), ["tatolab/no-undescribed-lint-directive", "tatolab/no-undescribed-lint-directive", "tatolab/no-undescribed-lint-directive"]);
});

test("an inline configuration comment is refused", () => {
  assert.deepEqual(new Set(ruleIdsReported("/* eslint no-console: off */\n/* global window */\nexport const quiet = 1;\n", "src/f.ts")), new Set(["tatolab/no-undescribed-lint-directive"]));
});

test("a repository with no test files passes an empty testFiles", () => {
  const configWithNoTests = tatolabTypeScriptLintConfig({ files: ["**/*.ts"], testFiles: [] });
  const reported = new Linter({ configType: "flat" }).verify("console.log(1);\n", configWithNoTests, "src/f.ts").map((message) => message.ruleId);
  assert.deepEqual(reported, ["no-console"]);
});
