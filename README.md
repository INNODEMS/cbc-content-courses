# cbc-content-courses

Moodle course content for **CBC Kenya Grade 10 Mathematics** — 15 courses covering Numbers and Algebra, Measurements and Geometry, and Statistics and Probability.

The repo contains scripts for generating fresh MBZ course backups from a CSV data source, as well as tools for editing and repackaging existing Moodle backups.

---

## Quick start — generate a course from scratch

```bash
# 1. Sync the CSV into courses.json (non-interactive, safe to re-run)
python scripts/populate_courses_json.py

# 2. Generate the MBZ folder for one course
#    (will ask for chapter/section number and logo on first run, then saves them)
python scripts/generate_course.py indices-and-logarithms

# 3. Compress to .mbz and upload to Moodle
python scripts/compress_mbz.py backup-moodle2-course-573-indices-and-logarithms
```

See [docs/pipeline.md](docs/pipeline.md) for the full end-to-end guide.

---

## Quick start — edit an existing backup

```bash
# 1. Extract the raw backup
python scripts/extract_mbz.py backup-moodle2-course-571-real_numbers-20260218-1335-nu.mbz

# 2. Edit XML files in courses-extracted/<folder>/

# 3. Repack
python scripts/compress_mbz.py backup-moodle2-course-571-real_numbers-20260218-1335-nu
```

---

## Directory structure

```
+-- assets/
¦   +-- course-logos/           # Logo images for each course (jpg/png)
+-- compressed-mbz-files/       # Output .mbz files ready for Moodle upload
+-- courses-extracted/          # Extracted course folders (editable XML)
+-- data/
¦   +-- automatic-links.csv     # Source of truth: all lessons, LOs, file paths
¦   +-- courses.json            # Generated course data (synced from CSV)
+-- docs/
¦   +-- pipeline.md             # End-to-end workflow guide
¦   +-- courses-json-schema.md  # courses.json field reference
¦   +-- csv-schema.md           # automatic-links.csv column reference
¦   +-- moodle-id-generation.md # How Moodle IDs work in MBZ files
+-- raw-mbz-files/              # Original .mbz backups (unmodified)
+-- scripts/
    +-- populate_courses_json.py # Sync CSV ? courses.json (non-interactive)
    +-- generate_course.py       # Build MBZ folder from courses.json
    +-- compress_mbz.py          # Zip a courses-extracted/ folder ? .mbz
    +-- extract_mbz.py           # Unzip a raw .mbz ? courses-extracted/
```

---

## Documentation

| Doc | Description |
|---|---|
| [docs/pipeline.md](docs/pipeline.md) | Full step-by-step workflow for both the generate and edit pipelines |
| [docs/courses-json-schema.md](docs/courses-json-schema.md) | Field reference for `data/courses.json` |
| [docs/csv-schema.md](docs/csv-schema.md) | Column reference for `data/automatic-links.csv` |
| [docs/moodle-id-generation.md](docs/moodle-id-generation.md) | How MBZ IDs work and how placeholder IDs are assigned |

---

## Courses

15 courses are tracked in this repo:

| Chapter | Course | Status |
|---|---|---|
| Numbers and Algebra | Real Numbers | ? Deployed (id 571) |
| Numbers and Algebra | Indices and Logarithms | ? Deployed (id 573) |
| Numbers and Algebra | Quadratic Expressions and Equations | ? Deployed (id 574) |
| Measurements and Geometry | Similarity and Enlargement | — |
| Measurements and Geometry | Reflection and Congruence | ? Deployed |
| Measurements and Geometry | Rotation | ? Deployed |
| Measurements and Geometry | Trigonometry 1 | ? Deployed |
| Measurements and Geometry | Area of Polygons | ? Deployed |
| Measurements and Geometry | Area of a Part of a Circle | ? Deployed |
| Measurements and Geometry | Surface Area | ? Deployed |
| Measurements and Geometry | Volume | ? Deployed |
| Measurements and Geometry | Vectors 1 | ? Deployed |
| Measurements and Geometry | Linear Motion | ? Deployed |
| Statistics and Probability | Statistics 1 | ? Deployed |
| Statistics and Probability | Probability 1 | ? Deployed |
