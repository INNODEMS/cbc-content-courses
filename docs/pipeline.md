# Course Authoring Pipeline

This document describes the full end-to-end process for creating and maintaining Moodle MBZ course backups for **CBC Kenya Grade 10 Mathematics**.

---

## Overview

The pipeline has two main branches:

```
CSV (automatic-links.csv)
        │
        ▼
 1. populate_courses_json.py   ← sync CSV into data/courses.json
        │
        ▼
 2. generate_course.py         ← build MBZ folder from courses.json
        │
        ▼
 3. compress_mbz.py            ← zip folder → .mbz file
        │
        ▼
 4. Upload to Moodle           ← Site administration → Courses → Restore
```

There is also a separate **edit** branch for manually tweaking courses that already have real Moodle backups:

```
raw-mbz-files/<course>.mbz
        │
        ▼
 extract_mbz.py                ← unzip into courses-extracted/
        │
   (edit XML files)
        │
        ▼
 compress_mbz.py               ← repack to compressed-mbz-files/
```

---

## Step 1 — Sync the CSV to JSON

**Script:** `scripts/populate_courses_json.py`  
**Input:** `data/automatic-links.csv`  
**Output:** `data/courses.json`

```bash
python scripts/populate_courses_json.py
```

This is **non-interactive**. It reads every row in the CSV and writes all 15 courses into `courses.json`. Run it whenever the CSV is updated.

### What it syncs from the CSV

| JSON field | CSV source |
|---|---|
| `chapter` / `chapter_filecase` | Chapter / Chapter Filecase |
| `section` / `section_filecase` | Section / Section Filecase |
| `moodle_course_id` | Extracted from Course URL (e.g. `?id=571`) |
| `student_section_url` | Auto-generated from `section_filecase` |
| `learning_outcomes` | LO 1 – LO 4 (deduplicated across the course) |
| Lesson `subsection` / `subsubsection` | Subsection / Subsubsection + Filecase variants |
| Lesson `lesson_plan_path` | Lesson Plan Path |
| Lesson `step_by_step_path` | Step By Step Guide Path |
| `lesson_plan_exists` / `step_by_step_exists` | Lesson Plan Exists / Step By Step Guide Exists |
| Lesson `learning_outcome_ids` | Which LOs apply to each row |

### What it does NOT overwrite

These fields are set elsewhere and preserved across runs:

| Field | Set by |
|---|---|
| `chapter_number` / `section_number` | `generate_course.py` (user prompt) |
| `course_logo_file` | `generate_course.py` (user prompt or auto-detected) |
| `moodle_course_folder` | Preserved if the real extracted folder name is used |
| Per-lesson `moodle_section_id` / `forum_id` | Preserved from deployed courses (e.g. Real Numbers) |

### Logo auto-detection

