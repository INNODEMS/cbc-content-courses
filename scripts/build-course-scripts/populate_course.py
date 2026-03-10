#!/usr/bin/env python3
"""
populate_course.py

Step 2 of the modular build pipeline.

Reads section/activity data from data/new-course-sections-data.json and
populates an existing course in courses-extracted/ with that content.

- Section 0 (the Announcements section) is left untouched.
- Content sections (numbers 1–N) are removed and recreated from the JSON.
- moodle_backup.xml is rebuilt to reflect the final structure.

Usage:
    python scripts/build-course-scripts/populate_course.py
    python scripts/build-course-scripts/populate_course.py <folder-name>
"""

import json
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent.parent
COURSE_DIR = REPO_ROOT / "courses-extracted"
DATA_FILE  = REPO_ROOT / "data" / "new-course-sections-data.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def select_course() -> Path:
    folders = sorted(f for f in COURSE_DIR.iterdir() if f.is_dir())
    if not folders:
        print("No course folders found in courses-extracted/")
        sys.exit(1)
    print("\nAvailable courses:")
    for i, f in enumerate(folders, 1):
        print(f"  {i}. {f.name}")
    print()
    while True:
        raw = input("Enter number to populate: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(folders):
            return folders[int(raw) - 1]
        print(f"  Please enter a number between 1 and {len(folders)}.")


def _parse_section0(course_dir: Path):
    """
    Return (section0_id, forum0_mod_id, forum0_inst_id, forum0_ctxid) for
    section number 0 (the Announcements section).
    """
    backup = ET.parse(course_dir / "moodle_backup.xml").getroot()

    section0_id = None
    for sec in backup.findall(".//sections/section"):
        if sec.findtext("title") == "0":
            section0_id = int(sec.findtext("sectionid"))
            break
    if section0_id is None:
        print("Error: could not find section 0 in moodle_backup.xml")
        sys.exit(1)

    forum0_mod_id = None
    for act in backup.findall(".//activities/activity"):
        if int(act.findtext("sectionid")) == section0_id:
            forum0_mod_id = int(act.findtext("moduleid"))
            break
    if forum0_mod_id is None:
        print("Error: could not find forum in section 0")
        sys.exit(1)

    forum_root    = ET.parse(course_dir / f"activities/forum_{forum0_mod_id}/forum.xml").getroot()
    forum0_inst_id = int(forum_root.get("id"))
    forum0_ctxid   = int(forum_root.get("contextid"))

    return section0_id, forum0_mod_id, forum0_inst_id, forum0_ctxid


# ---------------------------------------------------------------------------
# Stub constants (shared with create_blank_course.py)
# ---------------------------------------------------------------------------

STUB_INFOREF = '<?xml version="1.0" encoding="UTF-8"?>\n<inforef>\n</inforef>'
STUB_CALENDAR = '<?xml version="1.0" encoding="UTF-8"?>\n<events>\n</events>'
STUB_FILTERS = """\
<?xml version="1.0" encoding="UTF-8"?>
<filters>
  <filter_actives>
  </filter_actives>
  <filter_configs>
  </filter_configs>
</filters>"""
STUB_ROLES = """\
<?xml version="1.0" encoding="UTF-8"?>
<roles>
  <role_overrides>
  </role_overrides>
  <role_assignments>
  </role_assignments>
</roles>"""
STUB_GRADE_HIST = """\
<?xml version="1.0" encoding="UTF-8"?>
<grade_history>
  <grade_grades>
  </grade_grades>
</grade_history>"""
STUB_COMPETENCIES_MOD = """\
<?xml version="1.0" encoding="UTF-8"?>
<course_module_competencies>
  <competencies>
  </competencies>
</course_module_competencies>"""
STUB_GRADES = """\
<?xml version="1.0" encoding="UTF-8"?>
<activity_gradebook>
  <grade_items>
  </grade_items>
  <grade_letters>
  </grade_letters>
</activity_gradebook>"""
STUB_GRADING = '<?xml version="1.0" encoding="UTF-8"?>\n<areas>\n</areas>'


# ---------------------------------------------------------------------------
# XML builders
# ---------------------------------------------------------------------------

def _section_xml(section_id, number, name, description, sequence, now):
    summary = description or ""
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<section id="{section_id}">
  <number>{number}</number>
  <name>{name}</name>
  <summary>{summary}</summary>
  <summaryformat>1</summaryformat>
  <sequence>{sequence}</sequence>
  <visible>1</visible>
  <availabilityjson>$@NULL@$</availabilityjson>
  <component>$@NULL@$</component>
  <itemid>$@NULL@$</itemid>
  <timemodified>{now}</timemodified>
</section>"""


def _forum_xml(forum_inst_id, forum_mod_id, forum_ctxid, name, description, now):
    intro = description or ""
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<activity id="{forum_inst_id}" moduleid="{forum_mod_id}" modulename="forum" contextid="{forum_ctxid}">
  <forum id="{forum_inst_id}">
    <type>general</type>
    <name>{name}</name>
    <intro>{intro}</intro>
    <introformat>1</introformat>
    <duedate>0</duedate>
    <cutoffdate>0</cutoffdate>
    <assessed>0</assessed>
    <assesstimestart>0</assesstimestart>
    <assesstimefinish>0</assesstimefinish>
    <scale>0</scale>
    <maxbytes>0</maxbytes>
    <maxattachments>1</maxattachments>
    <forcesubscribe>0</forcesubscribe>
    <trackingtype>1</trackingtype>
    <rsstype>0</rsstype>
    <rssarticles>0</rssarticles>
    <timemodified>{now}</timemodified>
    <warnafter>0</warnafter>
    <blockafter>0</blockafter>
    <blockperiod>0</blockperiod>
    <completiondiscussions>0</completiondiscussions>
    <completionreplies>0</completionreplies>
    <completionposts>0</completionposts>
    <displaywordcount>0</displaywordcount>
    <lockdiscussionafter>0</lockdiscussionafter>
    <grade_forum>0</grade_forum>
    <discussions>
    </discussions>
    <subscriptions>
    </subscriptions>
    <digests>
    </digests>
    <readposts>
    </readposts>
    <trackedprefs>
    </trackedprefs>
    <poststags>
    </poststags>
    <grades>
    </grades>
  </forum>
</activity>"""


def _module_xml(forum_mod_id, section_id, section_number, show_description, now):
    show_desc = 1 if show_description else 0
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<module id="{forum_mod_id}" version="2024100700">
  <modulename>forum</modulename>
  <sectionid>{section_id}</sectionid>
  <sectionnumber>{section_number}</sectionnumber>
  <idnumber>$@NULL@$</idnumber>
  <added>{now}</added>
  <score>0</score>
  <indent>0</indent>
  <visible>1</visible>
  <visibleoncoursepage>1</visibleoncoursepage>
  <visibleold>1</visibleold>
  <groupmode>0</groupmode>
  <groupingid>0</groupingid>
  <completion>0</completion>
  <completiongradeitemnumber>$@NULL@$</completiongradeitemnumber>
  <completionpassgrade>0</completionpassgrade>
  <completionview>0</completionview>
  <completionexpected>0</completionexpected>
  <availability>$@NULL@$</availability>
  <showdescription>{show_desc}</showdescription>
  <downloadcontent>1</downloadcontent>
  <lang>$@NULL@$</lang>
  <tags>
  </tags>
</module>"""


def _moodle_backup_xml(course_dir, folder_name, section0_id, forum0_mod_id,
                        content_sections, now):
    """Rebuild moodle_backup.xml, preserving course-level metadata from the existing file."""
    info = ET.parse(course_dir / "moodle_backup.xml").getroot().find("information")

    mbz_name         = f"{folder_name}.mbz"
    moodle_version   = info.findtext("moodle_version",           "2024100702")
    moodle_release   = info.findtext("moodle_release",           "4.5.2 (Build: 20250210)")
    backup_version   = info.findtext("backup_version",           "2024100700")
    backup_release   = info.findtext("backup_release",           "4.5")
    wwwroot          = info.findtext("original_wwwroot",         "https://ecampus.idems.international")
    site_hash        = info.findtext("original_site_identifier_hash", "")
    course_id        = info.findtext("original_course_id",       "0")
    course_format    = info.findtext("original_course_format",   "topics")
    course_fullname  = info.findtext("original_course_fullname", folder_name)
    course_shortname = info.findtext("original_course_shortname",folder_name)
    course_startdate = info.findtext("original_course_startdate",str(now))
    course_enddate   = info.findtext("original_course_enddate",  "0")
    course_ctxid     = info.findtext("original_course_contextid","1")
    system_ctxid     = info.findtext("original_system_contextid","1")
    backup_id        = info.find(".//detail").get("backup_id", "")

    # --- activities block ---
    activity_lines = [f"""\
        <activity>
          <moduleid>{forum0_mod_id}</moduleid>
          <sectionid>{section0_id}</sectionid>
          <modulename>forum</modulename>
          <title>Announcements</title>
          <directory>activities/forum_{forum0_mod_id}</directory>
          <insubsection></insubsection>
        </activity>"""]
    for sec in content_sections:
        for act in sec["activities"]:
            activity_lines.append(f"""\
        <activity>
          <moduleid>{act["mod_id"]}</moduleid>
          <sectionid>{sec["section_id"]}</sectionid>
          <modulename>forum</modulename>
          <title>{act["title"]}</title>
          <directory>activities/forum_{act["mod_id"]}</directory>
          <insubsection></insubsection>
        </activity>""")

    # --- sections block ---
    section_lines = [f"""\
        <section>
          <sectionid>{section0_id}</sectionid>
          <title>0</title>
          <directory>sections/section_{section0_id}</directory>
          <parentcmid></parentcmid>
          <modname></modname>
        </section>"""]
    for sec in content_sections:
        section_lines.append(f"""\
        <section>
          <sectionid>{sec["section_id"]}</sectionid>
          <title>{sec["number"]}</title>
          <directory>sections/section_{sec["section_id"]}</directory>
          <parentcmid></parentcmid>
          <modname></modname>
        </section>""")

    # --- settings block ---
    settings_lines = [f"""\
      <setting>
        <level>section</level>
        <section>section_{section0_id}</section>
        <name>section_{section0_id}_included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>section</level>
        <section>section_{section0_id}</section>
        <name>section_{section0_id}_userinfo</name>
        <value>0</value>
      </setting>
      <setting>
        <level>activity</level>
        <activity>forum_{forum0_mod_id}</activity>
        <name>forum_{forum0_mod_id}_included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>activity</level>
        <activity>forum_{forum0_mod_id}</activity>
        <name>forum_{forum0_mod_id}_userinfo</name>
        <value>0</value>
      </setting>"""]
    for sec in content_sections:
        sid = sec["section_id"]
        settings_lines.append(f"""\
      <setting>
        <level>section</level>
        <section>section_{sid}</section>
        <name>section_{sid}_included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>section</level>
        <section>section_{sid}</section>
        <name>section_{sid}_userinfo</name>
        <value>0</value>
      </setting>""")
        for act in sec["activities"]:
            mid = act["mod_id"]
            settings_lines.append(f"""\
      <setting>
        <level>activity</level>
        <activity>forum_{mid}</activity>
        <name>forum_{mid}_included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>activity</level>
        <activity>forum_{mid}</activity>
        <name>forum_{mid}_userinfo</name>
        <value>0</value>
      </setting>""")

    nl = "\n"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<moodle_backup>
  <information>
    <name>{mbz_name}</name>
    <moodle_version>{moodle_version}</moodle_version>
    <moodle_release>{moodle_release}</moodle_release>
    <backup_version>{backup_version}</backup_version>
    <backup_release>{backup_release}</backup_release>
    <backup_date>{now}</backup_date>
    <mnet_remoteusers>0</mnet_remoteusers>
    <include_files>1</include_files>
    <include_file_references_to_external_content>0</include_file_references_to_external_content>
    <original_wwwroot>{wwwroot}</original_wwwroot>
    <original_site_identifier_hash>{site_hash}</original_site_identifier_hash>
    <original_course_id>{course_id}</original_course_id>
    <original_course_format>{course_format}</original_course_format>
    <original_course_fullname>{course_fullname}</original_course_fullname>
    <original_course_shortname>{course_shortname}</original_course_shortname>
    <original_course_startdate>{course_startdate}</original_course_startdate>
    <original_course_enddate>{course_enddate}</original_course_enddate>
    <original_course_contextid>{course_ctxid}</original_course_contextid>
    <original_system_contextid>{system_ctxid}</original_system_contextid>
    <details>
      <detail backup_id="{backup_id}">
        <type>course</type>
        <format>moodle2</format>
        <interactive>1</interactive>
        <mode>70</mode>
        <execution>2</execution>
        <executiontime>0</executiontime>
      </detail>
    </details>
    <contents>
      <activities>
{nl.join(activity_lines)}
      </activities>
      <sections>
{nl.join(section_lines)}
      </sections>
      <course>
        <courseid>{course_id}</courseid>
        <title>{course_fullname}</title>
        <directory>course</directory>
      </course>
    </contents>
    <settings>
      <setting>
        <level>root</level>
        <name>filename</name>
        <value>{mbz_name}</value>
      </setting>
      <setting>
        <level>root</level>
        <name>users</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>anonymize</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>role_assignments</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>activities</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>blocks</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>files</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>filters</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>comments</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>badges</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>calendarevents</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>userscompletion</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>logs</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>grade_histories</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>questionbank</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>groups</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>competencies</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>customfield</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>contentbankcontent</name>
        <value>1</value>
      </setting>
      <setting>
        <level>root</level>
        <name>xapistate</name>
        <value>0</value>
      </setting>
      <setting>
        <level>root</level>
        <name>legacyfiles</name>
        <value>1</value>
      </setting>
{nl.join(settings_lines)}
    </settings>
  </information>
</moodle_backup>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def populate_course(course_dir: Path) -> None:
    if not DATA_FILE.exists():
        print(f"Error: data file not found: {DATA_FILE.relative_to(REPO_ROOT)}")
        sys.exit(1)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    sections_data = data["sections"]

    # Read section 0 info before touching anything
    section0_id, forum0_mod_id, forum0_inst_id, forum0_ctxid = _parse_section0(course_dir)

    now = int(time.time())

    # Remove old content sections (keep only section 0)
    sections_dir = course_dir / "sections"
    for s_dir in sorted(sections_dir.iterdir()):
        if s_dir.name != f"section_{section0_id}":
            shutil.rmtree(s_dir)

    # Remove old non-Announcements forums
    activities_dir = course_dir / "activities"
    for a_dir in sorted(activities_dir.iterdir()):
        if a_dir.name != f"forum_{forum0_mod_id}":
            shutil.rmtree(a_dir)

    # Assign IDs and build content section descriptors
    forum_counter = 0
    content_sections = []

    for idx, sec_data in enumerate(sections_data):
        section_number = idx + 1
        section_id = section0_id + section_number

        activities = []
        for act_data in sec_data.get("activities", []):
            if act_data["type"] != "forum":
                continue
            forum_counter += 1
            activities.append({
                "mod_id":          forum0_mod_id  + forum_counter,
                "inst_id":         forum0_inst_id + forum_counter,
                "ctx_id":          forum0_ctxid   + forum_counter,
                "title":           act_data["title"],
                "description":     act_data.get("description", ""),
                "show_description":act_data.get("show_description", False),
            })

        content_sections.append({
            "section_id":  section_id,
            "number":      section_number,
            "title":       sec_data["title"],
            "description": sec_data.get("description", ""),
            "sequence":    ",".join(str(a["mod_id"]) for a in activities),
            "activities":  activities,
        })

    # Write section folders
    for sec in content_sections:
        s_dir = sections_dir / f"section_{sec['section_id']}"
        write(s_dir / "inforef.xml", STUB_INFOREF)
        write(s_dir / "section.xml", _section_xml(
            sec["section_id"], sec["number"],
            sec["title"], sec["description"],
            sec["sequence"], now,
        ))

    # Write forum activity folders
    for sec in content_sections:
        for act in sec["activities"]:
            af = activities_dir / f"forum_{act['mod_id']}"
            write(af / "calendar.xml",      STUB_CALENDAR)
            write(af / "competencies.xml",  STUB_COMPETENCIES_MOD)
            write(af / "filters.xml",       STUB_FILTERS)
            write(af / "grades.xml",        STUB_GRADES)
            write(af / "grade_history.xml", STUB_GRADE_HIST)
            write(af / "grading.xml",       STUB_GRADING)
            write(af / "inforef.xml",       STUB_INFOREF)
            write(af / "roles.xml",         STUB_ROLES)
            write(af / "forum.xml",  _forum_xml(
                act["inst_id"], act["mod_id"], act["ctx_id"],
                act["title"], act["description"], now,
            ))
            write(af / "module.xml", _module_xml(
                act["mod_id"], sec["section_id"], sec["number"],
                act["show_description"], now,
            ))

    # Rebuild moodle_backup.xml (reads old file for metadata, then overwrites)
    write(course_dir / "moodle_backup.xml",
          _moodle_backup_xml(course_dir, course_dir.name,
                              section0_id, forum0_mod_id, content_sections, now))

    print(f"\nPopulated: {course_dir.relative_to(REPO_ROOT)}/")
    for sec in content_sections:
        print(f"  Section {sec['number']}: {sec['title']}")
        for act in sec["activities"]:
            print(f"    forum_{act['mod_id']}: {act['title']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        course_dir = COURSE_DIR / sys.argv[1]
        if not course_dir.is_dir():
            print(f"Course folder not found: {sys.argv[1]}")
            sys.exit(1)
    else:
        course_dir = select_course()
    populate_course(course_dir)
