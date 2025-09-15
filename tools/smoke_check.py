import sys
from pathlib import Path

# Ensure project src is on sys.path
repo_root = Path(__file__).resolve().parents[1]
src_dir = repo_root / 'src'
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import db_helper  # noqa: E402

if __name__ == '__main__':
    print('Running smoke check: create_tables()...')
    db_helper.create_tables()
    print('Smoke check completed.')
