#!/usr/bin/env python3
"""
create_blank_course.py

Step 1 of the modular build pipeline.

Creates a minimal valid Moodle course backup folder structure in courses-extracted/.
The course has:
  - Section 0 ("New Blank Course") containing the Announcements forum
  - Section 1 ("Blank Section 1") — empty

Usage:
    python scripts/build-course-scripts/create_blank_course.py [folder-name]

If no folder name is given, defaults to "new-blank-course".
An existing folder with the same name is overwritten automatically.
"""

import hashlib
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent.parent
TARGET_DIR = REPO_ROOT / "courses-extracted"

COURSE_TITLE   = "New Blank Course"
COURSE_SHORT   = "new blank course"
SECTION_0_NAME = COURSE_TITLE
SECTION_1_NAME = "Blank Section 1"

# Stable IDs used inside the XML.
# Moodle reassigns all IDs on restore, so any consistent integers are fine.
COURSE_ID       = 0
COURSE_CTXID    = 1
SECTION_0_ID    = 1
SECTION_1_ID    = 2
FORUM_MOD_ID    = 1   # course_modules.id  (folder name: forum_1)
FORUM_INST_ID   = 1   # forum instance id  (mdl_forum.id)
FORUM_CTXID     = 2
ENROL_MANUAL_ID = 1
ENROL_GUEST_ID  = 2
ENROL_SELF_ID   = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _backup_id(now: int) -> str:
    return hashlib.md5(str(now).encode()).hexdigest()


# ---------------------------------------------------------------------------
# XML builders
# ---------------------------------------------------------------------------

def _course_xml(now: int) -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<course id="{COURSE_ID}" contextid="{COURSE_CTXID}">
  <shortname>{COURSE_SHORT}</shortname>
  <fullname>{COURSE_TITLE}</fullname>
  <idnumber></idnumber>
  <summary></summary>
  <summaryformat>0</summaryformat>
  <format>topics</format>
  <showgrades>1</showgrades>
  <newsitems>5</newsitems>
  <startdate>{now}</startdate>
  <enddate>0</enddate>
  <marker>0</marker>
  <maxbytes>0</maxbytes>
  <legacyfiles>0</legacyfiles>
  <showreports>0</showreports>
  <visible>1</visible>
  <groupmode>0</groupmode>
  <groupmodeforce>0</groupmodeforce>
  <defaultgroupingid>0</defaultgroupingid>
  <lang></lang>
  <theme></theme>
  <timecreated>{now}</timecreated>
  <timemodified>{now}</timemodified>
  <requested>0</requested>
  <showactivitydates>1</showactivitydates>
  <showcompletionconditions>1</showcompletionconditions>
  <pdfexportfont>$@NULL@$</pdfexportfont>
  <enablecompletion>1</enablecompletion>
  <completionnotify>0</completionnotify>
  <category id="16">
    <name>Schools</name>
    <description></description>
  </category>
  <tags>
  </tags>
  <customfields>
  </customfields>
  <courseformatoptions>
    <courseformatoption>
      <format>topics</format>
      <sectionid>0</sectionid>
      <name>hiddensections</name>
      <value>0</value>
    </courseformatoption>
    <courseformatoption>
      <format>topics</format>
      <sectionid>0</sectionid>
      <name>coursedisplay</name>
      <value>0</value>
    </courseformatoption>
  </courseformatoptions>
</course>"""


def _section_xml(section_id: int, number: int, name: str, sequence: str,
                 now: int) -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<section id="{section_id}">
  <number>{number}</number>
  <name>{name}</name>
  <summary></summary>
  <summaryformat>1</summaryformat>
  <sequence>{sequence}</sequence>
  <visible>1</visible>
  <availabilityjson>$@NULL@$</availabilityjson>
  <component>$@NULL@$</component>
  <itemid>$@NULL@$</itemid>
  <timemodified>{now}</timemodified>
</section>"""


def _forum_xml(now: int) -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<activity id="{FORUM_INST_ID}" moduleid="{FORUM_MOD_ID}" modulename="forum" contextid="{FORUM_CTXID}">
  <forum id="{FORUM_INST_ID}">
    <type>news</type>
    <name>Announcements</name>
    <intro>General news and announcements</intro>
    <introformat>1</introformat>
    <duedate>0</duedate>
    <cutoffdate>0</cutoffdate>
    <assessed>0</assessed>
    <assesstimestart>0</assesstimestart>
    <assesstimefinish>0</assesstimefinish>
    <scale>0</scale>
    <maxbytes>0</maxbytes>
    <maxattachments>1</maxattachments>
    <forcesubscribe>1</forcesubscribe>
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


