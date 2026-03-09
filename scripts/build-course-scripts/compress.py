#!/usr/bin/env python3
"""
compress.py

Compress a course folder from courses-extracted/ into a .mbz file in courses-built/.

Run without arguments to select interactively from a numbered list.
If a .mbz with the same name already exists it will be overwritten.

Usage:
    python scripts/build-course-scripts/compress.py
    python scripts/build-course-scripts/compress.py <folder-name>
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT        = Path(__file__).resolve().parent.parent.parent
SOURCE_DIRS      = [
    REPO_ROOT / "courses-extracted",
]
TARGET_DIR       = REPO_ROOT / "courses-built"


def _all_course_folders() -> list[Path]:
    folders = []
    for source in SOURCE_DIRS:
        if source.is_dir():
            folders.extend(sorted(f for f in source.iterdir() if f.is_dir()))
    return folders


def select_course_folder() -> Path:
    """List available course folders and prompt user to pick one."""
    folders = _all_course_folders()
    if not folders:
        print("No course folders found in courses-extracted/")
        sys.exit(1)

    print("\nAvailable courses:")
    for i, f in enumerate(folders, 1):
        print(f"  {i}. {f.name}")

    print()
    while True:
        raw = input("Enter number to compress: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(folders):
            return folders[int(raw) - 1]
        print(f"  Please enter a number between 1 and {len(folders)}.")


def _read_mbz_name(folder: Path) -> str:
    """Return the <name> from moodle_backup.xml, falling back to folder.name + .mbz."""
    manifest = folder / "moodle_backup.xml"
    if manifest.is_file():
        try:
            root = ET.parse(manifest).getroot()
            name = root.findtext("information/name", "").strip()
            if name:
                return name if name.endswith(".mbz") else f"{name}.mbz"
        except ET.ParseError:
            pass
    return f"{folder.name}.mbz"


def compress_course(folder: Path) -> None:
    """Zip a course folder into TARGET_DIR/<name>.mbz using the name from moodle_backup.xml."""
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    mbz_name = _read_mbz_name(folder)
    mbz_path = TARGET_DIR / mbz_name

    print(f"\nCompressing: {folder.name}  →  {mbz_name}")

    if mbz_path.exists():
        print(f"  → Overwriting existing file: {mbz_path.name}")
        mbz_path.unlink()

    all_files = sorted(folder.rglob("*"))
    with zipfile.ZipFile(mbz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in all_files:
            if file.is_file():
                zf.write(file, file.relative_to(folder))

    size_kb = mbz_path.stat().st_size / 1024
    print(f"  → Created: {mbz_path.relative_to(REPO_ROOT)}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        name = sys.argv[1]
        matches = [f for f in _all_course_folders() if f.name == name]
        if not matches:
            print(f"Error: '{name}' not found in courses-extracted/")
            sys.exit(1)
        folder = matches[0]
    else:
        folder = select_course_folder()

    compress_course(folder)
