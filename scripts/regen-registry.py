#!/usr/bin/env python3
"""Regenerate and validate the Typhoon registry (registry.toml).

The registry maps package names to source files in pinned upstream git
workspaces. Most dependency data is derivable from each Hoon file's import
header, so this script regenerates it mechanically instead of by hand.

Three import conventions are handled:

  * "flat"  (nockchain) -- `/= face /common/zoon`; the import target is the
            last whitespace token and maps directly to `nockchain<token>`.
  * "ford"  (urbit/numerics, jackfoxy/sequent) -- `/+ name` (library, lib/) and
            `/- name` (structure, sur/); names resolve within the workspace
            family via lib/sur indexes.
  * "explicit" (urbit) -- the curated /sys + vanes + /lib selection and its
            layering deps are not import-derivable, so they live in CONFIG.

Usage:
    regen-registry.py generate [--output registry.toml]
    regen-registry.py generate --check        # diff vs existing, non-zero if drift
    regen-registry.py validate [registry.toml] # resolvability + file existence

Checkouts for the derived families default to the paths in CHECKOUTS below and
can be overridden with `--checkout family=/path` (repeatable). If a checkout is
missing it is shallow-cloned at the configured ref into a temp cache.

Python 3.11+ (uses tomllib). Standard library only.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(REPO_ROOT, "registry.toml")

# ---------------------------------------------------------------------------
# Configuration: the curated, non-derivable parts of the registry.
# ---------------------------------------------------------------------------

REGISTRY_META = {
    "name": "typhoon",
    "version": "0.1.0",
    "description": "TYPical HOON package registry",
    "url": "https://github.com/sigilante/typhoon",
}
DEFAULT_REF = "latest"

# Workspace definitions, emitted in this order.
WORKSPACES = {
    "urbit": {
        "git_url": "https://github.com/urbit/urbit",
        "ref": "409k",
        "description": "Urbit OS",
        "root_path": "pkg/arvo",
    },
    "nockchain": {
        "git_url": "https://github.com/nockchain/nockchain",
        "ref": "6d29078",
        "description": "Nockchain standard library",
        "root_path": "hoon",
    },
    "numerics-math": {
        "git_url": "https://github.com/urbit/numerics",
        "ref": "043a437",
        "description": "Numerics: shared math primitives (libmath desk)",
        "root_path": "libmath/desk",
    },
    "numerics-lagoon": {
        "git_url": "https://github.com/urbit/numerics",
        "ref": "043a437",
        "description": "Lagoon: vector/matrix linear algebra (lagoon desk)",
        "root_path": "lagoon/desk",
    },
    "numerics-saloon": {
        "git_url": "https://github.com/urbit/numerics",
        "ref": "043a437",
        "description": "Saloon: eigen/decomposition routines (saloon desk)",
        "root_path": "saloon/desk",
    },
    "sequent": {
        "git_url": "https://github.com/jackfoxy/sequent",
        "ref": "7fc95fd",
        "description": "Sequent: list operations for mortal developers",
        "root_path": "desk",
    },
    "yard": {
        "git_url": "https://github.com/urbit/yard",
        "ref": "ce5cb82",
        "description": "Yard: curated community Hoon libraries (Urbit Foundation)",
        "root_path": "desk",
    },
    "nockapp-pack": {
        "git_url": "https://github.com/sigilante/nockapp-pack",
        "ref": "c1b7e566baf5ebf3506ec1aa11b9a50f9c286b5c",
        "description": "NockApp Pack: example NockApps (sigilante/nockapp-pack)",
        "root_path": "examples",
    },
    "nockasm": {
        "git_url": "https://github.com/sigilante/nockasm",
        "ref": "50e9e72",
        "description": "Nockasm: legible Nock assembly (expander, target IR, jam lifter)",
        "root_path": "desk",
    },
}

# Curated urbit packages (name, path, file, dependencies) -- not import-derived.
URBIT_PACKAGES = [
    ("urbit/hoon", "sys", "hoon.hoon", []),
    ("urbit/lull", "sys", "lull.hoon", ["urbit/hoon"]),
    ("urbit/zuse", "sys", "zuse.hoon", ["urbit/lull"]),
    ("urbit/arvo", "sys", "arvo.hoon", ["urbit/lull", "urbit/zuse"]),
    ("urbit/ames", "sys/vanes", "ames.hoon", ["urbit/arvo"]),
    ("urbit/behn", "sys/vanes", "behn.hoon", ["urbit/arvo"]),
    ("urbit/clay", "sys/vanes", "clay.hoon", ["urbit/arvo"]),
    ("urbit/dill", "sys/vanes", "dill.hoon", ["urbit/arvo"]),
    ("urbit/eyre", "sys/vanes", "eyre.hoon", ["urbit/arvo"]),
    ("urbit/gall", "sys/vanes", "gall.hoon", ["urbit/arvo"]),
    ("urbit/iris", "sys/vanes", "iris.hoon", ["urbit/arvo"]),
    ("urbit/jael", "sys/vanes", "jael.hoon", ["urbit/arvo"]),
    ("urbit/khan", "sys/vanes", "khan.hoon", ["urbit/arvo"]),
    ("urbit/lick", "sys/vanes", "lick.hoon", ["urbit/arvo"]),
    ("urbit/bits", "lib", "bits.hoon", []),
    ("urbit/list", "lib", "list.hoon", []),
    ("urbit/map", "lib", "map.hoon", []),
    ("urbit/math", "lib", "math.hoon", []),
    ("urbit/mapset", "lib", "mapset.hoon", ["urbit/map"]),
    ("urbit/set", "lib", "set.hoon", []),
    ("urbit/tiny", "lib", "tiny.hoon", []),
]

# NockApp Pack example apps (explicit; self-contained, so no cross-workspace deps).
NOCKAPP_PACKAGES = [
    ("nockapp/chain-watch",  "chain-watch/hoon/app",  "app.hoon",    []),
    ("nockapp/nock-price",   "nock-price/hoon/app",   "app.hoon",    []),
    ("nockapp/balance-api",  "balance-api/hoon/app",  "app.hoon",    []),
    ("nockapp/token-price",  "token-price/hoon/app",  "app.hoon",    []),
    ("nockapp/http-counter", "http-counter/hoon/app", "app.hoon",    []),
    ("nockapp/http-static",  "http-static/hoon/app",  "app.hoon",    []),
    ("nockapp/echo-grpc",    "echo-grpc/hoon/app",    "listen.hoon", []),
    ("nockapp/hello-basic",  "hello-basic/hoon/app",  "app.hoon",    []),
    ("nockapp/minesweeper",  "minesweeper/hoon/app",  "app.hoon",    []),
    ("nockapp/common-blog",  "common-blog/hoon/app",  "app.hoon",    []),
    ("nockapp/wordle",       "wordle/hoon/app",       "app.hoon",    []),
    ("nockapp/conway",       "conway/hoon/app",       "app.hoon",    []),
    ("nockapp/solitaire",    "solitaire/hoon/app",    "app.hoon",    []),
    ("nockapp/gematria",     "gematria/hoon/app",     "app.hoon",    []),
]

# Derived families: import headers are parsed to compute dependencies.
#
# flat family (nockchain): walk the workspace root, include every *.hoon except
# the excluded subtrees / suffixes; package name = "<prefix>/<relpath-no-ext>".
#
# ford family (numerics, sequent): explicit file specs per workspace so we never
# pick up tests, *-old, or symlinks. A "lib" file installs under lib/ and is the
# `/+` target; a "sur" file installs under sur/ and is the `/-` target.
FLAT_FAMILIES = [
    {
        "family": "nockchain",
        "checkout": "nockchain",          # CHECKOUTS key
        "workspace": "nockchain",
        "name_prefix": "nockchain",
        "exclude_dirs": ["tests", "jams", "test-jams", "scripts", "apps/roswell"],
        "exclude_suffix": ["-test.hoon"],
    },
]
FORD_FAMILIES = [
    {
        "family": "numerics",
        "checkout": "numerics",
        "name_prefix": "numerics",
        "specs": [
            {"workspace": "numerics-math", "subdir": "lib",
             "stems": ["twoc", "unum", "complex", "fixed", "math"]},
            {"workspace": "numerics-lagoon", "subdir": "sur", "stems": ["lagoon"]},
            {"workspace": "numerics-lagoon", "subdir": "lib", "stems": ["lagoon"]},
            {"workspace": "numerics-saloon", "subdir": "lib", "stems": ["saloon"]},
        ],
    },
    {
        "family": "sequent",
        "checkout": "sequent",
        "name_prefix": "sequent",
        "specs": [
            {"workspace": "sequent", "subdir": "lib", "stems": ["seq"]},
        ],
    },
    {
        # General-purpose, zero-dependency libs from the yard desk. Sail/print
        # (Tier B) and gall-agent helpers (Tier C) are intentionally omitted; the
        # exact duplicates of libs we already index (seq, twoc, test) are skipped.
        "family": "yard",
        "checkout": "yard",
        "name_prefix": "yard",
        "specs": [
            {"workspace": "yard", "subdir": "lib",
             "stems": ["string", "regex", "csv", "mip",
                       "number-to-words", "math", "etch", "cram"]},
        ],
    },
    {
        # Nockasm: single stdlib-only library from the nockasm desk (the desk
        # also carries mar/ and tests/, which are not packages).
        "family": "nockasm",
        "checkout": "nockasm",
        "name_prefix": "sigilante",
        "specs": [
            {"workspace": "nockasm", "subdir": "lib", "stems": ["nockasm"]},
        ],
    },
]

# Default checkout locations (override with --checkout family=/path).
CHECKOUTS = {
    "nockchain": "/tmp/nockchain",
    "numerics": "/tmp/numerics",
    "sequent": "/tmp/sequent-repo",
    "yard": "/tmp/yard",
    "nockasm": "/tmp/nockasm",
}

ALIASES = [
    ("nockchain/eight", "nockchain/common/ztd/eight"),
    ("nockchain/five", "nockchain/common/ztd/five"),
    ("nockchain/four", "nockchain/common/ztd/four"),
    ("nockchain/one", "nockchain/common/ztd/one"),
    ("nockchain/seven", "nockchain/common/ztd/seven"),
    ("nockchain/six", "nockchain/common/ztd/six"),
    ("nockchain/two", "nockchain/common/ztd/two"),
    ("nockchain/zeke", "nockchain/common/zeke"),
    ("nockchain/h-zoon", "nockchain/common/h-zoon"),
    ("nockchain/zoon", "nockchain/common/zoon"),
    ("nockchain/zose", "nockchain/common/zose"),
    ("nockchain/wallet", "nockchain/apps/wallet/wallet"),
    ("lagoon", "numerics/lagoon"),
    ("saloon", "numerics/saloon"),
    ("sequent", "sequent/seq"),
    ("nockasm", "sigilante/nockasm"),
]

# ---------------------------------------------------------------------------
# Checkout management
# ---------------------------------------------------------------------------

_CLONE_CACHE = os.path.join(tempfile.gettempdir(), "typhoon-regen-checkouts")


def get_checkout(key, overrides):
    """Return a local path for the checkout `key`, cloning if necessary."""
    path = overrides.get(key) or CHECKOUTS.get(key)
    if path and os.path.isdir(path):
        return path
    # Clone shallow at the configured ref of the first workspace that uses it.
    ws = next((w for fam in FLAT_FAMILIES + FORD_FAMILIES
               if fam["checkout"] == key
               for w in [WORKSPACES[fam.get("workspace", fam.get("specs", [{}])[0].get("workspace"))]]), None)
    if ws is None:
        raise SystemExit(f"no workspace found for checkout '{key}'")
    os.makedirs(_CLONE_CACHE, exist_ok=True)
    dest = os.path.join(_CLONE_CACHE, key)
    if not os.path.isdir(dest):
        print(f"cloning {ws['git_url']} -> {dest}", file=sys.stderr)
        subprocess.run(["git", "clone", "--filter=blob:none", ws["git_url"], dest], check=True)
        subprocess.run(["git", "-C", dest, "checkout", ws["ref"]], check=True)
    return dest

# ---------------------------------------------------------------------------
# Import parsing
# ---------------------------------------------------------------------------

_FORD_RE = re.compile(r"^/([+\-])\s+(.*)$")
_FLAT_PATH_RE = re.compile(r"^/[=+\-]\s")   # path imports: `/= face /common/zoon`
_NAME_RE = re.compile(r"^/#\s+(\S+)")        # by-name import: `/# softed-constraints`
_DATA_RE = re.compile(r"^/\*\s")             # mark/data import: `/* foo %jam /...` (not a dep)


def _strip_comment(line):
    i = line.find("::")
    return line[:i] if i >= 0 else line


def parse_flat_imports(text):
    """Return ordered, de-duplicated (kind, value) imports.

    kind="path" -> value is a repo path like '/common/zoon'
    kind="name" -> value is a bare stem like 'softed-constraints' (`/#` rune)
    `/*` data/mark imports are intentionally ignored (not package deps).
    """
    out, seen = [], set()

    def add(kind, value):
        if (kind, value) not in seen:
            seen.add((kind, value))
            out.append((kind, value))

    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if _DATA_RE.match(line):
            continue
        m = _NAME_RE.match(line)
        if m:
            add("name", m.group(1))
            continue
        if _FLAT_PATH_RE.match(line):
            tok = line.split()[-1]
            if tok.startswith("/"):
                add("path", tok)
            continue
        # stop scanning once we leave the import preamble
        if line and not line.startswith("/") and out:
            break
    return out


def _clean_ford_name(item):
    item = item.strip()
    if not item:
        return None
    if "=" in item:                 # face=name
        item = item.split("=", 1)[1]
    item = item.lstrip("*")         # /+ *name
    item = item.strip()
    return item or None


def parse_ford_imports(text):
    """Return ordered list of (rune, name) for `/+` and `/-` imports.

    Handles comma-separated lists that span multiple (indented) lines.
    """
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        m = _FORD_RE.match(_strip_comment(lines[i]).rstrip())
        if not m:
            i += 1
            continue
        rune = m.group(1)
        buf = m.group(2)
        # absorb continuation lines while the statement keeps trailing commas
        while buf.rstrip().endswith(",") and i + 1 < len(lines):
            i += 1
            buf += " " + _strip_comment(lines[i]).strip()
        for part in buf.split(","):
            name = _clean_ford_name(part)
            if name:
                out.append((rune, name))
        i += 1
    return out

# ---------------------------------------------------------------------------
# Package generation
# ---------------------------------------------------------------------------


def build_flat_packages(fam, checkout):
    root = os.path.join(checkout, WORKSPACES[fam["workspace"]]["root_path"])
    packages = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith(".hoon"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            rel = rel.replace(os.sep, "/")
            if any(rel == d or rel.startswith(d + "/") for d in fam["exclude_dirs"]):
                continue
            if any(rel.endswith(suf) for suf in fam["exclude_suffix"]):
                continue
            stem = rel[:-5]                      # drop .hoon
            name = f"{fam['name_prefix']}/{stem}"
            pkg_dir = os.path.dirname(stem)
            packages.append({
                "name": name,
                "workspace": fam["workspace"],
                "path": pkg_dir,
                "file": fn,
                "_abs": os.path.join(dirpath, fn),
                "_resolver": "flat",
            })
    return packages


def build_ford_packages(fam, checkout):
    packages = []
    for spec in fam["specs"]:
        ws = WORKSPACES[spec["workspace"]]
        root = os.path.join(checkout, ws["root_path"], spec["subdir"])
        for stem in spec["stems"]:
            abspath = os.path.join(root, stem + ".hoon")
            if spec["subdir"] == "sur":
                name = f"{fam['name_prefix']}/sur/{stem}"
            else:
                name = f"{fam['name_prefix']}/{stem}"
            packages.append({
                "name": name,
                "workspace": spec["workspace"],
                "path": spec["subdir"],
                "file": stem + ".hoon",
                "_abs": abspath,
                "_resolver": "ford",
                "_family": fam["name_prefix"],
                "_subdir": spec["subdir"],
                "_stem": stem,
            })
    return packages


def resolve_dependencies(packages, name_prefix_to_family):
    """Fill each package's `dependencies` list from its import header."""
    # ford indexes, scoped per family
    lib_index, sur_index = {}, {}
    # flat by-name (`/#`) index: stem -> [package names], scoped per name prefix
    stem_index = {}
    for p in packages:
        if p["_resolver"] == "ford":
            fam = p["_family"]
            (sur_index if p["_subdir"] == "sur" else lib_index).setdefault(fam, {})[p["_stem"]] = p["name"]
        elif p["_resolver"] == "flat":
            prefix = p["name"].split("/", 1)[0]
            stem = p["file"][:-5]
            stem_index.setdefault(prefix, {}).setdefault(stem, []).append(p["name"])

    warnings = []
    valid_names = {p["name"] for p in packages}
    for p in packages:
        with open(p["_abs"], "r", encoding="utf-8") as fh:
            text = fh.read()
        deps, seen = [], set()
        if p["_resolver"] == "flat":
            prefix = p["name"].split("/", 1)[0]
            for kind, value in parse_flat_imports(text):
                if kind == "path":
                    dep = prefix + value          # e.g. nockchain + /common/zoon
                    if dep != p["name"] and dep not in valid_names:
                        warnings.append(f"{p['name']}: import {value} -> {dep} not a package")
                        continue
                else:  # by-name (`/#`): resolve via stem index
                    matches = stem_index.get(prefix, {}).get(value, [])
                    if len(matches) != 1:
                        warnings.append(f"{p['name']}: /# {value} resolved to {matches or 'nothing'}")
                        continue
                    dep = matches[0]
                if dep != p["name"] and dep not in seen:
                    seen.add(dep); deps.append(dep)
        else:  # ford
            fam = p["_family"]
            for rune, nm in parse_ford_imports(text):
                idx = (sur_index if rune == "-" else lib_index).get(fam, {})
                dep = idx.get(nm)
                if dep is None:
                    warnings.append(f"{p['name']}: ford import /{rune} {nm} unresolved in family {fam}")
                    continue
                if dep != p["name"] and dep not in seen:
                    seen.add(dep); deps.append(dep)
        p["dependencies"] = deps
    return warnings


