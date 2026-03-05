#!/usr/bin/env python3
"""
populate_courses_json.py
========================
Non-interactive sync tool: reads the entire data/automatic-links.csv and
rebuilds data/courses.json with ALL courses.

Run from the repo root:
    python scripts/populate_courses_json.py

What it does:
  - Adds every (Chapter, Section) pair from the CSV as a course entry.
  - Pulls ALL lesson data from the CSV (paths, LOs, exists flags).
  - Auto-detects course_logo_file from assets/course-logos/ if a match exists.
  - PRESERVES any existing non-CSV data already in courses.json:
      chapter_number, section_number, course_logo_file (if set to null deliberately),
      moodle_course_folder (if it names a real extracted folder),
      moodle_section_id / forum_id per lesson (real Moodle IDs for deployed courses).

What it does NOT do:
  - Ask any questions.
  - Set chapter_number or section_number (those are not in the CSV).
  - Modify generate_course.py's job.

Anything null after running this script (chapter_number, section_number,
course_logo_file) will be requested interactively when running generate_course.py.
"""

import csv
import hashlib
import json
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

# ── Helpers ──────────────────────────────────────────────────────────────────

def lo_id(description: str) -> str:
    """Stable 10-char hash ID derived from the LO description text."""
    return "lo-" + hashlib.sha1(description.strip().encode()).hexdigest()[:10]


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


# ── CSV / JSON I/O ────────────────────────────────────────────────────────────

def load_csv() -> list[dict]:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_by_chapter_section(rows: list[dict]) -> dict:
    """Return {chapter: {section: [rows...]}} preserving CSV order."""
    result: dict = {}
    for row in rows:
        result.setdefault(row["Chapter"], {}).setdefault(row["Section"], []).append(row)
    return result


def load_json() -> dict:
    if JSON_PATH.exists():
        with open(JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"lesson_plan_base_url": LESSON_PLAN_BASE_URL, "facilitators": FACILITATORS, "courses": []}


def save_json(data: dict):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved → {JSON_PATH}")


# ── Course builder ────────────────────────────────────────────────────────────

