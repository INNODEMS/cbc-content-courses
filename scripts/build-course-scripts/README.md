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

## Planned steps

| Script | What it does |
|--------|______________|
| `create_blank_course.py` | Scaffold the minimal valid MBZ folder structure with empty/stub XML files |
| `populate_course_info.py` | Write course name, description, and metadata into `course/course.xml` |
| `add_sections.py` | Add lesson sections and the certificate section |
| `add_activities.py` | Add forum activities to each section |
| `add_assets.py` | Copy logo images and write `files.xml` / `inforef.xml` entries |
| `apply_css.py` | Inject HTML/CSS templates into section and course summaries |
| `compress.py` | Zip the folder into a `.mbz` ready for Moodle upload |

---

## Usage

Run scripts in order from the repo root:

```bash
python scripts/build-course-scripts/create_blank_course.py <course-id>
python scripts/build-course-scripts/populate_course_info.py <course-id>
# ... and so on
```

Each script reads from and writes to `courses-extracted/<course-id>/`, so the state
is always inspectable on disk between steps. When ready, run `compress.py` to
produce the final `.mbz` in `courses-built/`.
