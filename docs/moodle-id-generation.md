# Moodle MBZ IDs: How They Work and How to Generate Them

## Overview

When manually creating or modifying a Moodle backup (`.mbz`) file, you need to assign IDs to new sections and activities. This document explains what these IDs are, how Moodle uses them during restore, and the safe approach for generating new ones.

---

## What Are IDs in an MBZ File?

The IDs embedded in MBZ XML files (e.g. `<section id="6923">`, `<module id="22525">`) are the **original database row IDs** from the Moodle instance that created the backup. For example, in our courses:

| Type | Example ID | Example |
|------|-----------|---------|
| Section | `6903` | `sections/section_6903/section.xml` → `<section id="6903">` |
| Course module | `22525` | `activities/forum_22525/module.xml` → `<module id="22525">` |
| Activity instance | `22525` | `activities/forum_22525/forum.xml` → `<forum id="22525">` |
| Course | `571` | `course/course.xml` → `<course id="571">` |
| Context | `165404` | `course/course.xml` → `<course id="571" contextid="165404">` |

These IDs are specific to the source Moodle database. They are **not** the IDs the content will have after restore — Moodle remaps everything.

---

## How Moodle Handles IDs During Restore

When you restore an MBZ to a new course, Moodle:

1. **Reads the old IDs** from the XML files.
2. **Creates new database records** (sections, course modules, activity instances) in the destination Moodle database.
3. **Builds a mapping table** (`backup_ids_temp`) that tracks `old_id → new_id` for every item type (`course_section`, `course_module`, forum, folder, resource, etc.).
4. **Resolves all cross-references** using this mapping — e.g. `module.xml`'s `<sectionid>` is translated from the old section DB ID to the new one.

The key takeaway: **the IDs in the XML are only meaningful within the MBZ file itself**. As long as they are internally consistent, Moodle does not care what specific values they have.

---

## Where IDs Appear and Must Be Consistent

The following places reference IDs and must all be in sync:

### For a Section (e.g. section ID `6923`)

| File | Where | Value |
|------|-------|-------|
| `sections/section_6923/section.xml` | `<section id="...">` | `6923` |
| `moodle_backup.xml` | `<sectionid>` in `<sections>` block | `6923` |
| `moodle_backup.xml` | `<directory>` in `<sections>` block | `sections/section_6923` |
| `moodle_backup.xml` | `<section>` in `<settings>` block | `section_6923` |
| `moodle_backup.xml` | `<name>` of include/userinfo settings | `section_6923_included`, `section_6923_userinfo` |
| Any `module.xml` inside that section | `<sectionid>` | `6923` |
| `sections/section_6923/` | Folder name | Must match ID |

### For an Activity (e.g. forum module ID `22525`)

| File | Where | Value |
|------|-------|-------|
| `activities/forum_22525/module.xml` | `<module id="...">` | `22525` |
| `activities/forum_22525/forum.xml` | `<forum id="...">` | `22525` |
| `activities/forum_22525/` | Folder name | Must match ID |
| `moodle_backup.xml` | `<moduleid>` in `<activities>` block | `22525` |
| `moodle_backup.xml` | `<directory>` in `<activities>` block | `activities/forum_22525` |
| `moodle_backup.xml` | `<activity>` in `<settings>` block | `forum_22525` |
| `moodle_backup.xml` | `<name>` of include/userinfo settings | `forum_22525_included`, `forum_22525_userinfo` |

### Additional Fields to Note

- **`<number>` in `section.xml`** — the sequential position of the section (0, 1, 2, ...), not the DB ID. Section 0 is always the hidden top-level course section.
- **`<sectionnumber>` in `module.xml`** — must match the `<number>` of the parent section, not the section's ID.
- **Context IDs** (`contextid` in `course.xml`) — also remapped on restore; safe to leave as-is or assign a placeholder.

---

## Rules for Generating New IDs

Because IDs only need to be internally consistent within the MBZ, you can assign any positive integer values as long as:

1. **Each ID is unique within its type** — no two sections share an ID, no two modules share an ID.
2. **Cross-references are consistent** — every place that references a given ID uses the same value.
3. **Folder names match IDs** — e.g. an activity with `<moduleid>99001</moduleid>` must live in `activities/forum_99001/`.
4. **IDs are positive integers** — Moodle stores them as `INT` in its database.

IDs do **not** need to be:
- Globally unique across Moodle installations.
- Sequential or in any particular order.
- Within any specific range.

---

## Recommended ID Generation Strategy for This Repo

To avoid accidental collisions **within a single MBZ file** while keeping things simple:

### Approach: Increment from the Highest Existing ID

1. **Find the current maximum section ID and module ID** in the MBZ you are editing.
2. **Add new IDs sequentially** above that maximum.

**Current known maxima (as of the initial extraction):**

| Course | Max section ID | Max module ID |
|--------|---------------|--------------|
| Real Numbers (571) | `6929` | `22535` |
| Indices and Logarithms (573) | `6943` | `22555` |

So for new content in either course, start from:
- **New section IDs**: `7000+` (safe starting point above both courses)
- **New module IDs**: `23000+` (safe starting point above both courses)

### Checklist for Adding a New Section

- [ ] Choose a new unique section ID (e.g. `7001`)
- [ ] Create `sections/section_7001/` directory
- [ ] Create `sections/section_7001/section.xml` with `<section id="7001">` and the correct `<number>` (next sequential position)
- [ ] Add `<section>` entry to `moodle_backup.xml` `<sections>` block
- [ ] Add `section_7001_included` and `section_7001_userinfo` settings to `moodle_backup.xml` `<settings>` block

### Checklist for Adding a New Activity

- [ ] Choose a new unique module ID (e.g. `23001`)
- [ ] Create `activities/forum_23001/` directory (replace `forum` with the actual module type)
- [ ] Create `activities/forum_23001/module.xml` with `<module id="23001">` and correct `<sectionid>` referencing the parent section
- [ ] Create the activity-specific XML file (e.g. `forum.xml` with `<forum id="23001">`)
- [ ] Create any other required files for that activity type (`grades.xml`, `inforef.xml`, `roles.xml`, etc.)
- [ ] Add `<activity>` entry to `moodle_backup.xml` `<activities>` block with correct `<moduleid>` and `<sectionid>`
- [ ] Add `forum_23001_included` and `forum_23001_userinfo` settings to `moodle_backup.xml` `<settings>` block
- [ ] Add the module ID to the section's `<sequence>` in `sections/section_XXXX/section.xml`

---

## Script Recommendation (Future Work)

Rather than manually tracking the highest ID, a helper script should:

1. Parse `moodle_backup.xml` to find `max(moduleid)` and `max(sectionid)`.
2. Return the next safe IDs for use when scaffolding new sections/activities.
3. Optionally auto-populate the boilerplate XML files with the correct IDs.

This would reduce the risk of ID collisions when multiple sections or activities are added in sequence.

---

## References

- [Moodle Backup API](https://moodledev.io/docs/5.2/apis/subsystems/backup)
- [Moodle Restore API](https://moodledev.io/docs/5.2/apis/subsystems/backup/restore)
- Moodle source: `backup/moodle2/restore_stepslib.php` — `restore_dbops::set_backup_ids_record()` / `get_backup_ids_record()` show how old→new ID mapping is built and applied during restore
- Moodle source: `backup/util/dbops/restore_dbops.class.php` — `create_new_course()` shows that a brand-new course DB record is created before any XML IDs are processed