def generate(overrides):
    packages = []
    # urbit (explicit)
    for name, path, file, deps in URBIT_PACKAGES:
        packages.append({"name": name, "workspace": "urbit", "path": path,
                         "file": file, "dependencies": deps, "_resolver": "explicit"})
    # nockapp pack (explicit)
    for name, path, file, deps in NOCKAPP_PACKAGES:
        packages.append({"name": name, "workspace": "nockapp-pack", "path": path,
                         "file": file, "dependencies": deps, "_resolver": "explicit"})
    # derived families
    derived = []
    for fam in FLAT_FAMILIES:
        derived += build_flat_packages(fam, get_checkout(fam["checkout"], overrides))
    for fam in FORD_FAMILIES:
        derived += build_ford_packages(fam, get_checkout(fam["checkout"], overrides))
    warnings = resolve_dependencies(derived, None)
    # order: nockchain sorted by name, then numerics, then sequent (config order)
    flat = sorted((p for p in derived if p["_resolver"] == "flat"), key=lambda p: p["name"])
    ford = [p for p in derived if p["_resolver"] == "ford"]   # keep spec order
    packages += flat + ford
    return packages, warnings

# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


def _s(v):
    return json.dumps(v)


def _arr(items):
    return "[" + ", ".join(_s(i) for i in items) + "]"


