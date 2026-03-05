#!/usr/bin/env python3
"""
Compress an extracted Moodle course folder back into an MBZ (backup) file.

MBZ files are ZIP archives whose contents sit at the archive root (no
wrapping subdirectory).  This script replicates that structure so the
resulting file can be restored directly through Moodle's standard
Restore interface.

The output file is written to the `compressed-mbz-files/` directory at
the repository root.  That directory is kept separate from `raw-mbz-files/`
(which holds the original, unedited backups) so the two are never confused.

Usage:
    python scripts/compress_mbz.py <course-folder-name>

Example:
    python scripts/compress_mbz.py backup-moodle2-course-571-real_numbers-20260218-1335-nu

The course folder must already exist inside `courses-extracted/`.
The output file will be:
    compressed-mbz-files/backup-moodle2-course-571-real_numbers-20260218-1335-nu.mbz
"""

import sys
import zipfile
from pathlib import Path


def compress_mbz(course_folder_name, source_dir="courses-extracted", output_dir="compressed-mbz-files"):
    """
    Compress a course folder into an MBZ file.

    Args:
        course_folder_name: Name of the course folder inside source_dir
                            (e.g. 'backup-moodle2-course-571-real_numbers-20260218-1335-nu')
        source_dir:         Directory that contains extracted course folders
                            (default: courses-extracted)
        output_dir:         Directory where the .mbz file will be written
                            (default: compressed-mbz-files)
    """
    repo_root = Path(__file__).parent.parent
    course_path = repo_root / source_dir / course_folder_name
    output_path = repo_root / output_dir

    # Validate the course folder exists
    if not course_path.exists():
        print(f"Error: Course folder '{course_path}' does not exist.")
        print("\nAvailable course folders:")
        source_path = repo_root / source_dir
        if source_path.exists():
            folders = [f.name for f in source_path.iterdir() if f.is_dir()]
            if folders:
                for folder in sorted(folders):
                    print(f"  - {folder}")
            else:
                print("  (none)")
        return False

    # Collect all files to include
    all_files = [f for f in course_path.rglob("*") if f.is_file()]

    if not all_files:
        print(f"Error: Course folder '{course_path}' is empty.")
        return False

    # Create the output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Build the output filename
    mbz_filename = f"{course_folder_name}.mbz"
    mbz_file = output_path / mbz_filename

    print(f"Compressing: {course_folder_name}")
    print(f"  → Source:  {course_path.relative_to(repo_root)}")
    print(f"  → Output:  {mbz_file.relative_to(repo_root)}")
    print(f"  → Files:   {len(all_files)}")

    try:
        with zipfile.ZipFile(mbz_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(all_files):
                # Store with a path relative to the course folder so that
                # files sit at the archive root, matching Moodle's expectation.
                archive_name = file_path.relative_to(course_path)
                zf.write(file_path, archive_name)

        size_kb = mbz_file.stat().st_size / 1024
        print(f"  → Done ({size_kb:.1f} KB)\n")

    except Exception as e:
        print(f"  → Error during compression: {e}\n")
        return False

    print("Compression complete!")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please specify a course folder to compress.")
        print("\nUsage:")
        print("  python scripts/compress_mbz.py <course-folder-name>")
        print("\nExample:")
        print("  python scripts/compress_mbz.py backup-moodle2-course-571-real_numbers-20260218-1335-nu")

        # List available course folders
        repo_root = Path(__file__).parent.parent
        source_path = repo_root / "courses-extracted"
        if source_path.exists():
            folders = [f.name for f in source_path.iterdir() if f.is_dir()]
            if folders:
                print("\nAvailable course folders:")
                for folder in sorted(folders):
                    print(f"  - {folder}")
        sys.exit(1)

    course_folder_name = sys.argv[1]
    success = compress_mbz(course_folder_name)
    sys.exit(0 if success else 1)
