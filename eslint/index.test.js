import assert from "node:assert/strict";
import { test } from "node:test";
import { Linter } from "eslint";
import { tatolabTypeScriptLintConfig } from "./index.js";

/** The shared config followed by one rule of the repository's own, as a consumer spreads it. */
const config = [...tatolabTypeScriptLintConfig({ files: ["**/*.ts"], testFiles: ["**/*.test.ts"] }), { files: ["**/*.ts"], rules: { "no-var": "error" } }];

/** The rule ids ESLint reports for `code` in a file named `filename`. */
function ruleIdsReported(code, filename) {
  return new Linter({ configType: "flat" }).verify(code, config, filename).map((message) => message.ruleId);
}

test("a source file with no undescribed directive passes", () => {
  assert.deepEqual(ruleIdsReported("export const sizes = [1, 2] as const;\nexport function width(size: number): number { return size * 2; }\n", "src/sizes.ts"), []);
});

test("the rules oxlint runs are not reported by ESLint", () => {
  const code = "// @ts-ignore\nexport function f(value: any) { const text = value as string; debugger; console.log(text!.length); }\n";
  assert.deepEqual(ruleIdsReported(code, "src/f.ts"), []);
});

test("a test file may not focus or skip a test", () => {
  assert.deepEqual(ruleIdsReported('test.only("one", () => {});\nit.skip("two", () => {});\n', "src/f.test.ts"), ["tatolab/no-focused-or-skipped-test", "tatolab/no-focused-or-skipped-test"]);
});

test("a disable directive that disables nothing is reported", () => {
  assert.deepEqual(ruleIdsReported("// eslint-disable-next-line no-var -- the line declares with var\nexport const quiet = 1;\n", "src/quiet.ts"), [null]);
});

test("a described disable directive silences its line", () => {
  assert.deepEqual(ruleIdsReported("// eslint-disable-next-line no-var -- the one line that must hoist\nvar hoisted = 1;\nexport { hoisted };\n", "src/f.ts"), []);
});

test("a disable or enable directive without a description is refused", () => {
  const code = "/* eslint-disable no-var */\nvar a = 1;\n/* eslint-enable no-var */\n// eslint-disable-next-line no-var\nvar b = 2;\nexport { a, b };\n";
  assert.deepEqual(ruleIdsReported(code, "src/f.ts"), ["tatolab/no-undescribed-lint-directive", "tatolab/no-undescribed-lint-directive", "tatolab/no-undescribed-lint-directive"]);
});

test("an oxlint directive without a description is refused, and a described one passes", () => {
  const code = "// oxlint-disable-next-line no-console\nconsole.log(1);\n/* oxlint-disable no-debugger */\n// oxlint-disable-line no-console -- the one line that reports to the terminal\n";
  assert.deepEqual(ruleIdsReported(code, "src/f.ts"), ["tatolab/no-undescribed-lint-directive", "tatolab/no-undescribed-lint-directive"]);
});

test("an inline configuration comment is refused", () => {
  assert.deepEqual(new Set(ruleIdsReported("/* eslint no-console: off */\n/* global window */\nexport const quiet = 1;\n", "src/f.ts")), new Set(["tatolab/no-undescribed-lint-directive"]));
});

test("a repository with no test files passes an empty testFiles", () => {
  const configWithNoTests = tatolabTypeScriptLintConfig({ files: ["**/*.ts"], testFiles: [] });
  const reported = new Linter({ configType: "flat" }).verify('test.only("one", () => {});\n// eslint-disable-line no-var\n', configWithNoTests, "src/f.test.ts").map((message) => message.ruleId);
  assert.deepEqual(reported, ["tatolab/no-undescribed-lint-directive", null]);
});
