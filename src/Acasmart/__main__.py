from pathlib import Path
import runpy


def _run_top_level_main():
    # Locate the repository's src directory and execute main.py as a script
    package_dir = Path(__file__).resolve().parent          # .../src/acasmart
    src_dir = package_dir.parent                           # .../src
    main_py = src_dir / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(f"main.py not found at: {main_py}")
    runpy.run_path(str(main_py), run_name="__main__")


if __name__ == "__main__":
    _run_top_level_main()


