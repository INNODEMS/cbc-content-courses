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

To avoid accidental collisions **within a single MBZ file**, derive new IDs from the course you are actually editing rather than using fixed arbitrary numbers:

### Approach: Max Existing ID + Offset

For the course you are editing:

1. **Find the current maximum section ID** — scan all `<sectionid>` values in `moodle_backup.xml`.
2. **Find the current maximum module ID** — scan all `<moduleid>` values in `moodle_backup.xml`.
3. **Add a buffer of 1000** to each maximum, then assign new IDs sequentially from there.

The +1000 buffer means that even if a few IDs were missed in the scan, the new IDs remain collision-free. It also makes added content visually distinguishable from original content when inspecting the XML.

**Formula:**

```
new_section_start = max(all <sectionid> in moodle_backup.xml) + 1000
new_module_start  = max(all <moduleid>  in moodle_backup.xml) + 1000
```

**Example — Real Numbers course (course 571):**

| ID type | Max existing | Safe start for new IDs |
|---------|-------------|----------------------|
| Section IDs | `6929` | `7929` (i.e. 6929 + 1000) |
| Module IDs | `22535` | `23535` (i.e. 22535 + 1000) |

**Example — Indices and Logarithms course (course 573):**

| ID type | Max existing | Safe start for new IDs |
|---------|-------------|----------------------|
| Section IDs | `6943` | `7943` (i.e. 6943 + 1000) |
| Module IDs | `22555` | `23555` (i.e. 22555 + 1000) |

Always re-derive from the current `moodle_backup.xml` before starting work in case IDs have changed since these maxima were recorded.

### Checklist for Adding a New Section

- [ ] Determine `new_section_start` = max `<sectionid>` in `moodle_backup.xml` + 1000; assign IDs from there sequentially
- [ ] Create `sections/section_<ID>/` directory
- [ ] Create `sections/section_<ID>/section.xml` with `<section id="<ID>">` and the correct `<number>` (next sequential position)
- [ ] Add `<section>` entry to `moodle_backup.xml` `<sections>` block
- [ ] Add `section_<ID>_included` and `section_<ID>_userinfo` settings to `moodle_backup.xml` `<settings>` block

### Checklist for Adding a New Activity

- [ ] Determine `new_module_start` = max `<moduleid>` in `moodle_backup.xml` + 1000; assign IDs from there sequentially
- [ ] Create `activities/<type>_<ID>/` directory (e.g. `activities/forum_23535/`)
- [ ] Create `activities/<type>_<ID>/module.xml` with `<module id="<ID>">` and correct `<sectionid>` referencing the parent section
- [ ] Create the activity-specific XML file (e.g. `forum.xml` with `<forum id="<ID>">`)
- [ ] Create any other required files for that activity type (`grades.xml`, `inforef.xml`, `roles.xml`, etc.)
- [ ] Add `<activity>` entry to `moodle_backup.xml` `<activities>` block with correct `<moduleid>` and `<sectionid>`
- [ ] Add `<type>_<ID>_included` and `<type>_<ID>_userinfo` settings to `moodle_backup.xml` `<settings>` block
- [ ] Add the module ID to the parent section's `<sequence>` in `sections/section_<sectionID>/section.xml`

---

## Script Recommendation (Future Work)

Rather than manually scanning `moodle_backup.xml`, a helper script should:

1. Parse `moodle_backup.xml` of the target course to find `max(moduleid)` and `max(sectionid)`.
2. Return `max + 1000` as the safe starting ID for new sections and modules.
3. Optionally scaffolding new sections/activities with the correct IDs already filled in.

---

## References

- [Moodle Backup API](https://moodledev.io/docs/5.2/apis/subsystems/backup)
- [Moodle Restore API](https://moodledev.io/docs/5.2/apis/subsystems/backup/restore)
- Moodle source: `backup/moodle2/restore_stepslib.php` — `restore_dbops::set_backup_ids_record()` / `get_backup_ids_record()` show how old→new ID mapping is built and applied during restore
- Moodle source: `backup/util/dbops/restore_dbops.class.php` — `create_new_course()` shows that a brand-new course DB record is created before any XML IDs are processed
