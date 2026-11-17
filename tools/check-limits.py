"""Garde < 500 lignes/fichier, < 50 lignes/fonction (heuristique multi-langages)."""
import os
import re
import sys

MAX_FILE_LINES = 500
MAX_FUNC_LINES = 50
BRACE_EXTS = {".kt", ".kts", ".java", ".js", ".ts", ".tsx", ".jsx",
              ".ps1", ".sh", ".rs", ".go", ".c", ".cpp"}
INDENT_EXTS = {".py"}
COUNT_ONLY_EXTS = {".yml", ".yaml", ".json", ".toml"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "renders",
             "audio-generated", "__pycache__"}
# Lockfiles generates : jamais ecrits a la main, exclus des limites de taille.
SKIP_FILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock", "poetry.lock"}
FUNC_RE = re.compile(r"^\s*(def |function |fn |func |sub |Function )")


def strip_text(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"'(?:\\.|[^'\\])*'", "''", text)
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    clean = []
    for line in text.splitlines():
        line = re.sub(r"//.*$", "", line)
        line = re.sub(r"#.*$", "", line)
        clean.append(line)
    return clean


def scan_brace(lines):
    found = []
    depth = 0
    for i, line in enumerate(lines):
        m = FUNC_RE.match(line)
        if m:
            found.append({"start": i + 1, "depth": depth, "end": None})
        depth += line.count("{") - line.count("}")
        for func in found:
            if func["end"] is None and depth < func["depth"]:
                func["end"] = i + 1
    for func in found:
        if func["end"] is None:
            func["end"] = len(lines)
    return [(f["start"], f["end"] - f["start"]) for f in found]


def scan_indent(lines):
    found = []
    current = None
    for i, line in enumerate(lines):
        if FUNC_RE.match(line):
            if current:
                current["end"] = i + 1
                found.append(current)
            indent = len(line) - len(line.lstrip(" "))
            current = {"start": i + 1, "indent": indent, "end": None}
        elif current and line.strip():
            indent = len(line) - len(line.lstrip(" "))
            if indent <= current["indent"]:
                current["end"] = i + 1
                found.append(current)
                current = None
    if current:
        current["end"] = len(lines)
        found.append(current)
    return [(f["start"], f["end"] - f["start"]) for f in found]


def check_file(path):
    ext = os.path.splitext(path)[1]
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (UnicodeDecodeError, OSError):
        return []
    lines = [line for line in strip_text(text) if line.strip()]
    problems = []
    if len(lines) > MAX_FILE_LINES:
        problems.append("%s : %d lignes > %d" % (path, len(lines), MAX_FILE_LINES))
    if ext in BRACE_EXTS:
        funcs = scan_brace(lines)
    elif ext in INDENT_EXTS:
        funcs = scan_indent(lines)
    else:
        funcs = []
    for start, length in funcs:
        if length > MAX_FUNC_LINES:
            problems.append("%s : fonction ligne %d = %d lignes > %d"
                            % (path, start, length, MAX_FUNC_LINES))
    return problems


def main():
    problems = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name in SKIP_FILES:
                continue
            ext = os.path.splitext(name)[1]
            if ext in BRACE_EXTS or ext in INDENT_EXTS or ext in COUNT_ONLY_EXTS:
                problems += check_file(os.path.join(root, name))
    for problem in problems:
        print("ERROR %s" % problem)
    print("check-limits : %d probleme(s)" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
