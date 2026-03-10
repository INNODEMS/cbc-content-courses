# build-course-scripts

Scripts in this folder build a Moodle course backup (`.mbz`) one step at a time.
Each script does exactly one thing and can be run and inspected independently.
This makes it easy to debug at each stage before moving on.

---

## Philosophy

Rather than generating a complete course in one go, the pipeline is broken into
small, discrete steps. After each step you can open the output in
`courses-extracted/` and verify it looks correct before running the next one.

---

## Steps

| Script | What it does |
|--------|--------------|
| `create_blank_course.py` | Scaffold the minimal valid MBZ folder structure with empty/stub XML files |
| `populate_course.py` | Populate sections and forum activities from a JSON data file |
| `populate_course_info.py` | Write course name, description, and metadata into `course/course.xml` |
| `add_assets.py` | Copy logo images and write `files.xml` / `inforef.xml` entries |
| `apply_css.py` | Inject HTML/CSS templates into section and course summaries |
| `compress.py` | Zip the folder into a `.mbz` ready for Moodle upload |

---

## Usage

Run scripts in order from the repo root:

```bash
python scripts/build-course-scripts/create_blank_course.py <folder-name>
python scripts/build-course-scripts/populate_course.py <folder-name>
# ... and so on
```

Each script reads from and writes to `courses-extracted/<folder-name>/`, so the state
is always inspectable on disk between steps. When ready, run `compress.py` to
produce the final `.mbz` in `courses-built/`.

---

## Testing `populate_course.py`

### Step 1 — Create a blank course (if one doesn't exist yet)

```bash
python scripts/build-course-scripts/create_blank_course.py
```

You will be prompted to enter a course name. The script will derive a folder name
from it (lowercase, hyphenated) and ask you to confirm before creating it.
The course fullname and shortname will both be set to the name you enter.

Example:
```
Enter course name: Real Numbers
  Folder name will be: real-numbers
  Proceed? [Y/n]:
```

This creates `courses-extracted/real-numbers/` with a minimal valid structure.

---

### Step 2 — Add course data and populate

Edit `data/new-course-sections-data.json` with your course content. Each entry in
the `"sections"` array represents one content section with an optional forum activity:

```json
{
  "sections": [
    {
      "title": "Section title",
      "description": "Section description.",
      "show_description": true,
      "activities": [
        {
          "type": "forum",
          "title": "Forum title",
          "description": "Forum description.",
          "show_description": false
        }
      ]
    }
  ]
}
```

Then run:

```bash
python scripts/build-course-scripts/populate_course.py
```

You will be prompted to select a course from `courses-extracted/`. The script will:

- Remove any existing content sections (section 0 / Announcements is preserved)
- Write fresh section and forum activity folders from the JSON
- Rebuild `moodle_backup.xml` to reflect the new structure

**What to verify in `courses-extracted/<folder-name>/`:**

- `sections/` — one subfolder per section. Each `section.xml` should have the correct `<name>`, `<summary>`, and `<sequence>`.
- `activities/` — one `forum_N/` subfolder per forum. Check `forum.xml` for `<name>` and `<intro>`, and `module.xml` for `<showdescription>`.
- `moodle_backup.xml` — all sections and activities listed under `<contents>` and `<settings>`.

---

### Step 3 — Compress

```bash
python scripts/build-course-scripts/compress.py
```

Select `new-blank-course`. The output `.mbz` will be written to `courses-built/`,
ready to upload to Moodle.
