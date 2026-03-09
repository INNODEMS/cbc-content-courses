#!/usr/bin/env python3
"""
Extract a Moodle MBZ backup file from compressed-mbz-files/ to courses-extracted/

Run without arguments to select interactively from a numbered list.
If the destination folder already exists it will be overwritten.

Usage:
    python scripts/extract_mbz.py
    python scripts/extract_mbz.py <filename.mbz>
"""

import sys
import zipfile
import tarfile
import gzip
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SOURCE_DIR = REPO_ROOT / "compressed-mbz-files"
TARGET_DIR = REPO_ROOT / "courses-extracted"


def select_mbz_file() -> Path:
    """List available .mbz files and prompt user to pick one."""
    files = sorted(SOURCE_DIR.glob("*.mbz"))
    if not files:
        print(f"No .mbz files found in {SOURCE_DIR.relative_to(REPO_ROOT)}/")
        sys.exit(1)

    print("\nAvailable courses:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")

    print()
    while True:
        raw = input("Enter number to extract: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(files):
            return files[int(raw) - 1]
        print(f"  Please enter a number between 1 and {len(files)}.")


def extract_mbz_file(mbz_file: Path) -> bool:
    """Extract a single .mbz file into TARGET_DIR/<stem>/."""
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    course_folder = TARGET_DIR / mbz_file.stem

    print(f"\nExtracting: {mbz_file.name}")

    if course_folder.exists():
        print(f"  → Overwriting existing folder: {course_folder.name}")
        shutil.rmtree(course_folder)

    course_folder.mkdir(parents=True, exist_ok=True)

    try:
        if zipfile.is_zipfile(mbz_file):
            with zipfile.ZipFile(mbz_file, 'r') as zf:
                zf.extractall(course_folder)
            print(f"  → Extracted (ZIP) to: {course_folder.relative_to(REPO_ROOT)}")
        elif tarfile.is_tarfile(mbz_file):
            with tarfile.open(mbz_file, 'r:*') as tf:
                tf.extractall(course_folder, filter='data')
            print(f"  → Extracted (TAR) to: {course_folder.relative_to(REPO_ROOT)}")
        else:
            try:
                with gzip.open(mbz_file, 'rb') as gz:
                    out = course_folder / f"{mbz_file.stem}_decompressed"
                    with open(out, 'wb') as f:
                        shutil.copyfileobj(gz, f)
                print(f"  → Extracted (GZIP) to: {course_folder.relative_to(REPO_ROOT)}")
            except Exception:
                print(f"  → Error: could not determine archive format for '{mbz_file.name}'")
                return False
    except Exception as e:
        print(f"  → Error: {e}")
        return False

    print("\nExtraction complete!")
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        mbz_file = SOURCE_DIR / sys.argv[1]
        if not mbz_file.exists():
            print(f"Error: '{sys.argv[1]}' not found in {SOURCE_DIR.relative_to(REPO_ROOT)}/")
            sys.exit(1)
    else:
        mbz_file = select_mbz_file()

    success = extract_mbz_file(mbz_file)
    sys.exit(0 if success else 1)