def _module_xml(now: int) -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<module id="{FORUM_MOD_ID}" version="2024100700">
  <modulename>forum</modulename>
  <sectionid>{SECTION_0_ID}</sectionid>
  <sectionnumber>0</sectionnumber>
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
  <showdescription>0</showdescription>
  <downloadcontent>1</downloadcontent>
  <lang>$@NULL@$</lang>
  <tags>
  </tags>
</module>"""


def _enrolments_xml(now: int) -> str:
    def enrol_block(enrol_id: int, enrol_type: str, status: int, roleid: int,
                    threshold: int, customint1: str, customint6: str) -> str:
        return f"""\
    <enrol id="{enrol_id}">
      <enrol>{enrol_type}</enrol>
      <status>{status}</status>
      <name>$@NULL@$</name>
      <enrolperiod>0</enrolperiod>
      <enrolstartdate>0</enrolstartdate>
      <enrolenddate>0</enrolenddate>
      <expirynotify>0</expirynotify>
      <expirythreshold>{threshold}</expirythreshold>
      <notifyall>0</notifyall>
      <password>$@NULL@$</password>
      <cost>$@NULL@$</cost>
      <currency>$@NULL@$</currency>
      <roleid>{roleid}</roleid>
      <customint1>{customint1}</customint1>
      <customint2>$@NULL@$</customint2>
      <customint3>$@NULL@$</customint3>
      <customint4>$@NULL@$</customint4>
      <customint5>$@NULL@$</customint5>
      <customint6>{customint6}</customint6>
      <customint7>$@NULL@$</customint7>
      <customint8>$@NULL@$</customint8>
      <customchar1>$@NULL@$</customchar1>
      <customchar2>$@NULL@$</customchar2>
      <customchar3>$@NULL@$</customchar3>
      <customdec1>$@NULL@$</customdec1>
      <customdec2>$@NULL@$</customdec2>
      <customtext1>$@NULL@$</customtext1>
      <customtext2>$@NULL@$</customtext2>
      <customtext3>$@NULL@$</customtext3>
      <customtext4>$@NULL@$</customtext4>
      <timecreated>{now}</timecreated>
      <timemodified>{now}</timemodified>
      <user_enrolments>
      </user_enrolments>
    </enrol>"""

    manual = enrol_block(ENROL_MANUAL_ID, "manual", 0, 5, 86400, "1", "$@NULL@$")
    guest  = enrol_block(ENROL_GUEST_ID,  "guest",  1, 0, 0,     "$@NULL@$", "$@NULL@$")
    # guest has empty password, not $@NULL@$
    guest  = guest.replace("<password>$@NULL@$</password>", "<password></password>")
    self_  = enrol_block(ENROL_SELF_ID,   "self",   1, 5, 86400, "0", "1")

    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<enrolments>
  <enrols>
{manual}
{guest}
{self_}
  </enrols>
</enrolments>"""


def _moodle_backup_xml(folder_name: str, now: int) -> str:
    mbz_name = folder_name if folder_name.endswith(".mbz") else f"{folder_name}.mbz"
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<moodle_backup>
  <information>
    <name>{mbz_name}</name>
    <moodle_version>2024100702</moodle_version>
    <moodle_release>4.5.2 (Build: 20250210)</moodle_release>
    <backup_version>2024100700</backup_version>
    <backup_release>4.5</backup_release>
    <backup_date>{now}</backup_date>
    <mnet_remoteusers>0</mnet_remoteusers>
    <include_files>1</include_files>
    <include_file_references_to_external_content>0</include_file_references_to_external_content>
    <original_wwwroot>https://ecampus.idems.international</original_wwwroot>
    <original_site_identifier_hash>a49c31a10f6515d8a48a2a8422502bba</original_site_identifier_hash>
    <original_course_id>{COURSE_ID}</original_course_id>
    <original_course_format>topics</original_course_format>
    <original_course_fullname>{COURSE_TITLE}</original_course_fullname>
    <original_course_shortname>{COURSE_SHORT}</original_course_shortname>
    <original_course_startdate>{now}</original_course_startdate>
    <original_course_enddate>0</original_course_enddate>
    <original_course_contextid>{COURSE_CTXID}</original_course_contextid>
    <original_system_contextid>1</original_system_contextid>
    <details>
      <detail backup_id="{_backup_id(now)}">
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
        <activity>
          <moduleid>{FORUM_MOD_ID}</moduleid>
          <sectionid>{SECTION_0_ID}</sectionid>
          <modulename>forum</modulename>
          <title>Announcements</title>
          <directory>activities/forum_{FORUM_MOD_ID}</directory>
          <insubsection></insubsection>
        </activity>
      </activities>
      <sections>
        <section>
          <sectionid>{SECTION_0_ID}</sectionid>
          <title>0</title>
          <directory>sections/section_{SECTION_0_ID}</directory>
          <parentcmid></parentcmid>
          <modname></modname>
        </section>
        <section>
          <sectionid>{SECTION_1_ID}</sectionid>
          <title>1</title>
          <directory>sections/section_{SECTION_1_ID}</directory>
          <parentcmid></parentcmid>
          <modname></modname>
        </section>
      </sections>
      <course>
        <courseid>{COURSE_ID}</courseid>
        <title>{COURSE_TITLE}</title>
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
      <setting>
        <level>section</level>
        <section>section_{SECTION_0_ID}</section>
        <name>section_{SECTION_0_ID}_included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>section</level>
        <section>section_{SECTION_0_ID}</section>
        <name>section_{SECTION_0_ID}_userinfo</name>
        <value>0</value>
      </setting>
      <setting>
        <level>activity</level>
        <activity>forum_{FORUM_MOD_ID}</activity>
        <name>forum_{FORUM_MOD_ID}_included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>activity</level>
        <activity>forum_{FORUM_MOD_ID}</activity>
        <name>forum_{FORUM_MOD_ID}_userinfo</name>
        <value>0</value>
      </setting>
      <setting>
        <level>section</level>
        <section>section_{SECTION_1_ID}</section>
        <name>section_{SECTION_1_ID}_included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>section</level>
        <section>section_{SECTION_1_ID}</section>
        <name>section_{SECTION_1_ID}_userinfo</name>
        <value>0</value>
      </setting>
    </settings>
  </information>
