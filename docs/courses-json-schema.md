# `data/courses.json` Schema Reference

`courses.json` is the central data store for the course-generation pipeline. It is read by `generate_course.py` and updated by both `populate_courses_json.py` (automated sync) and `generate_course.py` (interactive gap-filler).

---

## Top-level structure

```json
{
  "lesson_plan_base_url": "https://innodems.github.io/CBC-Grade-10-Maths/external/lesson_plans/",
  "facilitators": [...],
  "courses": [...]
}
```

| Field | Type | Description |
|---|---|---|
| `lesson_plan_base_url` | string | Base URL prepended to `lesson_plan_path` when generating PDF links |
| `facilitators` | array | Contact details used in the course welcome message |
| `courses` | array | One entry per CBC Grade 10 Math course (15 total) |

---

## Facilitator object

```json
{
  "name": "Dr. Michael Obiero",
  "email": "obiero@maseno.ac.ke",
  "phone": "+254737456117"
}
```

---

## Course object

```json
{
  "moodle_course_id": 571,
  "moodle_course_folder": "backup-moodle2-course-571-real_numbers-20260218-1335-nu",
  "chapter": "Numbers and Algebra",
  "chapter_filecase": "numbers-and-algebra",
  "chapter_number": 1,
  "section": "Real Numbers",
  "section_filecase": "real-numbers",
  "section_number": 1,
  "student_section_url": "https://innodems.github.io/CBC-Grade-10-Maths/student/sec-real-numbers.html",
  "course_logo_file": "real-numbers.jpg",
  "learning_outcomes": [...],
  "lessons": [...]
}
```

### Course-level fields

| Field | Type | Source | Notes |
|---|---|---|---|
| `moodle_course_id` | int \| null | CSV (`Course URL`) | Numeric ID from the Moodle URL (`?id=571`). `null` if no URL in CSV (e.g. Similarity and Enlargement). Remapped by Moodle on restore — informational only. |
| `moodle_course_folder` | string | Auto-generated or preserved | Used as the output directory name inside `courses-extracted/`. For deployed courses the real backup folder name is preserved. |
| `chapter` | string | CSV (`Chapter`) | Full chapter name, e.g. `"Numbers and Algebra"` |
| `chapter_filecase` | string | CSV (`Chapter Filecase`) | URL-safe kebab-case, e.g. `"numbers-and-algebra"` |
| `chapter_number` | int \| null | User prompt (`generate_course.py`) | CBC curriculum chapter number. Not in CSV. Asked once, saved back. |
| `section` | string | CSV (`Section`) | Full course/section name, e.g. `"Real Numbers"` |
| `section_filecase` | string | CSV (`Section Filecase`) | URL-safe kebab-case, e.g. `"real-numbers"`. Used as the unique key for this course. |
| `section_number` | int \| null | User prompt (`generate_course.py`) | Position within the chapter. Not in CSV. Asked once, saved back. |
| `student_section_url` | string | Auto-generated | `https://innodems.github.io/CBC-Grade-10-Maths/student/sec-<section_filecase>.html` |
| `course_logo_file` | string \| null | Auto-detected or user prompt | Filename inside `assets/course-logos/`. Auto-detected if a file matching `<section_filecase>.<ext>` exists. Set to `null` to explicitly have no logo. |
| `learning_outcomes` | array | CSV (LO 1–4) | Deduplicated list of all LOs across the course; each has a stable hash-based `id`. |
| `lessons` | array | CSV (one entry per row) | Ordered list of lessons/activities within the course. |

---

## Learning outcome object

```json
{
  "id": "lo-184050140f",
  "description": "Classify whole numbers as odd, even, prime and composite in different situations"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable ID: `"lo-"` + first 10 chars of `sha1(description)`. Deterministic — same text always gets the same ID. |
| `description` | string | The full LO text as it appears in the CSV. |

---

## Lesson object

```json
{
  "subsection": "Classification of Numbers",
  "subsection_filecase": "classification-of-numbers",
  "subsubsection": "Even and Odd Numbers",
  "subsubsection_filecase": "even-and-odd-numbers",
  "moodle_section_id": 6907,
  "forum_id": 22512,
  "lesson_plan_path": "numbers-and-algebra/real-numbers/even-and-odd-numbers.pdf",
  "step_by_step_path": "numbers-and-algebra/real-numbers/step-by-step-guide_even-and-odd-numbers.pdf",
  "lesson_plan_exists": true,
  "step_by_step_exists": true,
  "learning_outcome_ids": ["lo-184050140f"]
}
```

| Field | Type | Source | Notes |
|---|---|---|---|
| `subsection` | string \| null | CSV | Groups lessons into sub-topics. `null` for top-level lessons. |
| `subsection_filecase` | string \| null | CSV | Kebab-case version of `subsection`. |
| `subsubsection` | string \| null | CSV | The specific lesson title. Usually present when `subsection` is set. |
| `subsubsection_filecase` | string \| null | CSV | Kebab-case version of `subsubsection`. |
| `moodle_section_id` | int | Preserved or auto-generated | Moodle DB section ID from the source backup, or a placeholder (100001+). Matched and preserved by `(subsection_filecase, subsubsection_filecase)`. Remapped on restore. |
| `forum_id` | int | Preserved or auto-generated | Moodle DB module/forum ID for this lesson's discussion forum. Placeholder (101001+) for new courses. Remapped on restore. |
| `lesson_plan_path` | string | CSV | Path relative to `lesson_plan_base_url`. Append to the base URL to get the full PDF link. |
| `step_by_step_path` | string | CSV | Same pattern as `lesson_plan_path`. |
| `lesson_plan_exists` | bool | CSV (`Lesson Plan Exists`) | Whether the PDF is actually published. The link is only shown in the generated course if `true`. |
| `step_by_step_exists` | bool | CSV (`Step By Step Guide Exists`) | Same for the step-by-step guide. |
| `learning_outcome_ids` | array of strings | CSV (LO 1–4 for this row) | References to `id` values in the course-level `learning_outcomes` array. |

---

## Null vs missing

- A field set to `null` means it was **deliberately left unset** (or hasn't been answered yet).
- `course_logo_file: null` is treated as "no logo" — the course can still be generated without one.
- `populate_courses_json.py` preserves existing `null` values rather than re-detecting; the distinction of "key absent" vs "key present but null" matters for logo auto-detection logic.

---

## ID preservation logic

`populate_courses_json.py` matches existing lessons by `(subsection_filecase, subsubsection_filecase)`. If a match is found, the existing `moodle_section_id` and `forum_id` are reused. This preserves real Moodle IDs for deployed courses (like Real Numbers, which uses IDs 6907, 6923–6928).

For genuinely new lessons, IDs are auto-incremented from `max(existing_ids_in_course) + 1`.

---

## Unique key

Each course is uniquely identified by `section_filecase`. This is the lookup key used by both `populate_courses_json.py` (to match existing entries) and `generate_course.py` (to select a course by name).
