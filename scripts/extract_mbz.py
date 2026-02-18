#!/usr/bin/env python3
"""
Extract Moodle MBZ (backup) files from raw-mbz-files/ to courses-extracted/

This script extracts a specified .mbz file from the raw-mbz-files directory,
placing the extracted course in its own subdirectory within courses-extracted/.
If a course folder already exists, it will be overwritten.

Usage:
    python scripts/extract_mbz.py <filename.mbz>
    
Example:
    python scripts/extract_mbz.py backup-moodle2-course-571-real_numbers-20260218-1335-nu.mbz
"""

import sys
import zipfile
import tarfile
import gzip
import shutil
from pathlib import Path


def extract_mbz_file(filename, source_dir="raw-mbz-files", target_dir="cuorses-extracted"):
    """
    Extract a specific MBZ file from source directory to target directory.
    
    Args:
        filename: Name of the .mbz file to extract (e.g., 'course-backup.mbz')
        source_dir: Directory containing .mbz files (default: raw-mbz-files)
        target_dir: Directory where course will be extracted (default: cuorses-extracted)
    """
    # Get the repository root (parent of scripts folder)
    repo_root = Path(__file__).parent.parent
    source_path = repo_root / source_dir
    target_path = repo_root / target_dir
    
    # Check if source directory exists
    if not source_path.exists():
        print(f"Error: Source directory '{source_path}' does not exist.")
        return False
    
    # Build the full path to the MBZ file
    mbz_file = source_path / filename
    
    # Check if the file exists
    if not mbz_file.exists():
        print(f"Error: File '{filename}' not found in '{source_path}'")
        print(f"\nAvailable .mbz files:")
        available_files = list(source_path.glob("*.mbz"))
        if available_files:
            for f in available_files:
                print(f"  - {f.name}")
        else:
            print("  (none)")
        return False
    
    # Create target directory if it doesn't exist
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Create a folder name from the MBZ filename (without extension)
    course_name = mbz_file.stem
    course_folder = target_path / course_name
    
    print(f"Extracting: {mbz_file.name}")
    
    # Remove existing folder if it exists
    if course_folder.exists():
        print(f"  → Removing existing folder: {course_folder.name}")
        shutil.rmtree(course_folder)
    
    # Create the course folder
    course_folder.mkdir(parents=True, exist_ok=True)
    
    # Detect file type and extract accordingly
    try:
        # Check if it's a ZIP file
        if zipfile.is_zipfile(mbz_file):
            with zipfile.ZipFile(mbz_file, 'r') as zip_ref:
                zip_ref.extractall(course_folder)
            print(f"  → Extracted (ZIP) to: {course_folder.relative_to(repo_root)}\n")
        # Check if it's a TAR.GZ file
        elif tarfile.is_tarfile(mbz_file):
            with tarfile.open(mbz_file, 'r:*') as tar_ref:
                tar_ref.extractall(course_folder)
            print(f"  → Extracted (TAR) to: {course_folder.relative_to(repo_root)}\n")
        else:
            # Try GZIP extraction (might be a single compressed file)
            try:
                with gzip.open(mbz_file, 'rb') as gz_file:
                    # For single GZIP files, save the decompressed content
                    output_file = course_folder / f"{course_name}_decompressed"
                    with open(output_file, 'wb') as out_file:
                        shutil.copyfileobj(gz_file, out_file)
                print(f"  → Extracted (GZIP) to: {course_folder.relative_to(repo_root)}\n")
            except Exception:
                print(f"  → Error: Could not determine archive format for '{mbz_file.name}'\n")
                return False
    except Exception as e:
        print(f"  → Error extracting '{mbz_file.name}': {e}\n")
        return False
    
    print("Extraction complete!")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please specify an MBZ file to extract.")
        print("\nUsage:")
        print("  python scripts/extract_mbz.py <filename.mbz>")
        print("\nExample:")
        print("  python scripts/extract_mbz.py backup-moodle2-course-571-real_numbers-20260218-1335-nu.mbz")
        
        # List available files
        repo_root = Path(__file__).parent.parent
        source_path = repo_root / "raw-mbz-files"
        if source_path.exists():
            available_files = list(source_path.glob("*.mbz"))
            if available_files:
                print("\nAvailable .mbz files:")
                for f in available_files:
                    print(f"  - {f.name}")
        sys.exit(1)
    
    filename = sys.argv[1]
    success = extract_mbz_file(filename)
    sys.exit(0 if success else 1)
