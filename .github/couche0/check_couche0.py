"""Couche 0 : scope declare + motifs interdits + fichiers de garde."""
import argparse
import os
import re
import subprocess
import sys

GUARD_FILES = (
    ".mergify.yml",
    ".github/ci-budget/",
    ".github/couche0/",
    ".github/workflows/couche0.yml",
    ".github/workflows/ci-budget.yml",
    ".github/workflows/ci.yml",
)
GUARD_FLAG = "HACK_ALLOW_GUARD_BUMP"
FORBIDDEN_PATTERNS = (
    (r"--force(?!-with-lease)", "push force interdit (utilise --force-with-lease)", None),
)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def is_guarded(path):
    for guard in GUARD_FILES:
        if guard.endswith("/") and path.startswith(guard):
            return True
        if path == guard:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args()
    if os.environ.get("HEAD_REF", "").startswith("mergify/"):
        print("branche mergify/* : succes sans controle.")
        return 0
    body = os.environ.get("PR_BODY", "")
    files = [f for f in run(["git", "diff", "--name-only", args.base + "...HEAD"]).splitlines() if f]
    if not files:
        print("aucun fichier modifie : rien a controler.")
        return 0
    if "## Scope" not in body:
        print("scope : aucune section `## Scope` dans le corps de la PR, "
              "alors que %d fichier(s) sont modifies" % len(files))
        return 1
    touched = [f for f in files if is_guarded(f)]
    if touched and GUARD_FLAG not in body:
        print("forbidden : fichier(s) de garde modifie(s) sans la mention `%s` : %s"
              % (GUARD_FLAG, ", ".join(touched)))
        return 1
    diff = run(["git", "diff", "-U0", args.base + "...HEAD"]).splitlines()
    errors = 0
    for line in diff:
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        if "modal" in content:
            continue
        for pattern, message, exempt in FORBIDDEN_PATTERNS:
            if exempt and exempt in content:
                continue
            if re.search(pattern, content):
                print("forbidden : %s : %s" % (message, content.strip()[:120]))
                errors += 1
    if errors:
        print("REFUSE - %d erreur(s)" % errors)
        return 1
    print("couche0 OK : %d fichier(s) controle(s), scope declare." % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