On first sync for a course, if a file named `<section_filecase>.<ext>` exists in `assets/course-logos/`, it is set as `course_logo_file` automatically. Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.svg`.

### After running

The script prints a summary of every course (added/updated, lesson count, chapter/section numbers if known) and a list of fields that are still `null` — these will be asked when you run the generator.

---

## Step 2 — Generate a Course MBZ Folder

**Script:** `scripts/generate_course.py`  
**Input:** `data/courses.json`  
**Output:** `courses-extracted/<folder-name>/`

```bash
python scripts/generate_course.py                     # interactive menu
python scripts/generate_course.py <key>               # by index or section_filecase
python scripts/generate_course.py <key> --compress    # also compress immediately
```

**Examples:**

```bash
python scripts/generate_course.py indices-and-logarithms
python scripts/generate_course.py 3
python scripts/generate_course.py trigonometry-1 --compress
```

### Interactive gap-filling

If any of the following fields are `null` in `courses.json`, the script asks for them before generating and **saves the answers back to `courses.json`** so they are never asked again:

| Field | Example prompt |
|---|---|
| `chapter_number` | `Chapter number for 'Numbers and Algebra' (e.g. 1, 4, 5):` |
| `section_number` | `Section number for 'Indices and Logarithms' within chapter 1:` |
| `course_logo_file` | `Logo filename for 'Indices and Logarithms' (in assets/course-logos/):` |

### What is generated

Inside `courses-extracted/<folder>/`:

| Path | Contents |
|---|---|
| `moodle_backup.xml` | Master manifest — lists all sections, activities, settings |
| `course/course.xml` | Course name, format (`flexsections`), summary HTML |
| `course/inforef.xml` | File references for the course logo |
| `sections/section_<id>/section.xml` | One per lesson: title, content HTML with resource buttons |
| `activities/forum_<id>/` | Discussion forum for each lesson (announcement + link) |
| `activities/forum_22478/` | Shared Announcements forum (section 0) |
| `activities/customcert_*/` | Course completion certificate |
| `files/` | Content-addressed files (logo images, cert background) |
| `gradebook.xml`, `roles.xml`, etc. | Required scaffold files |

### Section content

Each lesson section contains a **Quick Access** HTML box with up to four links (rendered as styled buttons):

1. Student notes (always present) — links to the PreTeXt student page
2. Lesson plan (if `lesson_plan_exists: true`) — links to the PDF
3. Step-by-step guide (if `step_by_step_exists: true`) — links to the PDF
4. Discussion forum (always present) — deep-links into the Moodle activity

### Placeholder IDs

For courses not yet deployed to Moodle, the generator assigns placeholder section and forum IDs (100001+, 101001+). These are reassigned by Moodle on restore — see [moodle-id-generation.md](moodle-id-generation.md) for details.

---

## Step 3 — Compress to MBZ

**Script:** `scripts/compress_mbz.py`  
**Input:** `courses-extracted/<folder>/`  
**Output:** `compressed-mbz-files/<folder>.mbz`

```bash
python scripts/compress_mbz.py <folder-name>
python scripts/compress_mbz.py <folder-name> <custom-output-name>.mbz
```

**Example:**

```bash
python scripts/compress_mbz.py backup-moodle2-course-None-indices-and-logarithms
```

This is also called automatically when you pass `--compress` to `generate_course.py`.

---

## Step 4 — Upload to Moodle

1. Go to **Site administration → Courses → Restore**
2. Upload the `.mbz` file from `compressed-mbz-files/`
3. Follow the restore wizard (choose target category, confirm settings)
4. Moodle remaps all internal IDs — the placeholder values do not matter

---

## Editing an Existing Course Backup

Use this flow when you have a real `.mbz` from Moodle and want to manually edit its XML:

### Extract

```bash
python scripts/extract_mbz.py <filename.mbz>
```

Place the source `.mbz` in `raw-mbz-files/` first. The script extracts it to `courses-extracted/<name>/`.

### Edit

Edit the XML files directly in `courses-extracted/<name>/`. Then commit to git to track the change.

### Repack

```bash
python scripts/compress_mbz.py <folder-name>
```

Output goes to `compressed-mbz-files/`.

---

## Re-running the Pipeline

When you need to update an already-generated course (e.g. after CSV changes):

1. **`python scripts/populate_courses_json.py`** — pulls latest CSV data; preserves all manually-set fields
2. **`python scripts/generate_course.py <key>`** — regenerates the folder; existing `courses-extracted/<folder>/` is replaced
3. **`python scripts/compress_mbz.py <folder>`** — repack

No fields will be asked again as long as `chapter_number`, `section_number`, and `course_logo_file` are already set in `courses.json`.

---

## Script Summary

| Script | Interactive? | Description |
|---|---|---|
| `populate_courses_json.py` | No | Sync entire CSV → courses.json |
| `generate_course.py` | Only for missing fields | Build MBZ folder from courses.json |
| `compress_mbz.py` | No | Zip a `courses-extracted/` folder to `.mbz` |
| `extract_mbz.py` | No | Unzip a raw `.mbz` to `courses-extracted/` |
