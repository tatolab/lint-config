// The ESLint rules every Tatolab TypeScript repository runs. A repository spreads
// `tatolabTypeScriptLintConfig(...)` first in its own flat config and adds its own rules after.

import tseslint from "typescript-eslint";

const TEST_CALLEES = new Set(["test", "it", "describe"]);
const FOCUSING_OR_SKIPPING = new Set(["only", "skip", "todo"]);

/** Refuses `test.only`, `it.skip`, `describe.todo` and the like: a test file runs every test it holds. */
const noFocusedOrSkippedTestRule = {
  meta: { type: "problem", schema: [], messages: { focusedOrSkipped: "No focused, skipped or todo test: `{{call}}`." } },
  create(context) {
    return {
      MemberExpression(node) {
        if (node.object.type !== "Identifier" || node.property.type !== "Identifier") return;
        if (!TEST_CALLEES.has(node.object.name) || !FOCUSING_OR_SKIPPING.has(node.property.name)) return;
        context.report({ node, messageId: "focusedOrSkipped", data: { call: `${node.object.name}.${node.property.name}` } });
      },
    };
  },
};

/** The plugin holding Tatolab's own rules, under the `tatolab` prefix. */
export const tatolabLintPlugin = { meta: { name: "@tatolab/lint-config" }, rules: { "no-focused-or-skipped-test": noFocusedOrSkippedTestRule } };

/**
 * The shared rules for `files`, and the test rule for `testFiles`: no `any`, no type assertion but `as const`, no non-null
 * `!`, no `@ts-` comment, no console or debugger outside tests, and every disable directive used.
 */
export function tatolabTypeScriptLintConfig({ files, testFiles }) {
  return [
    {
      files,
      languageOptions: { parser: tseslint.parser },
      plugins: { "@typescript-eslint": tseslint.plugin, tatolab: tatolabLintPlugin },
      linterOptions: { reportUnusedDisableDirectives: "error" },
      rules: {
        "no-console": "error",
        "no-debugger": "error",
        "@typescript-eslint/no-explicit-any": "error",
        "@typescript-eslint/consistent-type-assertions": ["error", { assertionStyle: "never" }],
        "@typescript-eslint/no-non-null-assertion": "error",
        "@typescript-eslint/ban-ts-comment": "error",
      },
    },
    {
      files: testFiles,
      rules: { "no-console": "off", "no-debugger": "off", "tatolab/no-focused-or-skipped-test": "error" },
    },
  ];
}