</moodle_backup>"""


# ---------------------------------------------------------------------------
# Static stub strings
# ---------------------------------------------------------------------------

STUB_BADGES      = '<?xml version="1.0" encoding="UTF-8"?>\n<badges>\n</badges>'
STUB_COMPLETION  = '<?xml version="1.0" encoding="UTF-8"?>\n<course_completion>\n</course_completion>'
STUB_FILES       = '<?xml version="1.0" encoding="UTF-8"?>\n<files>\n</files>'
STUB_OUTCOMES    = '<?xml version="1.0" encoding="UTF-8"?>\n<outcomes_definition>\n</outcomes_definition>'
STUB_QUESTIONS   = '<?xml version="1.0" encoding="UTF-8"?>\n<question_categories>\n</question_categories>'
STUB_SCALES      = '<?xml version="1.0" encoding="UTF-8"?>\n<scales_definition>\n</scales_definition>'
STUB_INFOREF     = '<?xml version="1.0" encoding="UTF-8"?>\n<inforef>\n</inforef>'
STUB_CALENDAR    = '<?xml version="1.0" encoding="UTF-8"?>\n<events>\n</events>'
STUB_FILTERS     = """\
<?xml version="1.0" encoding="UTF-8"?>
<filters>
  <filter_actives>
  </filter_actives>
  <filter_configs>
  </filter_configs>
</filters>"""
STUB_ROLES       = """\
<?xml version="1.0" encoding="UTF-8"?>
<roles>
  <role_overrides>
  </role_overrides>
  <role_assignments>
  </role_assignments>
</roles>"""
STUB_GRADE_HIST  = """\
<?xml version="1.0" encoding="UTF-8"?>
<grade_history>
  <grade_grades>
  </grade_grades>
</grade_history>"""
STUB_GRADEBOOK   = """\
<?xml version="1.0" encoding="UTF-8"?>
<gradebook>
  <attributes>
  </attributes>
  <grade_categories>
  </grade_categories>
  <grade_items>
  </grade_items>
  <grade_letters>
  </grade_letters>
  <grade_settings>
    <grade_setting id="">
      <name>minmaxtouse</name>
      <value>1</value>
    </grade_setting>
  </grade_settings>
</gradebook>"""
STUB_GROUPS      = """\
<?xml version="1.0" encoding="UTF-8"?>
<groups>
  <groupcustomfields>
  </groupcustomfields>
  <groupings>
    <groupingcustomfields>
    </groupingcustomfields>
  </groupings>
</groups>"""
STUB_ROLES_DEF   = """\
<?xml version="1.0" encoding="UTF-8"?>
<roles_definition>
  <role id="5">
    <name></name>
    <shortname>student</shortname>
    <nameincourse>$@NULL@$</nameincourse>
    <description></description>
    <sortorder>5</sortorder>
    <archetype>student</archetype>
  </role>
</roles_definition>"""
STUB_COURSE_INFOREF = """\
<?xml version="1.0" encoding="UTF-8"?>
<inforef>
  <roleref>
    <role>
      <id>5</id>
    </role>
  </roleref>