def emit(packages):
    L = []
    bar = "# " + "=" * 76
    L += [bar, "# Registry metadata", bar, "[registry]"]
    for k in ("name", "version", "description", "url"):
        L.append(f"{k} = {_s(REGISTRY_META[k])}")
    L += ["", "[config]", f"default_ref = {_s(DEFAULT_REF)}", ""]
    L += [bar, "# Workspaces", bar, ""]
    for wsname, ws in WORKSPACES.items():
        L.append(f"[workspace.{wsname}]")
        L.append(f"git_url = {_s(ws['git_url'])}")
        L.append(f"ref = {_s(ws['ref'])}")
        L.append(f"description = {_s(ws['description'])}")
        L.append(f"root_path = {_s(ws['root_path'])}")
        L.append("")
    L += [bar, "# Packages", bar, ""]
    group_comments = {
        "urbit": "# Urbit (urbit/urbit, pkg/arvo): /sys stdlib, vanes, /lib",
        "nockchain": "# Nockchain standard library (nockchain/nockchain, hoon/)",
        "numerics": "# urbit/numerics: math primitives, lagoon (linalg), saloon (decompositions)",
        "sequent": "# jackfoxy/sequent: list operations",
        "yard": "# urbit/yard: curated general-purpose libraries (Urbit Foundation)",
        "nockapp": "# NockApp Pack (sigilante/nockapp-pack): example apps",
        "nockasm": "# Nockasm (sigilante/nockasm, desk): Nock assembly expander + target IR",
    }
    last_ws_group = None
    for p in packages:
        group = p["workspace"].split("-")[0]
        if group != last_ws_group:
            L.append(group_comments.get(group, f"# {group}"))
            last_ws_group = group
        L.append("[[package]]")
        L.append(f"name = {_s(p['name'])}")
        L.append(f"workspace = {_s(p['workspace'])}")
        L.append(f"path = {_s(p['path'])}")
        L.append(f"file = {_s(p['file'])}")
        L.append(f"dependencies = {_arr(p['dependencies'])}")
        L.append("")
    L += [bar, "# Aliases", bar, ""]
    for name, target in ALIASES:
        L += ["[[alias]]", f"name = {_s(name)}", f"target = {_s(target)}", ""]
    return "\n".join(L).rstrip() + "\n"

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate(path, overrides):
    with open(path, "rb") as fh:
        d = tomllib.load(fh)
    ws = d.get("workspace", {})
    pkgs = d.get("package", [])
    names = {p["name"] for p in pkgs}
    aliases = {a["name"]: a["target"] for a in d.get("alias", [])}
    resolvable = names | set(aliases)
    errors = []

    for p in pkgs:
        for dep in p.get("dependencies", []):
            if dep not in resolvable:
                errors.append(f"unresolved dependency: {p['name']} -> {dep}")
    for n, t in aliases.items():
        if t not in names:
            errors.append(f"dangling alias: {n} -> {t}")

    # file existence where a checkout is available
    checkout_for_ws = {}
    for fam in FLAT_FAMILIES:
        checkout_for_ws[fam["workspace"]] = fam["checkout"]
    for fam in FORD_FAMILIES:
        for spec in fam["specs"]:
            checkout_for_ws[spec["workspace"]] = fam["checkout"]
    checked = skipped = 0
    for p in pkgs:
        key = checkout_for_ws.get(p["workspace"])
        base = overrides.get(key) or CHECKOUTS.get(key) if key else None
        if not base or not os.path.isdir(base):
            skipped += 1
            continue
        fp = os.path.join(base, ws[p["workspace"]]["root_path"], p["path"], p["file"])
        if not os.path.isfile(fp):
            errors.append(f"missing file: {p['name']} -> {fp}")
        else:
            checked += 1

    print(f"workspaces={len(ws)} packages={len(pkgs)} aliases={len(aliases)}")
    print(f"files checked={checked} skipped(no checkout)={skipped}")
    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        return 1
    print("OK: all dependencies and aliases resolve; all checked files exist.")
    return 0

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_overrides(items):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--checkout expects family=/path, got {it!r}")
        k, v = it.split("=", 1)
        out[k] = v
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="regenerate registry.toml")
    g.add_argument("--output", default=REGISTRY_PATH)
    g.add_argument("--check", action="store_true",
                   help="compare against existing registry semantically; non-zero on drift")
    g.add_argument("--checkout", action="append", metavar="family=/path")

    v = sub.add_parser("validate", help="validate a registry.toml")
    v.add_argument("path", nargs="?", default=REGISTRY_PATH)
    v.add_argument("--checkout", action="append", metavar="family=/path")

    args = ap.parse_args(argv)
    overrides = parse_overrides(getattr(args, "checkout", None))

    if args.cmd == "generate":
        packages, warnings = generate(overrides)
        for w in warnings:
            print("warning: " + w, file=sys.stderr)
        text = emit(packages)
        if args.check:
            return _check_drift(text)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.output}: {len(packages)} packages, {len(ALIASES)} aliases",
              file=sys.stderr)
        return 1 if warnings else 0

    if args.cmd == "validate":
        return validate(args.path, overrides)


