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

### Maintaining the registry

`registry.toml` is generated. Dependency lists are parsed from each Hoon file's
import header rather than hand-maintained, so they don't drift out of sync with
upstream.

```sh
# regenerate registry.toml from upstream checkouts
scripts/regen-registry.py generate

# fail (non-zero) if registry.toml has drifted from what the sources imply
scripts/regen-registry.py generate --check

# check that every dependency/alias resolves and every file exists
scripts/regen-registry.py validate
```

To bump an upstream, edit its `ref` in the `WORKSPACES` table at the top of
`scripts/regen-registry.py` and re-run `generate`. The script reuses local
checkouts (defaults under `/tmp`, override with `--checkout name=/path`) and
shallow-clones at the pinned ref otherwise. Requires Python 3.11+ (standard
library only). The curated `urbit` selection and all aliases also live in that
config table.
