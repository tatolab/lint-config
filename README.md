# lint-config

The lint rules every Tatolab repository runs. A repository pins this one at a
commit and runs its rules locally, in the repository's own lint command, so an
agent or a person checks as they work. CI runs the same command to verify.

A rule changes here, by pull request, and reaches a repository when that
repository moves its pin. Every file has a code owner (`.github/CODEOWNERS`),
and `main` takes a change only through a pull request the code owner approves.

## What it holds

- `ast-grep/rust/rules/`: ast-grep rules for Rust library source, each with
  `valid` and `invalid` cases in `ast-grep/rust/rule-tests/`:
  - `no-inline-test-module`: a `#[cfg(test)]` module lives in its own file.
  - `no-glob-re-export-outside-a-prelude`: `pub use …::*;` only in a `prelude`.
  - `no-path-attribute`: no `#[path]` in library source.

  A consumer's `sgconfig.yml` lists `ruleDirs: [<pin>/ast-grep/rust/rules]`.
- `ast-grep/check_ast_grep_scan.py`: runs `ast-grep scan` and fails on each
  finding not in the repository's exception list of `<count> <rule-id> <path>`
  entries. The list works like the file-size check's: a listed file may not
  gain findings, an entry with none left must go, and `--compare-to` fails on a
  new entry or a raised count. ast-grep skips hidden directories, so a rule for
  `.github/` needs `--path . --path .github`.
- `eslint/index.js`: `tatolabTypeScriptLintConfig({ files, testFiles })`, the
  shared ESLint flat config. A consumer installs this repository as a git
  dependency pinned by SHA and spreads it first in its own config:

  ```js
  import { tatolabTypeScriptLintConfig } from "@tatolab/lint-config/eslint";
  export default [...tatolabTypeScriptLintConfig({ files: ["src/**/*.{ts,tsx}"], testFiles: ["src/**/*.test.{ts,tsx}"] }), /* the repository's own rules */];
  ```

  It refuses a focused or skipped test, an unused disable directive, and an
  ESLint or oxlint directive with no `-- description`.
- `oxlint/oxlintrc.json`: the shared oxlint config, holding the rules oxlint
  runs so ESLint does not run them too: no `any`, no type assertion but
  `as const`, no non-null `!`, no `@ts-` comment, and no console or debugger
  outside a `*.test.*` or `*.spec.*` file. Oxlint resolves `extends` by path,
  so a consumer installs `oxlint` and extends the pinned copy from its own
  `.oxlintrc.json`:

  ```json
  { "extends": ["./node_modules/@tatolab/lint-config/oxlint/oxlintrc.json"] }
  ```
- `file-size/check_file_sizes.py`: no hand-written file over 1,000 lines. Files
  not split yet are listed as `<lines> <path>` in the repository's exception
  list. A listed file may not grow, an entry whose file is back under the limit
  must go, and `--compare-to origin/main` fails on a new entry or a raised
  count. Generated files (an `@generated` or `do not edit` marker, in any case, in the first
  five lines), `vendor/` and `node_modules/` are not checked; `--exclude` adds
  more.
- `rust/check_module_files.py`: a Rust module with children is `foo/mod.rs`,
  never `foo.rs` beside `foo/`. `--exceptions` takes a list of `1 <path>`
  entries for the files not moved yet, which may only shrink.
- `rust/workspace-lints.toml`, `rust/clippy.toml` and `rust/check_lint_table.py`:
  the lints every Rust workspace sets at least as strictly. Cargo can't inherit
  lints across repositories, so the check holds a workspace's own
  `[workspace.lints]` and `clippy.toml` to the reference.

The scripts need Python 3 (3.11 or newer for the lint-table check) and run from
the consumer's repository root.

## Testing

```bash
npm ci --ignore-scripts
npm test   # the ESLint and oxlint configs' tests, the scripts' tests and `ast-grep test`
```

`ast-grep` must be on the path; CI installs `ast-grep-cli` 0.51.2.

## Licence

MIT. See `LICENSE`.
