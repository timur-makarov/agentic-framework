"""doc-lint (plan, section 13): ARCHITECTURE.md's ## Areas keeps matching the tree.

It skips a project until ARCHITECTURE.md exists. Hidden directories, such as .rail and .claude, hold
configuration rather than areas, so they need no row.
"""

from . import gitx
from .areas import parse_areas
from .util import globmatch

CAP = 150


def areas(project, ref):
    """What is wrong with the ## Areas table at `ref`: [problem]. Empty when it is fine or absent."""
    text = gitx.read_blobs([f"{ref}:ARCHITECTURE.md"], project.root).get(f"{ref}:ARCHITECTURE.md")
    if text is None:
        return []
    problems = []
    if len(text.splitlines()) > CAP:
        problems.append(f"ARCHITECTURE.md has {len(text.splitlines())} lines; keep it to {CAP} or fewer")
    rows = parse_areas(text)
    if not rows:
        return problems + ["ARCHITECTURE.md has no ## Areas table"]
    files = [f for f in gitx.git(["ls-tree", "-r", "-z", "--name-only", ref], project.root).stdout.split("\0") if f]
    globs = [g for row in rows for g in row["paths"]]
    for row in rows:
        for glob in row["paths"]:
            if not any(globmatch(glob, f) for f in files):
                problems.append(f"## Areas row '{row['area']}': {glob} matches no tracked file")
    depth = project.config["map"]["depth"]
    ignore = [i.rstrip("/") for i in project.config["map"]["ignore"]]  # "docs/" and "docs" mean the same
    dirs = {}
    for f in files:
        parts = f.split("/")
        if len(parts) > depth and not any(p.startswith(".") for p in parts[:depth]):
            dirs.setdefault("/".join(parts[:depth]), []).append(f)
    for d in sorted(dirs):
        if d in ignore or any(d.startswith(i + "/") for i in ignore):
            continue
        if not any(globmatch(g, f) for g in globs for f in dirs[d]):
            problems.append(f"{d}/ is in no ## Areas row; add a row, or list it in [map] ignore")
    return problems
