#!/usr/bin/env python3
"""
populate_courses_json.py

Interactive script to populate data/courses.json from data/automatic-links.csv.
Run from the repo root:
    python scripts/populate_courses_json.py
"""

import csv
import json
import os
import hashlib
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT        = Path(__file__).parent.parent
CSV_PATH         = REPO_ROOT / "data" / "automatic-links.csv"
JSON_PATH        = REPO_ROOT / "data" / "courses.json"
COURSE_LOGOS_DIR = REPO_ROOT / "assets" / "course-logos"

LESSON_PLAN_BASE_URL = "https://innodems.github.io/CBC-Grade-10-Maths/external/lesson_plans/"

FACILITATORS = [
    {"name": "Dr. Michael Obiero",  "email": "obiero@maseno.ac.ke",  "phone": "+254737456117"},
    {"name": "Zachariah Mbasu",     "email": "zmbasu@innodems.org",  "phone": "+254722124199"},
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def lo_id(description: str) -> str:
    """Stable 10-char ID derived from the LO description text."""
    return "lo-" + hashlib.sha1(description.strip().encode()).hexdigest()[:10]


def ask(prompt: str, default: str | None = None) -> str:
    """Prompt the user, showing a default value they can accept with Enter."""
    if default:
        answer = input(f"{prompt} [{default}]: ").strip()
        return answer if answer else default
    while True:
        answer = input(f"{prompt}: ").strip()
        if answer:
            return answer


def ask_int(prompt: str, default: int | None = None) -> int:
    if default is not None:
        while True:
            raw = input(f"{prompt} [{default}]: ").strip()
            if not raw:
                return default
            try:
                return int(raw)
            except ValueError:
                print("  Please enter a whole number.")
    else:
        while True:
            try:
                return int(input(f"{prompt}: ").strip())
            except ValueError:
                print("  Please enter a whole number.")


def choose(prompt: str, options: list[str]) -> int:
    """Show a numbered list and return the 0-based index of the chosen item."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        try:
            choice = int(input("Enter number: ").strip())
            if 1 <= choice <= len(options):
                return choice - 1
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(options)}.")


def extract_course_id_from_url(url: str) -> int | None:
    """Extract the numeric id from a Moodle course URL like ...?id=571"""
    try:
        return int(url.split("id=")[1].split("&")[0])
    except (IndexError, ValueError):
        return None


def find_course_logo(section_filecase: str) -> str | None:
    """Find a logo file matching the section filecase in assets/course-logos/."""
    for ext in ("jpg", "jpeg", "png", "webp", "gif", "svg"):
        candidate = COURSE_LOGOS_DIR / f"{section_filecase}.{ext}"
        if candidate.exists():
            return candidate.name
    return None


# ── Load CSV ──────────────────────────────────────────────────────────────────

def load_csv() -> list[dict]:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_by_chapter_section(rows: list[dict]) -> dict:
    """
    Returns:
        {
            chapter: {
                section: [rows...]
            }
        }
    preserving CSV order.
    """
    result = {}
    for row in rows:
        ch = row["Chapter"]
        se = row["Section"]
        result.setdefault(ch, {}).setdefault(se, []).append(row)
    return result


# ── Load / save JSON ──────────────────────────────────────────────────────────

def load_json() -> dict:
    if JSON_PATH.exists():
        with open(JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "lesson_plan_base_url": LESSON_PLAN_BASE_URL,
        "facilitators": FACILITATORS,
        "courses": [],
    }


def save_json(data: dict):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved → {JSON_PATH}")


# ── Build a course entry ──────────────────────────────────────────────────────

def build_course(rows: list[dict], existing_json: dict) -> dict:
    """Interactively build a course JSON entry from a list of CSV rows."""

    # -- Representative row for course-level data
    rep = rows[0]
    chapter          = rep["Chapter"]
    chapter_filecase = rep["Chapter Filecase"]
    section          = rep["Section"]
    section_filecase = rep["Section Filecase"]

    # -- Check if course already exists in JSON
    existing_course = next(
        (c for c in existing_json["courses"]
         if c.get("section_filecase") == section_filecase),
        None
    )
    if existing_course:
        overwrite = ask(
            f"\n  Course '{section}' already exists in courses.json. Overwrite? (y/n)",
            default="n"
        ).lower()
        if overwrite != "y":
            print("  Skipping.")
            return None

    print(f"\n{'='*60}")
    print(f"  Populating course: {chapter} → {section}")
    print(f"{'='*60}")

    # -- Course-level fields
    # Moodle course ID is extracted from CSV automatically (informational only — resets on restore)
    moodle_course_id = extract_course_id_from_url(rep.get("Course URL", ""))

    chapter_number = ask_int("  Chapter number (e.g. 1 for 'Numbers and Algebra')")
    section_number = ask_int("  Section number within the chapter (e.g. 1 for 'Real Numbers')")

    suggested_slug = f"sec-{section_filecase}"
    student_section_url_slug = ask(
        "  Student textbook section URL slug",
        default=suggested_slug
    )

    detected_logo = find_course_logo(section_filecase)
    course_logo_file = ask(
        "  Course logo filename (in assets/course-logos/)",
        default=detected_logo or f"{section_filecase}.jpg"
    )

    moodle_course_folder = ask(
        "  Moodle course folder name (in courses-extracted/)",
        default=f"backup-moodle2-course-{moodle_course_id}-{section_filecase}-YYYYMMDD-HHMM-nu"
    )

    # -- Build learning outcomes (deduplicated, from all LO columns)
    lo_texts_seen = {}  # description → id (preserves order, deduplicates)
    for row in rows:
        for col in ("LO 1", "LO 2", "LO 3", "LO 4"):
            text = row.get(col, "").strip()
            if text and text not in lo_texts_seen:
                lo_texts_seen[text] = lo_id(text)

    learning_outcomes = [
        {"id": lid, "description": desc}
        for desc, lid in lo_texts_seen.items()
    ]

    print(f"\n  Found {len(learning_outcomes)} unique learning outcome(s):")
    for lo in learning_outcomes:
        print(f"    [{lo['id']}] {lo['description']}")

    # -- Build lessons
    lessons = []
    n = len(rows)
    print(f"\n  Now entering IDs for each of the {n} lesson(s).")
    print("  (These come from the Moodle course XML files.)\n")

    for i, row in enumerate(rows, 1):
        # Determine label (deepest level)
        subsubsection          = row.get("Subsubsection", "").strip() or None
        subsubsection_filecase = row.get("Subsubsection Filecase", "").strip() or None
        subsection             = row.get("Subsection", "").strip() or None
        subsection_filecase    = row.get("Subsection Filecase", "").strip() or None
        label = subsubsection or subsection

        print(f"  Lesson {i}/{n}: {label}")

        moodle_section_id = ask_int("    moodle_section_id")
        forum_id          = ask_int("    forum_id")

        # LO IDs for this lesson
        lesson_lo_ids = []
        for col in ("LO 1", "LO 2", "LO 3", "LO 4"):
            text = row.get(col, "").strip()
            if text and text in lo_texts_seen:
                lid = lo_texts_seen[text]
                if lid not in lesson_lo_ids:
                    lesson_lo_ids.append(lid)

        lessons.append({
            "subsection":             subsection,
            "subsection_filecase":    subsection_filecase,
            "subsubsection":          subsubsection,
            "subsubsection_filecase": subsubsection_filecase,
            "moodle_section_id":      moodle_section_id,
            "forum_id":               forum_id,
            "lesson_plan_path":       row["Lesson Plan Path"],
            "step_by_step_path":      row["Step By Step Guide Path"],
            "lesson_plan_exists":     row.get("Lesson Plan Exists", "").upper() == "YES",
            "step_by_step_exists":    row.get("Step By Step Guide Exists", "").upper() == "YES",
            "learning_outcome_ids":   lesson_lo_ids,
        })

        print()

    return {
        "moodle_course_id":         moodle_course_id,
        "moodle_course_folder":     moodle_course_folder,
        "chapter":                  chapter,
        "chapter_filecase":         chapter_filecase,
        "chapter_number":           chapter_number,
        "section":                  section,
        "section_filecase":         section_filecase,
        "section_number":           section_number,
        "student_section_url_slug": student_section_url_slug,
        "course_logo_file":         course_logo_file,
        "learning_outcomes":        learning_outcomes,
        "lessons":                  lessons,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    rows = load_csv()
    grouped = group_by_chapter_section(rows)
    existing_json = load_json()

    chapters = list(grouped.keys())
    ch_idx = choose("Which chapter do you want to populate?", chapters)
    chapter = chapters[ch_idx]

    sections = list(grouped[chapter].keys())
    se_idx = choose(f"Which section of '{chapter}'?", sections)
    section = sections[se_idx]

    course_rows = grouped[chapter][section]
    course_entry = build_course(course_rows, existing_json)

    if course_entry is None:
        return

    # Remove existing entry for this section if present
    existing_json["courses"] = [
        c for c in existing_json["courses"]
        if c.get("section_filecase") != course_entry["section_filecase"]
    ]
    existing_json["courses"].append(course_entry)

    # Ensure top-level fields are present
    existing_json.setdefault("lesson_plan_base_url", LESSON_PLAN_BASE_URL)
    existing_json.setdefault("facilitators", FACILITATORS)

    save_json(existing_json)
    print("\nDone! Review data/courses.json and commit when ready.")


if __name__ == "__main__":
    main()
