# `data/automatic-links.csv` Schema Reference

`automatic-links.csv` is the **source of truth** for all lesson-level content data. It is read by `populate_courses_json.py` and drives the structure of every course in `courses.json`.

The file has **132 data rows** (plus a header), covering **15 courses** across **3 chapters**.

---

## Columns

| Column | Type | Example | Description |
|---|---|---|---|
| `Chapter` | string | `Numbers and Algebra` | Top-level curriculum chapter. Groups courses. |
| `Section` | string | `Real Numbers` | Course name within the chapter. One Moodle course per section. |
| `Subsection` | string | `Classification of Numbers` | Sub-topic grouping within the course. May be empty at the top level. |
| `Subsubsection` | string | `Even and Odd Numbers` | Individual lesson title. Usually the deepest level. |
| `In Syllabus` | `Yes` / `No` | `Yes` | Whether this lesson is included in the CBC syllabus. All current rows are `Yes`. |
| `Chapter Filecase` | string | `numbers-and-algebra` | Kebab-case version of `Chapter`. Used in file paths and URLs. |
| `Section Filecase` | string | `real-numbers` | Kebab-case version of `Section`. **Unique key** for the course. |
| `Subsection Filecase` | string | `classification-of-numbers` | Kebab-case version of `Subsection`. |
| `Subsubsection Filecase` | string | `even-and-odd-numbers` | Kebab-case version of `Subsubsection`. |
| `PTX Path` | string | `numbers-and-algebra/real-numbers/subsubsec-even-and-odd-numbers.ptx` | Path to the PreTeXt source file in the content repo. Not used by the pipeline scripts directly. |
| `Lesson Plan Path` | string | `numbers-and-algebra/real-numbers/even-and-odd-numbers.pdf` | Relative path appended to `lesson_plan_base_url` to form the lesson plan PDF link. |
| `Step By Step Guide Path` | string | `numbers-and-algebra/real-numbers/step-by-step-guide_even-and-odd-numbers.pdf` | Same structure as `Lesson Plan Path`. |
| `LO 1` | string | `Classify whole numbers as odd, even, prime…` | First learning outcome for this lesson. May be empty. |
| `LO 2` | string | _(empty for most rows)_ | Second learning outcome. Often empty. |
| `LO 3` | string | _(empty)_ | Third learning outcome. |
| `LO 4` | string | _(empty)_ | Fourth learning outcome. |
| `Course URL` | string \| empty | `https://ecampus.idems.international/course/view.php?id=571` | Moodle course URL. The numeric `id` parameter is extracted as `moodle_course_id`. Empty for courses not yet deployed (e.g. Similarity and Enlargement). |
| `PTX Exists` | `YES` / `NO` | `YES` | Whether the PTX source file exists. Not currently used by the pipeline. |
| `Lesson Plan Exists` | `YES` / `NO` | `YES` | Controls whether the Lesson Plan button appears in the generated course section. |
| `Step By Step Guide Exists` | `YES` / `NO` | `YES` | Controls whether the Step-by-Step Guide button appears. |

---

## Courses in the file

### Numbers and Algebra (chapter_number = 1)

| section_filecase | Moodle ID | Lessons |
|---|---|---|
| `real-numbers` | 571 | 6 |
| `indices-and-logarithms` | 573 | 11 |
| `quadratic-expressions-and-equations` | 574 | 11 |

### Measurements and Geometry (chapter_number = 4)

| section_filecase | Moodle ID | Lessons |
|---|---|---|
| `similarity-and-enlargement` | _(none)_ | 6 |
| `reflection-and-congruence` | present | 5 |
| `rotation` | present | 6 |
| `trigonometry-1` | present | 9 |
| `area-of-polygons` | present | 13 |
| `area-of-a-part-of-a-circle` | present | 6 |
| `surface-area` | present | 9 |
| `volume` | present | 9 |
| `vectors-1` | present | 11 |
| `linear-motion` | present | 8 |

### Statistics and Probability (chapter_number = 5)

| section_filecase | Moodle ID | Lessons |
|---|---|---|
| `statistics-1` | present | 13 |
| `probability-1` | present | 8 |

---

## How the CSV feeds into courses.json

`populate_courses_json.py` processes the CSV in order:

1. Groups rows by `(Chapter, Section)` — one group per course.
2. Extracts the representative values (first row per group) for course-level fields.
3. Deduplicates LOs across all four LO columns and all rows in the group.
4. Maps each row to a lesson entry.
5. Generates a stable `lo-<hash>` ID for each unique LO text.

The `Lesson Plan Exists` and `Step By Step Guide Exists` columns are normalised to booleans (`YES` → `true`, anything else → `false`).

---

## Filecase naming convention

Filecase values are lowercase kebab-case representations of their display names:
- Spaces become `-`
- All letters are lowercase
- Special characters are dropped

Example: `"Area of a Part of a Circle"` → `"area-of-a-part-of-a-circle"`

These are used in file paths, folder names, and generated URLs throughout the pipeline. They are **authoritative in the CSV** — if a filecase needs to change, update the CSV and re-run `populate_courses_json.py`.

---

## Updating the CSV

After any edit to `automatic-links.csv`:

```bash
python scripts/populate_courses_json.py
```

This re-syncs `courses.json` without disturbing manually-set fields (`chapter_number`, `section_number`, `course_logo_file`, real Moodle IDs from deployed courses).
