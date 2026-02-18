# cbc-content-courses

This repository is for editing and version controlling Moodle course content.

## To-do

- Spearate the repo in terms of content and scripts. Scripts should be in an IDEMS repo, content should remain in an INNODEMS repo
- Figure out how to make them talk to each other so that scripts from the IDEMS repo can be read and launched from the INNODEMS repo once separated
- Write script that reads from the spreadsheet and generates a json with all the data
- Write a script that populates courses with the data from the json
- Write a script that compresses a course into an mbz file that is compatible with course files in Moodle


## Workflow

### 1. Add MBZ Files

Place your Moodle backup files (`.mbz`) in the `raw-mbz-files/` directory.

### 2. Extract a Course

Run the extraction script with the specific MBZ file you want to extract:

```bash
python scripts/extract_mbz.py <filename.mbz>
```

**Example:**
```bash
python scripts/extract_mbz.py backup-moodle2-course-571-real_numbers-20260218-1335-nu.mbz
```

The script will:
- Extract the specified MBZ file to `cuorses-extracted/<course-name>/`
- Overwrite any existing folder with the same name
- Support ZIP, TAR.GZ, and GZIP archive formats

**Important:** You must specify which file to extract. This prevents accidentally overwriting courses you've already edited.

### 3. Edit Course Content

Once extracted, you can edit the course files in `cuorses-extracted/`:
- **moodle_backup.xml** - Main course structure and metadata
- **activities/** - Course activities and resources
- **sections/** - Course sections
- **files/** - Media files and attachments
- Various XML files for gradebook, questions, roles, etc.

### 4. Version Control

Commit your changes to git to track course modifications over time.

## Directory Structure

```
├── raw-mbz-files/          # Original MBZ backup files
├── cuorses-extracted/      # Extracted course content (editable)
└── scripts/                # Utility scripts
    └── extract_mbz.py      # Extraction script
```
