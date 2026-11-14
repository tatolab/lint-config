# lint-config

The lint rules every Tatolab repository runs. A repository pins this one at a
commit and runs its rules locally, in the repository's own lint command, so an
agent or a person checks as they work. CI runs the same command to verify.

A rule changes here, by pull request, and reaches a repository when that
repository moves its pin.

## Layout

- `ast-grep/rust/` — ast-grep rules for Rust, each with its `valid` and
  `invalid` cases under `rule-tests/`. A consumer's `sgconfig.yml` lists
  `ruleDirs` and `testConfigs` pointing here.
- `eslint/` — the shared ESLint flat config.
- `file-size/` — the file-size lint: no hand-written file over 1,000 lines,
  with a per-repository exception list that may only shrink.
- `rust/` — the reference `[workspace.lints]` table and `clippy.toml`, and the
  check a consumer runs to prove its own table matches.

## Licence

MIT. See `LICENSE`.
