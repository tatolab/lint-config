// The ESLint rules every Tatolab TypeScript repository runs. A repository spreads
// `tatolabTypeScriptLintConfig(...)` first in its own flat config and adds its own rules after.
// The rules oxlint can run (no `any`, no type assertion, no non-null `!`, no `@ts-` comment, no console or
// debugger outside tests) live in `oxlint/oxlintrc.json` instead, so no rule is reported by both linters.

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

const DISABLE_OR_ENABLE_DIRECTIVE = /^((eslint|oxlint)-disable(-next-line|-line)?|(eslint|oxlint)-enable)(\s|$)/;
const INLINE_CONFIGURATION_COMMENT = /^(eslint|eslint-env|global|globals|exported)\s/;

/**
 * Refuses an ESLint or oxlint disable or enable directive with no `-- description`, and any inline configuration comment
 * (`/* eslint rule: off *\/`, `/* global *\/`): a rule is switched off in `eslint.config.js`, or for one line with a reason.
 */
const noUndescribedLintDirectiveRule = {
  meta: {
    type: "problem",
    schema: [],
    messages: {
      undescribedDirective: "A disable directive says why after ` -- `: `{{directive}}`.",
      inlineConfiguration: "Rules are configured in eslint.config.js, not in an inline `{{directive}}` comment.",
    },
  },
  create(context) {
    return {
      Program() {
        for (const comment of context.sourceCode.getAllComments()) {
          const text = comment.value.trim();
          const directive = text.split(/\s/)[0];
          if (DISABLE_OR_ENABLE_DIRECTIVE.test(text)) {
            const description = text.split(/\s--\s/)[1];
            if (description === undefined || description.trim() === "") context.report({ loc: comment.loc, messageId: "undescribedDirective", data: { directive } });
          } else if (INLINE_CONFIGURATION_COMMENT.test(text)) {
            context.report({ loc: comment.loc, messageId: "inlineConfiguration", data: { directive } });
          }
        }
      },
    };
  },
};

/** The plugin holding Tatolab's own rules, under the `tatolab` prefix. */
export const tatolabLintPlugin = {
  meta: { name: "@tatolab/lint-config" },
  rules: { "no-focused-or-skipped-test": noFocusedOrSkippedTestRule, "no-undescribed-lint-directive": noUndescribedLintDirectiveRule },
};

/**
 * The shared rules for `files`, and the test rule for `testFiles` (which may be empty): every ESLint disable directive used, every
 * ESLint or oxlint directive described, and no focused or skipped test.
 */
export function tatolabTypeScriptLintConfig({ files, testFiles }) {
  return [
    {
      files,
      languageOptions: { parser: tseslint.parser },
      plugins: { "@typescript-eslint": tseslint.plugin, tatolab: tatolabLintPlugin },
      linterOptions: { reportUnusedDisableDirectives: "error" },
      rules: { "tatolab/no-undescribed-lint-directive": "error" },
    },
    ...(testFiles.length > 0 ? [{ files: testFiles, rules: { "tatolab/no-focused-or-skipped-test": "error" } }] : []),
  ];
}