def _semantic(d):
    """Comparable view of a parsed registry (order-independent)."""
    return {
        "workspaces": {k: v for k, v in d.get("workspace", {}).items()},
        "packages": {p["name"]: {"workspace": p["workspace"], "path": p["path"],
                                 "file": p["file"], "deps": sorted(p.get("dependencies", []))}
                     for p in d.get("package", [])},
        "aliases": {a["name"]: a["target"] for a in d.get("alias", [])},
    }


def _check_drift(generated_text):
    new = _semantic(tomllib.loads(generated_text))
    with open(REGISTRY_PATH, "rb") as fh:
        cur = _semantic(tomllib.load(fh))
    if new == cur:
        print("no drift: generated registry matches registry.toml")
        return 0
    # report differences
    for kind in ("workspaces", "packages", "aliases"):
        cur_keys, new_keys = set(cur[kind]), set(new[kind])
        for k in sorted(new_keys - cur_keys):
            print(f"+ {kind[:-1]} {k}")
        for k in sorted(cur_keys - new_keys):
            print(f"- {kind[:-1]} {k}")
        for k in sorted(cur_keys & new_keys):
            if cur[kind][k] != new[kind][k]:
                print(f"~ {kind[:-1]} {k}: {cur[kind][k]} -> {new[kind][k]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
