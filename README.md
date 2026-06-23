# TYPHOON
## TYPical HOON Registry

**Status:** Works with Nockup. `nockchain` is pinned at `6d29078` (2026-06-22); see
`registry.toml` for the exact ref of every workspace. Update requests are welcome
as issues or PRs.

![](./img/hero.jpg)

Typhoon is a registry of common Hoon projects for use with [Nockup](https://github.com/nockchain/nockchain/tree/master/crates/nockup) or other Hoon projects.

Nockup consumes a single file: [`registry.toml`](./registry.toml) on the `master`
branch. It declares **workspaces** (pinned upstream git repos), **packages** (a
named Hoon source file plus its dependency closure), and **aliases** (short names).

### Indexed upstreams

| Workspace | Source | What |
| --- | --- | --- |
| `urbit` | [urbit/urbit](https://github.com/urbit/urbit) | `/sys` stdlib (hoon, lull, zuse, arvo), vanes, `/lib` |
| `nockchain` | [nockchain/nockchain](https://github.com/nockchain/nockchain) | Nockchain stdlib, tx-engine, dumbnet, wallet, bridge |
| `numerics-*` | [urbit/numerics](https://github.com/urbit/numerics) | `lagoon` (linear algebra), `saloon` (decompositions), math primitives |
| `sequent` | [jackfoxy/sequent](https://github.com/jackfoxy/sequent) | `seq` list operations |
| `yard` | [urbit/yard](https://github.com/urbit/yard) | curated general-purpose libs (string, regex, csv, mip, math, etch, cram, number-to-words) |

### Maintaining the registry

`registry.toml` is a **generated artifact — do not hand-edit it.** The source of
truth is the config tables at the top of
[`scripts/regen-registry.py`](./scripts/regen-registry.py) plus the upstream
source files themselves: dependency lists are parsed from each Hoon file's
`/=` / `/+` / `/-` import header, so they cannot drift out of sync with upstream.
CI (`.github/workflows/registry.yml`) runs `generate --check` on every push and
PR, so a hand-edit that bypasses the generator fails the build.

Requires Python 3.11+ (standard library only) and `git`.

```sh
# regenerate registry.toml from the pinned upstreams
scripts/regen-registry.py generate

# fail (non-zero) if registry.toml has drifted from the sources (CI runs this)
scripts/regen-registry.py generate --check

# check that every dependency/alias resolves and every file exists
scripts/regen-registry.py validate
```

The script reuses local checkouts (defaults under your temp dir; override with
`--checkout name=/path`) and shallow-clones each upstream at its pinned ref
otherwise.

#### Common tasks

Each is an edit to a config table at the top of `scripts/regen-registry.py`,
followed by `generate` → `generate --check` → `validate`, then committing the
regenerated `registry.toml` **together with** the script change.

- **Bump an upstream** — change its `ref` in `WORKSPACES` and regenerate. Read
  the `generate --check` output as a changelog (added / removed / changed
  packages), and **watch for `… not a package` warnings**: they flag an upstream
  file that now depends on something the registry doesn't track yet (this is how
  new load-bearing libraries such as `h-zoon` or `asert` surfaced). Add genuinely
  new libraries deliberately; skip internal or test-only modules.

- **Add a package to an existing workspace** — for `nockchain` (a `FLAT_FAMILIES`
  entry) every non-test `.hoon` under the root is picked up automatically, so just
  regenerate. For the curated / `FORD_FAMILIES` workspaces (`urbit`, `numerics`,
  `sequent`, `yard`) add the file's stem to the relevant `stems` list (or to
  `URBIT_PACKAGES` for `urbit`).

- **Add a new workspace** — add an entry to `WORKSPACES` (git URL, `ref`,
  description, `root_path`), then say how to enumerate its packages: a
  `FLAT_FAMILIES` entry (walk a tree, parse flat `/=` imports) or a
  `FORD_FAMILIES` entry (explicit `lib`/`sur` file stems, ford `/+` / `/-`
  imports). The `numerics` and `yard` blocks are worked examples.

- **Add an alias** — add a `(name, target)` pair to `ALIASES`.

When you bump `nockchain`, update the ref quoted in the **Status** line at the top
of this file too.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the maintenance policy (on-demand
cadence, contribution rules) and the full upgrade runbook.
