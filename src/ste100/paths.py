"""Install-relative and target-relative path resolution, plus JSON/data loading.

Two different roots are at play, and conflating them was a real bug when this
tool became a standalone package:

  PACKAGE_DIR  where the linter's own rule data and presets are installed.
               Fixed at install time; never depends on the caller's cwd.
  root()       the tree being linted. Findings are reported relative to it,
               and profile path_globs are matched against it, so it must be
               the user's project -- not wherever the linter happens to live.
"""
import json
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
LINT_DATA_DIR = PACKAGE_DIR / "data"
PRESETS_DIR = PACKAGE_DIR / "presets"

SCHEMA_VERSION = 1

# Config lookup order, highest priority first. A project-local file lets a
# user drop config next to their docs and just run `ste100` with no flags.
PROJECT_CONFIG_NAMES = ["ste100.json", ".ste100.json"]

LINT_DATA_NAMES = ["substitutions", "hedges", "vague", "filler", "ai_tells",
                   "pos_heuristics", "budgets"]

_root = Path.cwd()


def root():
    """The tree being linted."""
    return _root


def set_root(path):
    global _root
    _root = Path(path).resolve()
    return _root


def available_presets():
    if not PRESETS_DIR.is_dir():
        return []
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def default_preset():
    """Prefer the generic preset; fall back to whatever single preset ships."""
    for name in ("default", "veistra"):
        if (PRESETS_DIR / f"{name}.json").is_file():
            return name
    presets = available_presets()
    return presets[0] if presets else None


def resolve_config(cli_config=None, cli_preset=None, start=None):
    """Resolve which config file to load.

    Order: --config path > --preset name > project-local ste100.json found by
    walking up from the target tree > the shipped default preset.
    """
    if cli_config:
        path = Path(cli_config)
        if not path.is_file():
            raise FileNotFoundError(f"config file not found: {path}")
        return path

    if cli_preset:
        path = PRESETS_DIR / f"{cli_preset}.json"
        if not path.is_file():
            raise FileNotFoundError(
                "unknown preset {!r}; available: {}".format(
                    cli_preset, ", ".join(available_presets()) or "(none)"))
        return path

    here = Path(start or root()).resolve()
    for directory in [here, *here.parents]:
        for name in PROJECT_CONFIG_NAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate

    name = default_preset()
    if name is None:
        raise FileNotFoundError(f"no presets installed under {PRESETS_DIR}")
    return PRESETS_DIR / f"{name}.json"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_lint_data():
    return {n: load_json(LINT_DATA_DIR / f"{n}.json") for n in LINT_DATA_NAMES}


def relative_to_root(abs_path):
    """Report path, relative to the linted tree, POSIX-style.

    Falls back to a relative path with '..' segments when the target sits
    outside the root (linting a file by absolute path from elsewhere), and to
    the absolute path when even that is impossible -- on Windows that happens
    whenever the two are on different drives.
    """
    abs_path = Path(abs_path)
    try:
        return abs_path.relative_to(root()).as_posix()
    except ValueError:
        pass
    try:
        return Path(os.path.relpath(abs_path, root())).as_posix()
    except ValueError:
        return abs_path.as_posix()


# Kept for backwards compatibility with the pre-package layout. Prefer
# resolve_config(); this constant cannot see --preset or a project-local file.
DEFAULT_CONFIG = PRESETS_DIR / f"{default_preset() or 'default'}.json"
