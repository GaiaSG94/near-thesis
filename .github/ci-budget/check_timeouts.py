"""Garde budget CI : chaque job a timeout-minutes <= 5 (stdlib uniquement)."""
import glob
import re
import sys

errors = []
warnings = []


def check_file(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    in_jobs = False
    current = None
    jobs = set()
    timeouts = {}
    for line in lines:
        if re.match(r"^jobs:\s*(#.*)?$", line):
            in_jobs = True
            continue
        if in_jobs and line.strip() and not line.startswith((" ", "#")):
            in_jobs = False
            current = None
        if not in_jobs:
            continue
        m = re.match(r"^  ([A-Za-z0-9_.-]+):\s*(#.*)?$", line)
        if m:
            current = m.group(1)
            jobs.add(current)
            continue
        m = re.search(r"timeout-minutes:\s*(\d+)", line)
        if m and current:
            timeouts[current] = int(m.group(1))
    if not jobs:
        errors.append("%s : aucun job detecte" % path)
    for job in sorted(jobs):
        if job not in timeouts:
            errors.append("%s : job %s sans timeout-minutes" % (path, job))
        elif timeouts[job] > 5:
            errors.append("%s : job %s timeout %d > 5" % (path, job, timeouts[job]))
    text = "\n".join(lines)
    if "concurrency:" not in text:
        warnings.append("%s : concurrency manquant" % path)
    if "fetch-depth:" not in text:
        warnings.append("%s : fetch-depth manquant" % path)


def main():
    files = sorted(glob.glob(".github/workflows/*.yml") + glob.glob(".github/workflows/*.yaml"))
    for path in files:
        check_file(path)
    for w in warnings:
        print("WARN %s" % w)
    for e in errors:
        print("ERROR %s" % e)
    print("ci-budget : %d fichier(s), %d erreur(s), %d alerte(s)" % (len(files), len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
