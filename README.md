# cbc-content-courses

Moodle course content for **CBC Kenya Grade 10 Mathematics** - 15 courses covering Numbers and Algebra, Measurements and Geometry, and Statistics and Probability.

---

## Extracting a course

Place `.mbz` backup files in `compressed-mbz-files/`, then run:

```bash
python scripts/extract_mbz.py
```

The script will display a numbered list of all `.mbz` files available and prompt you to choose one:

```
Available courses:
  1. backup-moodle2-course-583-testing_new-20260309-1558-nu.mbz

Enter number to extract:
```

The chosen backup is unpacked into `courses-extracted/<filename>/` where all the Moodle XML files can be inspected and edited directly. If a folder with that name already exists it is overwritten automatically.

You can also pass the filename directly to skip the prompt:

```bash
python scripts/extract_mbz.py backup-moodle2-course-583-testing_new-20260309-1558-nu.mbz
```

---

## Building a course

Scripts in `scripts/build-course-scripts/` build a course one step at a time.
Each script writes its output to `courses-extracted/<folder-name>/` so you can
inspect the XML at any stage before moving on.

### 1. Create the blank scaffold

Creates the full Moodle backup folder structure with all required stub XML
files, an Announcements forum in section 0, and one empty section.

```bash
python scripts/build-course-scripts/create_blank_course.py [folder-name]
```

Defaults to `new-blank-course` if no name is given.

### 2. Compress to .mbz

Zips a course folder from `courses-extracted/` into a `.mbz` file in
`courses-built/` ready for upload to Moodle. Prompts with a numbered list of
all courses in `courses-extracted/`.

```bash
python scripts/build-course-scripts/compress.py [folder-name]
```

Both scripts accept an optional name argument to skip the interactive prompt.

---

## Directory structure

```
assets/
  logos/                        # Institutional logo images
compressed-mbz-files/           # .mbz backups from Moodle server (input)
courses-extracted/              # Working folder: extracted and newly built courses
courses-built/                  # Output .mbz files ready for Moodle upload
scripts/
  extract_mbz.py                # Extract a .mbz into courses-extracted/
  build-course-scripts/         # Step-by-step scripts for building a course
```