def build_course_from_csv(rows: list[dict], existing: dict | None) -> dict:
    """
    Build a course dict purely from CSV rows, preserving non-CSV fields from
    any existing JSON entry.

    Preserved from existing (never overwritten by this script):
      chapter_number, section_number
      course_logo_file  (even if None — None means 'deliberately unset')
      moodle_course_folder
      moodle_section_id / forum_id per lesson (matched by subsection+subsubsection filecase)
    """
    rep              = rows[0]
    chapter          = rep["Chapter"]
    chapter_filecase = rep["Chapter Filecase"]
    section          = rep["Section"]
    section_filecase = rep["Section Filecase"]

    # ── Course-level fields from CSV ──
    moodle_course_id    = extract_course_id_from_url(rep.get("Course URL", ""))
    student_section_url = (
        f"https://innodems.github.io/CBC-Grade-10-Maths/student/sec-{section_filecase}.html"
    )

    # ── Preserve non-CSV fields from existing entry ──
    chapter_number = existing.get("chapter_number") if existing else None
    section_number = existing.get("section_number") if existing else None

    # Logo: preserve if key exists in existing (even if value is None).
    # If the key isn't there at all, try to auto-detect from assets.
    if existing and "course_logo_file" in existing:
        course_logo_file = existing["course_logo_file"]
    else:
        course_logo_file = find_course_logo(section_filecase)

    # Folder name: preserve an existing name (could be the real extracted folder);
    # generate a clean placeholder for new courses.
    if existing and existing.get("moodle_course_folder"):
        moodle_course_folder = existing["moodle_course_folder"]
    else:
        moodle_course_folder = f"backup-moodle2-course-{moodle_course_id}-{section_filecase}"

    # ── Learning outcomes (deduplicated, ordered by first appearance) ──
    lo_texts: dict[str, str] = {}   # description → id
    for row in rows:
        for col in ("LO 1", "LO 2", "LO 3", "LO 4"):
            text = row.get(col, "").strip()
            if text and text not in lo_texts:
                lo_texts[text] = lo_id(text)

    learning_outcomes = [{"id": lid, "description": desc} for desc, lid in lo_texts.items()]

    # ── Lesson ID preservation ──
    # Build a lookup of existing lesson IDs keyed by (subsection_fc, subsubsection_fc).
    existing_lesson_ids: dict[tuple, tuple] = {}
    if existing:
        for lesson in existing.get("lessons", []):
            key = (lesson.get("subsection_filecase"), lesson.get("subsubsection_filecase"))
            existing_lesson_ids[key] = (
                lesson.get("moodle_section_id"),
                lesson.get("forum_id"),
            )

    # Next available placeholder IDs (above the highest existing one within this course).
    used_sids = [sid for sid, _ in existing_lesson_ids.values() if sid]
    used_fids = [fid for _, fid in existing_lesson_ids.values() if fid]
    next_sid  = max(used_sids + [100000]) + 1
    next_fid  = max(used_fids + [101000]) + 1

    # ── Build lessons ──
    lessons = []
    for row in rows:
        subsection             = row.get("Subsection", "").strip() or None
        subsection_filecase    = row.get("Subsection Filecase", "").strip() or None
        subsubsection          = row.get("Subsubsection", "").strip() or None
        subsubsection_filecase = row.get("Subsubsection Filecase", "").strip() or None

        key = (subsection_filecase, subsubsection_filecase)
        if key in existing_lesson_ids and all(v is not None for v in existing_lesson_ids[key]):
            moodle_section_id, forum_id = existing_lesson_ids[key]
        else:
            moodle_section_id = next_sid;  next_sid += 1
            forum_id          = next_fid;  next_fid += 1

        lesson_lo_ids = []
        for col in ("LO 1", "LO 2", "LO 3", "LO 4"):
            text = row.get(col, "").strip()
            if text and text in lo_texts:
                lid = lo_texts[text]
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

    return {
        "moodle_course_id":     moodle_course_id,
        "moodle_course_folder": moodle_course_folder,
        "chapter":              chapter,
        "chapter_filecase":     chapter_filecase,
        "chapter_number":       chapter_number,
        "section":              section,
        "section_filecase":     section_filecase,
        "section_number":       section_number,
        "student_section_url":  student_section_url,
        "course_logo_file":     course_logo_file,
        "learning_outcomes":    learning_outcomes,
        "lessons":              lessons,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Reading CSV…")
    rows    = load_csv()
    grouped = group_by_chapter_section(rows)
    data    = load_json()

    # Index existing courses by section_filecase for fast lookup + preservation.
    existing_index: dict[str, dict] = {
        c["section_filecase"]: c for c in data.get("courses", [])
    }

    new_courses = []
    added = updated = 0

    for chapter, sections in grouped.items():
        for section, section_rows in sections.items():
            section_filecase = section_rows[0]["Section Filecase"]
            existing = existing_index.get(section_filecase)
            course   = build_course_from_csv(section_rows, existing)
            new_courses.append(course)

            tag = "updated" if existing else "added"
            n   = len(section_rows)
            logo_note = f", logo={course['course_logo_file']!r}" if course["course_logo_file"] else ""
            ch_note   = f"  ch={course['chapter_number']}" if course["chapter_number"] else "  ch=?"
            se_note   = f" sec={course['section_number']}" if course["section_number"] else " sec=?"
            print(f"  [{tag:7s}] {section:<45s} {n:2d} lessons{ch_note}{se_note}{logo_note}")

            if existing:
                updated += 1
            else:
                added += 1

    data["courses"]            = new_courses
    data["lesson_plan_base_url"] = LESSON_PLAN_BASE_URL
    data.setdefault("facilitators", FACILITATORS)

    print()
    save_json(data)
    print(f"\nDone: {added} new, {updated} updated, {len(new_courses)} total courses.\n")

    # Report fields still missing (will be asked by generate_course.py)
    missing_fields: list[str] = []
    for c in new_courses:
        gaps = []
        if c["chapter_number"] is None: gaps.append("chapter_number")
        if c["section_number"]  is None: gaps.append("section_number")
        if c["course_logo_file"] is None: gaps.append("course_logo_file")
        if gaps:
            missing_fields.append(f"  {c['section']}: {', '.join(gaps)}")

    if missing_fields:
        print("Fields still needed (will be asked when running generate_course.py):")
        for line in missing_fields:
            print(line)
    else:
        print("All courses fully populated — ready to generate!")


if __name__ == "__main__":
    main()