</inforef>"""
STUB_COMPETENCIES_COURSE = """\
<?xml version="1.0" encoding="UTF-8"?>
<course_competencies>
  <competencies>
  </competencies>
  <user_competencies>
  </user_competencies>
</course_competencies>"""
STUB_COMPLETION_DEFAULTS = '<?xml version="1.0" encoding="UTF-8"?>\n<course_completion_defaults>\n</course_completion_defaults>'
STUB_CONTENTBANK = '<?xml version="1.0" encoding="UTF-8"?>\n<contents>\n</contents>'
STUB_COMPETENCIES_MOD = """\
<?xml version="1.0" encoding="UTF-8"?>
<course_module_competencies>
  <competencies>
  </competencies>
</course_module_competencies>"""
STUB_GRADES      = """\
<?xml version="1.0" encoding="UTF-8"?>
<activity_gradebook>
  <grade_items>
  </grade_items>
  <grade_letters>
  </grade_letters>
</activity_gradebook>"""
STUB_GRADING     = '<?xml version="1.0" encoding="UTF-8"?>\n<areas>\n</areas>'


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def create_blank_course(folder_name: str) -> None:
    out = TARGET_DIR / folder_name

    if out.exists():
        shutil.rmtree(out)

    now = int(time.time())

    # --- root stubs ---
    write(out / "badges.xml",        STUB_BADGES)
    write(out / "completion.xml",    STUB_COMPLETION)
    write(out / "files.xml",         STUB_FILES)
    write(out / "grade_history.xml", STUB_GRADE_HIST)
    write(out / "gradebook.xml",     STUB_GRADEBOOK)
    write(out / "groups.xml",        STUB_GROUPS)
    write(out / "outcomes.xml",      STUB_OUTCOMES)
    write(out / "questions.xml",     STUB_QUESTIONS)
    write(out / "roles.xml",         STUB_ROLES_DEF)
    write(out / "scales.xml",        STUB_SCALES)

    # --- course/ ---
    write(out / "course" / "calendar.xml",          STUB_CALENDAR)
    write(out / "course" / "competencies.xml",      STUB_COMPETENCIES_COURSE)
    write(out / "course" / "completiondefaults.xml",STUB_COMPLETION_DEFAULTS)
    write(out / "course" / "contentbank.xml",       STUB_CONTENTBANK)
    write(out / "course" / "filters.xml",           STUB_FILTERS)
    write(out / "course" / "inforef.xml",           STUB_COURSE_INFOREF)
    write(out / "course" / "roles.xml",             STUB_ROLES)
    write(out / "course" / "enrolments.xml",        _enrolments_xml(now))
    write(out / "course" / "course.xml",            _course_xml(now))

    # --- section 0 ---
    s0 = out / "sections" / f"section_{SECTION_0_ID}"
    write(s0 / "inforef.xml", STUB_INFOREF)
    write(s0 / "section.xml", _section_xml(SECTION_0_ID, 0, SECTION_0_NAME,
                                            str(FORUM_MOD_ID), now))

    # --- section 1 ---
    s1 = out / "sections" / f"section_{SECTION_1_ID}"
    write(s1 / "inforef.xml", STUB_INFOREF)
    write(s1 / "section.xml", _section_xml(SECTION_1_ID, 1, SECTION_1_NAME,
                                            "", now))

    # --- Announcements forum ---
    af = out / "activities" / f"forum_{FORUM_MOD_ID}"
    write(af / "calendar.xml",    STUB_CALENDAR)
    write(af / "competencies.xml",STUB_COMPETENCIES_MOD)
    write(af / "filters.xml",     STUB_FILTERS)
    write(af / "grades.xml",      STUB_GRADES)
    write(af / "grade_history.xml", STUB_GRADE_HIST)
    write(af / "grading.xml",     STUB_GRADING)
    write(af / "inforef.xml",     STUB_INFOREF)
    write(af / "roles.xml",       STUB_ROLES)
    write(af / "forum.xml",       _forum_xml(now))
    write(af / "module.xml",      _module_xml(now))

    # --- manifest ---
    write(out / "moodle_backup.xml", _moodle_backup_xml(folder_name, now))

    print(f"Created: {out.relative_to(REPO_ROOT)}/")
    print(f"  sections/section_{SECTION_0_ID}/  → {SECTION_0_NAME}")
    print(f"  sections/section_{SECTION_1_ID}/  → {SECTION_1_NAME}")
    print(f"  activities/forum_{FORUM_MOD_ID}/  → Announcements")


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "new-blank-course"
    create_blank_course(folder)
