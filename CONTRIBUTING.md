# Contributing to Typhoon

Typhoon is the package registry that [Nockup](https://github.com/nockchain/nockchain/tree/master/crates/nockup)
reads to resolve Hoon dependencies. It indexes pinned upstream git repositories
(`urbit/urbit`, `nockchain/nockchain`, `urbit/numerics`, `jackfoxy/sequent`) and
exposes their Hoon source files as named packages with explicit dependency
closures.

## Golden rule: `registry.toml` is generated — do not hand-edit it

`registry.toml` is a build artifact produced by
[`scripts/regen-registry.py`](./scripts/regen-registry.py). Dependency lists are
**parsed from each Hoon file's import header**, not maintained by hand, so they
cannot silently drift out of sync with the upstream sources.

The source of truth is the configuration table at the top of the script:

- **`WORKSPACES`** — upstream repos and the pinned `ref` for each.
- **`URBIT_PACKAGES`** — the curated `urbit` selection and its layering (not
  import-derivable, so it is explicit).
- **`FLAT_FAMILIES` / `FORD_FAMILIES`** — which files to include for the
  import-derived workspaces and how their imports resolve.
- **`ALIASES`** — short names.

CI runs `generate --check` on every push and PR; a hand-edit that bypasses the
generator will fail the build.

## Tooling

Requires Python 3.11+ (standard library only) and `git`.

```sh
# Regenerate registry.toml from the pinned sources.
scripts/regen-registry.py generate

# Fail (non-zero) if registry.toml has drifted from what the sources imply.
# This is what CI runs. It shallow-clones nockchain / numerics / sequent on
# demand (urbit is explicit config and is never cloned).
scripts/regen-registry.py generate --check

# Confirm every dependency and alias resolves, and every file exists
# (file checks are skipped for any upstream without a local checkout).
scripts/regen-registry.py validate
```

By default the script reuses checkouts under your temp dir and shallow-clones at
the pinned ref otherwise. Point it at existing checkouts with
`--checkout nockchain=/path` (repeatable: `numerics`, `sequent`).

## Upgrade runbook (bumping an upstream)

1. Edit the `ref` for the workspace in the `WORKSPACES` table.
2. Run `scripts/regen-registry.py generate`.
3. Run `scripts/regen-registry.py generate --check` and read its output as a
   changelog: it reports added / removed / changed packages. **Read the
   warnings** — an `import ... not a package` warning means an upstream file now
   depends on something the registry does not track yet (this is exactly how a
   new load-bearing library such as `h-zoon` or `asert` surfaces). Add it (and
   any genuinely new app) deliberately; skip things that are not reusable
   libraries (e.g. test runners).
4. Run `scripts/regen-registry.py validate`.
5. Smoke-test with Nockup: create a throwaway project whose `nockapp.toml`
   depends on an affected package and run `nockup project init`; confirm the
   dependency closure resolves.
6. Commit the regenerated `registry.toml` together with the script change, and
   push to `master`.

> Nockup reads `registry.toml` only from this repo's **`master`** branch
> (the URL is hardcoded in nockup, with no local override), so changes are not
> testable through nockup until they are pushed to `master`.

## Maintenance policy

- **Cadence: on-demand.** Refs are bumped when a user requests it or when a
  breaking upstream change lands. Open an issue or PR to request a bump.
  Because every workspace is pinned by commit, the registry is deterministic
  and reproducible between bumps.
- **New packages** go through the runbook above; reusable libraries are added,
  internal/test-only modules are not.
- **Contributions** should change the script configuration and include the
  regenerated `registry.toml` in the same commit. CI enforces that the two
  agree.
