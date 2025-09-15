import os
import re
import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Python 3.8 compatible

FROM_DB_HELPER_PATTERN = re.compile(
    r"^\s*from\s+db_helper\s+import\s+(?P<imports>.+)$",
    re.MULTILINE,
)

# Captures names in import lists like: a, b as c, (a, b, c), \
# Also handles multiline parenthesized imports joined by newlines
NAME_EXTRACT_PATTERN = re.compile(r"[\(\)\\]\s*|")

SECTION_KEYWORDS: List[Tuple[str, str]] = [
    ("schema", "schema"),
    ("migrat", "migrations"),
    ("setting", "settings"),
    ("profile", "profiles"),
    ("student", "students"),
    ("teacher", "teachers"),
    ("class", "classes"),
    ("term", "terms"),
    ("session", "sessions"),
    ("attend", "attendance"),
    ("pay", "payments"),
    ("finance", "finance"),
    ("notif", "notifications"),
    ("sms", "notifications"),
    ("report", "reports"),
]


def guess_section(function_name: str) -> str:
    lower_name = function_name.lower()
    for needle, section in SECTION_KEYWORDS:
        if needle in lower_name:
            return section
    return "misc"


def normalize_import_list(import_block: str) -> List[str]:
    # Remove parentheses and line continuations
    cleaned = import_block.replace("\\n", " ")
    cleaned = cleaned.replace("\\", " ")
    cleaned = cleaned.replace("(", " ").replace(")", " ")
    # Split by comma
    parts = [p.strip() for p in cleaned.split(',')]
    names: List[str] = []
    for part in parts:
        if not part:
            continue
        # Remove aliasing "as alias"
        if ' as ' in part:
            part = part.split(' as ', 1)[0].strip()
        # Filter out empty leftovers
        if part:
            names.append(part)
    return [n for n in names if n and n != '*']


def find_db_helper_imports(py_content: str) -> List[List[str]]:
    results: List[List[str]] = []
    # Handle multi-line parenthesized imports: we need to stitch lines following a match until no trailing comma? Simplify by capturing consecutive lines that belong to the same import.
    lines = py_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^\s*from\s+db_helper\s+import\s+(.*)$", line)
        if match:
            block = match.group(1)
            # If parentheses not balanced or line ends with comma, keep consuming
            open_paren = block.count('(') - block.count(')')
            while (open_paren > 0 or block.strip().endswith(',')) and i + 1 < len(lines):
                i += 1
                nxt = lines[i]
                block += "\n" + nxt
                open_paren += nxt.count('(') - nxt.count(')')
            imports = normalize_import_list(block)
            if imports:
                results.append(imports)
        i += 1
    return results


def main() -> None:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]

    # Collect all Python files under repo, excluding typical dirs
    exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'env', 'artifacts', 'build', 'dist'}
    py_files: List[Path] = []
    for root, dirs, files in os.walk(repo_root):
        # prune excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        for f in files:
            if f.endswith('.py'):
                py_files.append(Path(root) / f)

    # Maps
    function_to_files: Dict[str, Set[str]] = {}
    file_to_functions: Dict[str, List[str]] = {}

    for py_file in py_files:
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        imports_lists = find_db_helper_imports(content)
        imported_functions: List[str] = []
        for imports in imports_lists:
            for func in imports:
                imported_functions.append(func)
                function_to_files.setdefault(func, set()).add(str(py_file.relative_to(repo_root).as_posix()))
        if imported_functions:
            # Deduplicate but preserve order
            seen: Set[str] = set()
            ordered = []
            for name in imported_functions:
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
            file_to_functions[str(py_file.relative_to(repo_root).as_posix())] = ordered

    artifacts_dir = repo_root / 'artifacts'
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write db_helper_usage_by_function.csv
    usage_csv = artifacts_dir / 'db_helper_usage_by_function.csv'
    with usage_csv.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['function', 'section_guess', 'used_in_files'])
        for func in sorted(function_to_files.keys(), key=lambda s: s.lower()):
            files = sorted(function_to_files[func])
            writer.writerow([func, guess_section(func), ';'.join(files)])

    # Write db_helper_imports_by_file.csv
    imports_csv = artifacts_dir / 'db_helper_imports_by_file.csv'
    with imports_csv.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['file', 'imports_from_db_helper'])
        for file_path in sorted(file_to_functions.keys(), key=lambda s: s.lower()):
            writer.writerow([file_path, ';'.join(file_to_functions[file_path])])

    print(f"Wrote: {usage_csv}")
    print(f"Wrote: {imports_csv}")


if __name__ == '__main__':
    main()
