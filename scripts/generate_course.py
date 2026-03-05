#!/usr/bin/env python3
"""
generate_course.py
==================
Generates a complete Moodle MBZ course backup folder from data/courses.json.

Usage:
    python scripts/generate_course.py             # interactive menu
    python scripts/generate_course.py <key>       # key = 1-based index or section_filecase
    python scripts/generate_course.py <key> --compress   # also compress to .mbz

After running, use compress_mbz.py to package the folder, or pass --compress.
"""

import hashlib
import html
import json
import os
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
COURSES_JSON = REPO_ROOT / "data" / "courses.json"
COURSES_OUT = REPO_ROOT / "courses-extracted"
COURSE_LOGOS = REPO_ROOT / "assets" / "course-logos"
TEMPLATE_DIR = (
    REPO_ROOT
    / "courses-extracted"
    / "backup-moodle2-course-571-real_numbers-20260218-1335-nu"
)

# Rotating emojis for lesson sections
LESSON_EMOJIS = [
    "🔢", "🔍", "🧮", "➗", "📊", "📐", "📏", "💡",
    "🎯", "🌟", "⚡", "🔬", "🔭", "📌", "✏️", "🔑",
]

# ─── Placeholder IDs ────────────────────────────────────────────────────────
# Moodle reassigns all IDs on restore, so these are just internal placeholders.
CTX_COURSE = 165404          # keep same as template so cert file refs stay consistent
CTX_CUSTOMCERT_MOD = 166008  # placeholder module context for customcert
SECTION0_ID = 1000           # section 0
CERT_SECTION_ID = 2000       # certificate/completion section
ANN_FORUM_MOD_ID = 3000      # announcements forum module id (also activity id)
CERT_MOD_ID = 4000           # customcert module id (also activity id)

NOW_TS = int(time.time())

# ─── Utilities ───────────────────────────────────────────────────────────────

def he(text: str) -> str:
    """HTML-escape for embedding in XML attributes or CDATA."""
    return html.escape(str(text), quote=False)


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_courses_json():
    with open(COURSES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def select_course(data, key=None):
    courses = data["courses"]
    if key is None:
        print("\nAvailable courses:")
        for i, c in enumerate(courses, 1):
            status = "✓" if c.get("moodle_course_id") else "○"
            print(f"  {i}. [{status}] {c['section']}  ({c['chapter']})")
        key = input("\nEnter number or section_filecase: ").strip()
    # numeric index
    try:
        idx = int(key)
        return courses[idx - 1]
    except (ValueError, IndexError):
        pass
    # section_filecase
    for c in courses:
        if c["section_filecase"] == key:
            return c
    raise SystemExit(f"Course not found: {key!r}")


def lesson_title(lesson: dict, idx: int) -> str:
    """Section display name for a lesson (with emoji)."""
    name = lesson.get("subsubsection") or lesson["subsection"]
    emoji = LESSON_EMOJIS[idx % len(LESSON_EMOJIS)]
    return f"{emoji} {name}"


def lesson_short_name(lesson: dict) -> str:
    """Short name used in discussion forum title."""
    return lesson.get("subsubsection") or lesson["subsection"]


def lo_lookup(course: dict) -> dict:
    """Build {id -> description} from course learning_outcomes."""
    return {lo["id"]: lo["description"] for lo in course.get("learning_outcomes", [])}


# ─── Static XML content ──────────────────────────────────────────────────────

STATIC_XML = {
    "calendar.xml":      '<?xml version="1.0" encoding="UTF-8"?>\n<events>\n</events>',
    "competencies.xml":  '<?xml version="1.0" encoding="UTF-8"?>\n<course_module_competencies>\n  <competencies>\n  </competencies>\n</course_module_competencies>',
    "filters.xml":       '<?xml version="1.0" encoding="UTF-8"?>\n<filters>\n  <filter_actives>\n  </filter_actives>\n  <filter_configs>\n  </filter_configs>\n</filters>',
    "grades.xml":        '<?xml version="1.0" encoding="UTF-8"?>\n<activity_gradebook>\n  <grade_items>\n  </grade_items>\n  <grade_letters>\n  </grade_letters>\n</activity_gradebook>',
    "grade_history.xml": '<?xml version="1.0" encoding="UTF-8"?>\n<grade_history>\n  <grade_grades>\n  </grade_grades>\n</grade_history>',
    "roles.xml":         '<?xml version="1.0" encoding="UTF-8"?>\n<roles>\n  <role_overrides>\n  </role_overrides>\n  <role_assignments>\n  </role_assignments>\n</roles>',
    "inforef.xml":       '<?xml version="1.0" encoding="UTF-8"?>\n<inforef>\n</inforef>',
}

COURSE_INFOREF_XML = """<?xml version="1.0" encoding="UTF-8"?>
<inforef>
  <roleref>
    <role>
      <id>5</id>
    </role>
  </roleref>
</inforef>"""

COURSE_CALENDAR_XML    = STATIC_XML["calendar.xml"]
COURSE_COMPETENCIES_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<course_competencies>\n  <competencies>\n  </competencies>\n  <user_competencies>\n  </user_competencies>\n</course_competencies>'
COURSE_COMPLETIONDEFAULTS_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<course_completion_defaults>\n</course_completion_defaults>'
COURSE_CONTENTBANK_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<contents>\n</contents>'
COURSE_ENROLMENTS_XML  = '<?xml version="1.0" encoding="UTF-8"?>\n<enrolments>\n  <enrols>\n  </enrols>\n</enrolments>'
COURSE_FILTERS_XML     = STATIC_XML["filters.xml"]
COURSE_ROLES_XML       = '<?xml version="1.0" encoding="UTF-8"?>\n<roles>\n  <role_overrides>\n  </role_overrides>\n  <role_assignments>\n  </role_assignments>\n  <role_capabilities>\n  </role_capabilities>\n</roles>'


# ─── XML generators ──────────────────────────────────────────────────────────

def gen_grading_xml(area_id: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<areas>
  <area id="{area_id}">
    <areaname>forum</areaname>
    <activemethod>$@NULL@$</activemethod>
    <definitions>
    </definitions>
  </area>
</areas>"""


def gen_forum_xml(mod_id: int, forum_type: str, name: str, intro: str,
                  is_announcement: bool = False) -> str:
    intro_fmt = "1" if is_announcement else "0"
    scale = "0" if is_announcement else "100"
    maxbytes = "0" if is_announcement else "512000"
    maxattach = "1" if is_announcement else "9"
    force_sub = "1" if is_announcement else "0"
    comp_disc  = "0" if is_announcement else "1"
    comp_repl  = "0" if is_announcement else "2"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<activity id="{mod_id}" moduleid="{mod_id}" modulename="forum" contextid="{mod_id + 10000}">
  <forum id="{mod_id}">
    <type>{forum_type}</type>
    <name>{he(name)}</name>
    <intro>{he(intro)}</intro>
    <introformat>{intro_fmt}</introformat>
    <duedate>0</duedate>
    <cutoffdate>0</cutoffdate>
    <assessed>0</assessed>
    <assesstimestart>0</assesstimestart>
    <assesstimefinish>0</assesstimefinish>
    <scale>{scale}</scale>
    <maxbytes>{maxbytes}</maxbytes>
    <maxattachments>{maxattach}</maxattachments>
    <forcesubscribe>{force_sub}</forcesubscribe>
    <trackingtype>1</trackingtype>
    <rsstype>0</rsstype>
    <rssarticles>0</rssarticles>
    <timemodified>{NOW_TS}</timemodified>
    <warnafter>0</warnafter>
    <blockafter>0</blockafter>
    <blockperiod>0</blockperiod>
    <completiondiscussions>{comp_disc}</completiondiscussions>
    <completionreplies>{comp_repl}</completionreplies>
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


def gen_forum_module_xml(mod_id: int, section_id: int, section_number: int,
                         is_announcement: bool = False, visible_on_page: int = 0) -> str:
    completion = "0" if is_announcement else "2"
    visible_on_page_val = "1" if is_announcement else str(visible_on_page)
    idnumber = "$@NULL@$" if is_announcement else ""
    lang = "$@NULL@$" if is_announcement else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<module id="{mod_id}" version="2024100700">
  <modulename>forum</modulename>
  <sectionid>{section_id}</sectionid>
  <sectionnumber>{section_number}</sectionnumber>
  <idnumber>{idnumber}</idnumber>
  <added>{NOW_TS}</added>
  <score>0</score>
  <indent>0</indent>
  <visible>1</visible>
  <visibleoncoursepage>{visible_on_page_val}</visibleoncoursepage>
  <visibleold>1</visibleold>
  <groupmode>0</groupmode>
  <groupingid>0</groupingid>
  <completion>{completion}</completion>
  <completiongradeitemnumber>$@NULL@$</completiongradeitemnumber>
  <completionpassgrade>0</completionpassgrade>
  <completionview>0</completionview>
  <completionexpected>0</completionexpected>
  <availability>$@NULL@$</availability>
  <showdescription>0</showdescription>
  <downloadcontent>1</downloadcontent>
  <lang>{lang}</lang>
  <tags>
  </tags>
</module>"""


def gen_customcert_module_xml(mod_id: int, cert_section_id: int,
                               cert_section_number: int, lesson_forum_ids: list) -> str:
    """Build customcert module.xml with availability conditions for all lesson forums."""
    conditions = "".join(
        f'{{"type":"completion","cm":{fid},"e":1}},' for fid in lesson_forum_ids
    ).rstrip(",")
    showc = ",".join(["true"] * len(lesson_forum_ids))
    availability = he(
        f'{{"op":"&","c":[{conditions}],"showc":[{showc}]}}'
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<module id="{mod_id}" version="2024042207">
  <modulename>customcert</modulename>
  <sectionid>{cert_section_id}</sectionid>
  <sectionnumber>{cert_section_number}</sectionnumber>
  <idnumber></idnumber>
  <added>{NOW_TS}</added>
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
  <availability>{availability}</availability>
  <showdescription>0</showdescription>
  <downloadcontent>1</downloadcontent>
  <lang></lang>
  <tags>
  </tags>
</module>"""


def gen_course_xml(course: dict, n_lessons: int) -> str:
    section = course["section"]
    chapter = course["chapter"]
    course_id = course.get("moodle_course_id") or 0
    shortname = f"{section} "
    fullname = f"CBE topic delivery: {section}"
    summary = (
        f"This module is designed to equip teachers with tools on how to deliver the topic "
        f'"{chapter} - {section}." In the module, teachers will learn how to effectively design '
        f"and deliver learner-centered tasks that will help learners discover the beautiful "
        f"mathematical concepts covered in this section. Teachers will also keep a journal entry "
        f"of their interaction with learners and give constructive feedback on how to improve "
        f"both the instruction materials and the delivery mechanisms"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<course id="{course_id}" contextid="{CTX_COURSE}">
  <shortname>{he(shortname)}</shortname>
  <fullname>{he(fullname)}</fullname>
  <idnumber></idnumber>
  <summary>{he(summary)}</summary>
  <summaryformat>0</summaryformat>
  <format>flexsections</format>
  <showgrades>1</showgrades>
  <newsitems>5</newsitems>
  <startdate>1769126400</startdate>
  <enddate>1800662400</enddate>
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
  <timecreated>{NOW_TS}</timecreated>
  <timemodified>{NOW_TS}</timemodified>
  <requested>0</requested>
  <showactivitydates>1</showactivitydates>
  <showcompletionconditions>1</showcompletionconditions>
  <pdfexportfont>$@NULL@$</pdfexportfont>
  <enablecompletion>1</enablecompletion>
  <completionnotify>0</completionnotify>
  <category id="1">
    <name>{he(chapter)}</name>
    <description></description>
  </category>
  <tags>
  </tags>
  <customfields>
  </customfields>
  <courseformatoptions>
    <courseformatoption>
      <format>flexsections</format>
      <sectionid>0</sectionid>
      <name>showsection0title</name>
      <value>0</value>
    </courseformatoption>
    <courseformatoption>
      <format>flexsections</format>
      <sectionid>0</sectionid>
      <name>courseindexdisplay</name>
      <value>0</value>
    </courseformatoption>
    <courseformatoption>
      <format>flexsections</format>
      <sectionid>0</sectionid>
      <name>accordion</name>
      <value>1</value>
    </courseformatoption>
    <courseformatoption>
      <format>flexsections</format>
      <sectionid>0</sectionid>
      <name>cmbacklink</name>
      <value>0</value>
    </courseformatoption>
  </courseformatoptions>
</course>"""


def gen_section0_xml(course: dict, facilitators: list, ann_forum_id: int) -> str:
    section        = course["section"]
    chapter        = course["chapter"]
    chapter_number = course["chapter_number"]
    section_number = course["section_number"]
    student_url    = course["student_section_url"]
    chapter_filecase = course["chapter_filecase"]
    section_filecase = course["section_filecase"]
    n_lessons      = len(course["lessons"])
    logo_file      = course.get("course_logo_file")

    # Build facilitator HTML rows
    fac_rows = ""
    for fac in facilitators:
        fac_rows += f"""
      &lt;!-- Facilitator --&gt;
      &lt;div class="cbc-fac-row" style="margin-bottom:2px;"&gt;
        &lt;div&gt;{he(fac["name"])}&lt;/div&gt;
        &lt;div&gt;
          &lt;a href="mailto:{he(fac["email"])}"
             target="_blank"
             rel="noopener"
             style="color:#fff; text-decoration:underline;"&gt;
            {he(fac["email"])}
          &lt;/a&gt;
        &lt;/div&gt;
        &lt;div&gt;{he(fac.get("phone", ""))}&lt;/div&gt;
      &lt;/div&gt;"""

    # Course image block
    if logo_file:
        img_block = f"""    &lt;!-- IMAGE --&gt;
    &lt;div class="cbc-imagewrap"&gt;
      &lt;img
        src="@@PLUGINFILE@@/{logo_file}"
        alt="{he(section)}"
        style="width:100%; max-width:140px; height:auto; border-radius:8px; display:block;"&gt;
    &lt;/div&gt;"""
    else:
        img_block = ""

    # Discussion forum link in section 0 (announcements)
    ann_link = f"$@FORUMVIEWBYID*{ann_forum_id}@$"

    summary = f"""&lt;style&gt;
  .cbc-banner{{
    background:#67A3B3;
    padding:20px;
    color:#fff;
    border-radius:10px;
  }}
  .cbc-banner-grid{{
    display:grid;
    grid-template-columns: 1fr 180px;
    column-gap:32px;
    row-gap:18px;
    align-items:stretch;
  }}
  .cbc-titleintro{{ grid-column:1; grid-row:1; }}
  .cbc-infogrid {{ grid-column:1; grid-row:2; }}
  .cbc-imagewrap{{
    grid-column:2;
    grid-row:1 / span 2;
    display:flex;
    align-items:center;
    justify-content:center;
  }}
  @media (max-width: 700px){{
    .cbc-banner-grid{{
      grid-template-columns: 1fr;
      row-gap:18px;
    }}
    .cbc-titleintro{{ grid-column:1; grid-row:1; }}
    .cbc-imagewrap{{
      grid-column:1;
      grid-row:2;
      justify-content:center;
    }}
    .cbc-infogrid{{ grid-column:1; grid-row:3; }}
  }}
  .cbc-fac-row{{
    display:grid;
    grid-template-columns: 1.2fr 1.2fr 1fr;
    column-gap:24px;
    row-gap:2px;
    align-items:start;
    line-height:1.35;
  }}
  @media (max-width: 700px){{
    .cbc-fac-row{{
      grid-template-columns: 1fr;
      row-gap:4px;
    }}
  }}
&lt;/style&gt;

&lt;!-- ===================== TOP BANNER ===================== --&gt;
&lt;div class="cbc-banner"&gt;
  &lt;div class="cbc-banner-grid"&gt;

    &lt;!-- LEFT / ROW 1 --&gt;
    &lt;div class="cbc-titleintro"&gt;
      &lt;div style="font-size:clamp(32px, 6vw, 48px); line-height:1.1; font-weight:800;"&gt;
        Welcome to the Course
      &lt;/div&gt;

      &lt;p style="font-size:clamp(15px, 2.6vw, 18px); margin-top:16px; margin-bottom:0;"&gt;
        This course provides teaching resources and a platform to exchange with other teachers.
        It is based on this
        &lt;a href="https://innodems.github.io/CBC-Grade-10-Maths/frontmatter.html"
           target="_blank"
           style="color:#FFEFD5; text-decoration:underline;"&gt;
          interactive open teaching and learning resource&lt;/a&gt; which is aligned with the
          Kenyan Grade 10 CBC Maths curriculum.&lt;/p&gt;

        &lt;p style="font-size:clamp(15px, 2.6vw, 18px); margin-top:16px; margin-bottom:0;"&gt;
          A &lt;a href="{student_url}"
           target="_blank"
           style="color:#FFEFD5; text-decoration:underline;"&gt;
           student version&lt;/a&gt; is available to be shared with students who have access to devices.
           Students can practice at their own pace on "Checkpoint" questions that give instant feedback.
      &lt;/p&gt;

        &lt;p style="font-size:clamp(12px, 2.6vw, 15px); margin-top:16px; margin-bottom:0;"&gt;
       These materials are co-developed by INNODEMS, IDEMS, and The Kenya Mathematical Society (KMS).
        &lt;/p&gt;
    &lt;/div&gt;

{img_block}

    &lt;!-- LEFT / ROW 2 --&gt;
    &lt;div class="cbc-infogrid" style="font-size:clamp(15px, 2.6vw, 18px);"&gt;

      &lt;!-- Duration --&gt;
      &lt;div&gt;
        &lt;div style="font-weight:700;"&gt;Duration&lt;/div&gt;
        &lt;div&gt;{n_lessons} hours&lt;/div&gt;
      &lt;/div&gt;

      &lt;div style="height:14px;"&gt;&lt;/div&gt;

      &lt;!-- Facilitators label --&gt;
      &lt;div style="font-weight:700; margin-bottom:4px;"&gt;
        Facilitators
      &lt;/div&gt;
{fac_rows}
    &lt;/div&gt;

  &lt;/div&gt;
&lt;/div&gt;

&lt;!-- ===================== LOGO STRIP ===================== --&gt;
&lt;div style="
  background:white;
  padding:22px 16px 10px 16px;
  display:flex;
  justify-content:center;
  align-items:center;
  gap:28px;
  flex-wrap:wrap;
"&gt;
  &lt;img src="@@PLUGINFILE@@/innodems.png"
       alt="INNODEMS"
       style="height:36px;"&gt;

  &lt;img src="@@PLUGINFILE@@/kms.png"
       alt="Kenya Mathematical Society"
       style="height:112px; position:relative; top:6px;"&gt;

  &lt;img src="@@PLUGINFILE@@/idems.png"
       alt="IDEMS International"
       style="height:36px;"&gt;
&lt;/div&gt;

&lt;!-- CAPTION --&gt;
&lt;div style="
  background:white;
  text-align:center;
  color:#777;
  font-size:14px;
  padding:0 16px 25px 16px;
  line-height:1.4;
"&gt;
  Delivered jointly by INNODEMS, the Kenya Mathematical Society (KMS), and IDEMS International
&lt;/div&gt;

&lt;!-- ===================== WHITE SECTION ===================== --&gt;
&lt;div style="background:white; color:#444; padding:20px; font-size:18px; line-height:1.6;"&gt;

  &lt;p&gt;This course is intended to provide teachers with resources to help teaching CBE-aligned Grade 10 mathematics, and create a forum for teachers to share resources and experiences on the delivery of the Kenyan grade 10 math.&lt;/p&gt;

  &lt;p&gt;
    We also have a more general course on &lt;a href="$@COURSEVIEWBYID*564@$"&gt;Competency Based Education Math delivery&lt;/a&gt;. We suggest taking this course first if this is your first time teaching using CBE Maths.
  &lt;/p&gt;

  &lt;p&gt;Enhance your CBE grade 10 teaching with ease: Spend less time on preparation and more time supporting your learners!&lt;/p&gt;

  &lt;p&gt;This particular course is for Chapter {chapter_number}, Section {section_number}: {he(section)} ({n_lessons} lessons).&lt;/p&gt;

  &lt;h3 style="margin-top:30px; font-size:22px; color:#67A3B3;"&gt;&lt;strong&gt;What you will gain&lt;/strong&gt;&lt;/h3&gt;

  &lt;ul style="margin-left:20px;"&gt;
    &lt;li&gt;Access to ready-to-use example lesson plans aligned with CBE&lt;/li&gt;
    &lt;li&gt;Access to ready-to-use step-by-step lesson guides aligned with CBE&lt;/li&gt;
    &lt;li&gt;Opportunities to exchange your teaching experience with other teachers&lt;/li&gt;
  &lt;/ul&gt;

  &lt;h3 style="margin-top:30px; font-size:22px; color:#67A3B3;"&gt;&lt;strong&gt;Certification&lt;/strong&gt;&lt;/h3&gt;

  &lt;p&gt;There will be a certificate at the end of this course. In order to get accreditation for this course you should participate in all forum discussions by:&lt;/p&gt;

  &lt;ul style="margin-left:20px;"&gt;
    &lt;li&gt;Starting a discussion in each topic outlining your experience, &lt;em&gt;and&lt;/em&gt;&lt;/li&gt;
    &lt;li&gt;Responding to at least two forum posts by your colleagues in each topic.&lt;/li&gt;
  &lt;/ul&gt;

&lt;/div&gt;"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<section id="{SECTION0_ID}">
  <number>0</number>
  <name></name>
  <summary>{summary}</summary>
  <summaryformat>1</summaryformat>
  <sequence>{ann_forum_id}</sequence>
  <visible>1</visible>
  <availabilityjson>{{"op":"&amp;","c":[],"showc":[]}}</availabilityjson>
  <component>$@NULL@$</component>
  <itemid>$@NULL@$</itemid>
  <timemodified>{NOW_TS}</timemodified>
  <course_format_options id="1">
    <format>flexsections</format>
    <name>collapsed</name>
    <value>0</value>
  </course_format_options>
  <course_format_options id="2">
    <format>flexsections</format>
    <name>parent</name>
    <value>0</value>
  </course_format_options>
  <course_format_options id="3">
    <format>flexsections</format>
    <name>visibleold</name>
    <value>1</value>
  </course_format_options>
</section>"""


def gen_lesson_section_xml(lesson: dict, idx: int, lo_map: dict,
                           lesson_plan_base: str) -> str:
    section_id  = lesson["moodle_section_id"]
    forum_id    = lesson["forum_id"]
    title       = lesson_title(lesson, idx)
    short_name  = lesson_short_name(lesson)
    section_num = idx + 1  # 1-based

    # Build LO bullet points
    lo_items = ""
    for lo_id in lesson.get("learning_outcome_ids", []):
        desc = lo_map.get(lo_id, lo_id)
        lo_items += f"\n        &lt;li&gt;{he(desc)}&lt;/li&gt;"

    # Build Quick Access links
    lp_path = lesson.get("lesson_plan_path", "")
    sp_path = lesson.get("step_by_step_path", "")
    lp_exists = lesson.get("lesson_plan_exists", False)
    sp_exists  = lesson.get("step_by_step_exists", False)

    lp_href = (lesson_plan_base + lp_path) if lp_exists and lp_path else "#"
    sp_href = (lesson_plan_base + sp_path) if sp_exists and sp_path else "#"

    lp_disabled = "" if lp_exists else ' opacity:0.4; cursor:not-allowed;'
    sp_disabled = "" if sp_exists else ' opacity:0.4; cursor:not-allowed;'

    summary = f"""&lt;!-- ===============  SECTION CONTAINER  =============== --&gt;
&lt;div style="background:#f7fbfc; border:1px solid #d9e7ec; border-radius:16px; overflow:hidden; margin:10px 0;"&gt;

  &lt;!-- ===============  HEADER BANNER  =============== --&gt;
  &lt;div style="background:#67A3B3; color:white; padding:20px;"&gt;
    &lt;div style="font-size:24px; font-weight:800; line-height:1.2;"&gt;
      {he(title)}
    &lt;/div&gt;
    &lt;div style="font-size:14px; opacity:0.95; margin-top:6px;"&gt;
      A practical, discovery-based Grade 10 lesson.
    &lt;/div&gt;
  &lt;/div&gt;

  &lt;!-- ===============  MAIN CONTENT AREA  =============== --&gt;
  &lt;div style="padding:20px; color:#2f3a3d; font-size:15px; line-height:1.5;"&gt;

    &lt;!-- QUICK LINKS --&gt;
    &lt;div style="margin-bottom:18px;"&gt;
      &lt;div style="font-weight:700; margin-bottom:8px; color:#0b5565;"&gt;
        Quick Access
      &lt;/div&gt;

      &lt;div style="background:white; border:1px solid #e3eef2; border-radius:12px; padding:14px;"&gt;
        &lt;div style="display:flex; flex-wrap:wrap; gap:10px;"&gt;
          &lt;a href="{lp_href}"
             target="_blank" rel="noopener"
             style="padding:10px 12px; border-radius:10px; background:#f7fbfc; border:1px solid #d9e7ec; text-decoration:none; color:#0b5565; font-weight:700;{lp_disabled}"&gt;
            &#xD83D;&#xDCC4; Lesson Plan
          &lt;/a&gt;

          &lt;a href="{sp_href}"
             target="_blank" rel="noopener"
             style="padding:10px 12px; border-radius:10px; background:#f7fbfc; border:1px solid #d9e7ec; text-decoration:none; color:#0b5565; font-weight:700;{sp_disabled}"&gt;
            &#xD83E;&#xDDD1;&#x200D;&#xD83C;&#xDFEB; Step-by-step guide
          &lt;/a&gt;
        &lt;/div&gt;
      &lt;/div&gt;
    &lt;/div&gt;

    &lt;!-- IN THIS SECTION --&gt;
    &lt;div style="background:white; border:1px solid #e3eef2; border-radius:12px; padding:14px; margin-bottom:14px;"&gt;
      &lt;div style="font-weight:800; margin-bottom:8px; color:#0b5565;"&gt;
        The lesson plan and step by step guide supports you to guide learners to:
      &lt;/div&gt;
      &lt;ul style="margin:0; padding-left:18px;"&gt;{lo_items}
      &lt;/ul&gt;
    &lt;/div&gt;

    &lt;!-- ===============  DISCUSSION BOX  =============== --&gt;
    &lt;div style="background:#fff6e8; border:1px solid #ffe1b5; border-radius:14px; padding:16px; margin-bottom:20px;"&gt;

      &lt;div style="font-weight:900; color:#7a4b00; margin-bottom:8px;"&gt;
        &#xD83D;&#xDCAC; Discussion Forum: Share one classroom strategy or real-life example here
      &lt;/div&gt;

      &lt;p style="margin:0 0 12px 0;"&gt;
        Post at least once and respond to at least two colleagues.
      &lt;/p&gt;

      &lt;a href="$@FORUMVIEWBYID*{forum_id}@$"
         target="_blank" rel="noopener"
         style="display:inline-flex; align-items:center; gap:6px; padding:10px 12px; border-radius:10px; background:white; border:1px solid #ffe1b5; text-decoration:none; color:#7a4b00; font-weight:800;"&gt;
        &#xD83D;&#xDCAC; Open discussion forum
      &lt;/a&gt;

    &lt;/div&gt;

  &lt;/div&gt;
&lt;/div&gt;"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<section id="{section_id}">
  <number>{section_num}</number>
  <name>{he(title)}</name>
  <summary>{summary}</summary>
  <summaryformat>1</summaryformat>
  <sequence>{forum_id}</sequence>
  <visible>1</visible>
  <availabilityjson>{{"op":"&amp;","c":[],"showc":[]}}</availabilityjson>
  <component>$@NULL@$</component>
  <itemid>$@NULL@$</itemid>
  <timemodified>{NOW_TS}</timemodified>
  <course_format_options id="{section_id + 100}">
    <format>flexsections</format>
    <name>collapsed</name>
    <value>0</value>
  </course_format_options>
  <course_format_options id="{section_id + 101}">
    <format>flexsections</format>
    <name>parent</name>
    <value>0</value>
  </course_format_options>
  <course_format_options id="{section_id + 102}">
    <format>flexsections</format>
    <name>visibleold</name>
    <value>1</value>
  </course_format_options>
</section>"""


def gen_cert_section_xml(cert_section_id: int, cert_section_number: int,
                          cert_mod_id: int) -> str:
    summary = """&lt;!-- ===============  CERTIFICATION CONTAINER  =============== --&gt;
&lt;div style="background:#f7fbfc; border:1px solid #d9e7ec; border-radius:16px; padding:20px; margin:10px 0; color:#2f3a3d; font-size:15px; line-height:1.5;"&gt;

  &lt;div style="font-size:20px; font-weight:800; color:#0b5565; margin-bottom:10px;"&gt;
    &#xD83C;&#xDF93; Course Completion &amp;amp; Certification
  &lt;/div&gt;

  &lt;p style="margin:0 0 14px 0;"&gt;
    A certificate of completion is awarded at the end of this course to participants who have actively engaged with all learning activities.
  &lt;/p&gt;

  &lt;div style="background:white; border:1px solid #e3eef2; border-radius:12px; padding:14px; margin-bottom:14px;"&gt;
    &lt;div style="font-weight:800; margin-bottom:8px; color:#0b5565;"&gt;
      To qualify for certification, you must:
    &lt;/div&gt;
    &lt;ul style="margin:0; padding-left:18px;"&gt;
      &lt;li&gt;Start at least &lt;strong&gt;one discussion&lt;/strong&gt; in &lt;strong&gt;each topic&lt;/strong&gt;, sharing your classroom experience or reflections.&lt;/li&gt;
      &lt;li&gt;Respond to at least &lt;strong&gt;two forum posts&lt;/strong&gt; by your colleagues in &lt;strong&gt;each topic&lt;/strong&gt;.&lt;/li&gt;
    &lt;/ul&gt;
  &lt;/div&gt;

  &lt;p style="margin:0;"&gt;
    These discussions are designed to support reflection, peer learning, and the sharing of effective classroom practices.
  &lt;/p&gt;

&lt;/div&gt;"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<section id="{cert_section_id}">
  <number>{cert_section_number}</number>
  <name>&#xD83C;&#xDFC5; Completion Certificate</name>
  <summary>{summary}</summary>
  <summaryformat>1</summaryformat>
  <sequence>{cert_mod_id}</sequence>
  <visible>1</visible>
  <availabilityjson>{{"op":"&amp;","c":[],"showc":[]}}</availabilityjson>
  <component>$@NULL@$</component>
  <itemid>$@NULL@$</itemid>
  <timemodified>{NOW_TS}</timemodified>
  <course_format_options id="{cert_section_id + 100}">
    <format>flexsections</format>
    <name>collapsed</name>
    <value>0</value>
  </course_format_options>
  <course_format_options id="{cert_section_id + 101}">
    <format>flexsections</format>
    <name>parent</name>
    <value>0</value>
  </course_format_options>
  <course_format_options id="{cert_section_id + 102}">
    <format>flexsections</format>
    <name>visibleold</name>
    <value>1</value>
  </course_format_options>
</section>"""


def gen_moodle_backup_xml(course: dict, lessons: list, section_entries: list,
                           activity_entries: list, folder_name: str) -> str:
    """
    section_entries: list of dicts with keys: sectionid, title, directory
    activity_entries: list of dicts with keys: moduleid, sectionid, modulename, title, directory
    """
    course_id = course.get("moodle_course_id") or 0
    section = course["section"]

    acts_xml = ""
    for a in activity_entries:
        acts_xml += f"""        <activity>
          <moduleid>{a["moduleid"]}</moduleid>
          <sectionid>{a["sectionid"]}</sectionid>
          <modulename>{a["modulename"]}</modulename>
          <title>{he(a["title"])}</title>
          <directory>{a["directory"]}</directory>
          <insubsection></insubsection>
        </activity>\n"""

    sects_xml = ""
    for s in section_entries:
        sects_xml += f"""        <section>
          <sectionid>{s["sectionid"]}</sectionid>
          <title>{he(s["title"])}</title>
          <directory>{s["directory"]}</directory>
          <parentcmid></parentcmid>
          <modname></modname>
        </section>\n"""

    # Build per-activity settings
    act_settings = ""
    for a in activity_entries:
        mname = a["modulename"]
        mid   = a["moduleid"]
        act_settings += f"""      <setting>
        <level>activity</level>
        <activity>{mname}_{mid}</activity>
        <name>included</name>
        <value>1</value>
      </setting>
      <setting>
        <level>activity</level>
        <activity>{mname}_{mid}</activity>
        <name>userinfo</name>
        <value>0</value>
      </setting>\n"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<moodle_backup>
  <information>
    <name>{folder_name}.mbz</name>
    <moodle_version>2024100702</moodle_version>
    <moodle_release>4.5.2 (Build: 20250210)</moodle_release>
    <backup_version>2024100700</backup_version>
    <backup_release>4.5</backup_release>
    <backup_date>{NOW_TS}</backup_date>
    <mnet_remoteusers>0</mnet_remoteusers>
    <include_files>1</include_files>
    <include_file_references_to_external_content>0</include_file_references_to_external_content>
    <original_wwwroot>https://ecampus.idems.international</original_wwwroot>
    <original_site_identifier_hash>a49c31a10f6515d8a48a2a8422502bba</original_site_identifier_hash>
    <original_course_id>{course_id}</original_course_id>
    <original_course_format>flexsections</original_course_format>
    <original_course_fullname>CBE topic delivery: {he(section)}</original_course_fullname>
    <original_course_shortname>{he(section)} </original_course_shortname>
    <original_course_startdate>1769126400</original_course_startdate>
    <original_course_enddate>1800662400</original_course_enddate>
    <original_course_contextid>{CTX_COURSE}</original_course_contextid>
    <original_system_contextid>1</original_system_contextid>
    <details>
      <detail backup_id="generated">
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
{acts_xml}      </activities>
      <sections>
{sects_xml}      </sections>
      <course>
        <courseid>{course_id}</courseid>
        <title>{he(section)} </title>
        <directory>course</directory>
      </course>
    </contents>
    <settings>
      <setting>
        <level>root</level>
        <name>filename</name>
        <value>{folder_name}.mbz</value>
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
{act_settings}    </settings>
  </information>
</moodle_backup>"""


# ─── files.xml helpers ───────────────────────────────────────────────────────

EMPTY_DIR_HASH = "da39a3ee5e6b4b0d3255bfef95601890afd80709"  # sha1 of empty bytes


def read_customcert_file_entries(template_files_xml: Path) -> list:
    """
    Parse the template files.xml and return all <file> elements where
    component is 'mod_customcert'. Returns list of raw XML strings.
    """
    tree = ET.parse(template_files_xml)
    root = tree.getroot()
    entries = []
    for f_el in root.findall("file"):
        comp = f_el.findtext("component", "")
        if comp == "mod_customcert":
            entries.append(ET.tostring(f_el, encoding="unicode"))
    return entries


def gen_files_xml(cert_file_entries: list, logo_info: dict | None,
                   section0_logo_files: list) -> str:
    """
    cert_file_entries: list of XML strings for mod_customcert files
    logo_info: dict with keys: filename, contenthash, filesize, mimetype, itemid
               or None if no logo
    section0_logo_files: list of logo dicts for innodems/kms/idems logos stored in section
    Returns full files.xml content.
    """
    file_id = 50000
    all_entries = []

    # Cert images
    for entry_xml in cert_file_entries:
        # re-indent only - keep original content
        all_entries.append(f"  {entry_xml.strip()}")

    # Section 0: empty dir sentinel
    file_id += 1
    all_entries.append(f"""  <file id="{file_id}">
    <contenthash>{EMPTY_DIR_HASH}</contenthash>
    <contextid>{CTX_COURSE}</contextid>
    <component>course</component>
    <filearea>section</filearea>
    <itemid>{SECTION0_ID}</itemid>
    <filepath>/</filepath>
    <filename>.</filename>
    <userid>$@NULL@$</userid>
    <filesize>0</filesize>
    <mimetype>$@NULL@$</mimetype>
    <status>0</status>
    <timecreated>{NOW_TS}</timecreated>
    <timemodified>{NOW_TS}</timemodified>
    <source>$@NULL@$</source>
    <author>$@NULL@$</author>
    <license>$@NULL@$</license>
    <sortorder>0</sortorder>
    <repositorytype>$@NULL@$</repositorytype>
    <repositoryid>$@NULL@$</repositoryid>
    <reference>$@NULL@$</reference>
  </file>""")

    # Institutional logos in section 0
    for logo in section0_logo_files:
        file_id += 1
        all_entries.append(f"""  <file id="{file_id}">
    <contenthash>{logo["contenthash"]}</contenthash>
    <contextid>{CTX_COURSE}</contextid>
    <component>course</component>
    <filearea>section</filearea>
    <itemid>{SECTION0_ID}</itemid>
    <filepath>/</filepath>
    <filename>{he(logo["filename"])}</filename>
    <userid>$@NULL@$</userid>
    <filesize>{logo["filesize"]}</filesize>
    <mimetype>{logo["mimetype"]}</mimetype>
    <status>0</status>
    <timecreated>{NOW_TS}</timecreated>
    <timemodified>{NOW_TS}</timemodified>
    <source>{he(logo["filename"])}</source>
    <author>$@NULL@$</author>
    <license>allrightsreserved</license>
    <sortorder>0</sortorder>
    <repositorytype>$@NULL@$</repositorytype>
    <repositoryid>$@NULL@$</repositoryid>
    <reference>$@NULL@$</reference>
  </file>""")

    # Course logo (if present)
    if logo_info:
        file_id += 1
        all_entries.append(f"""  <file id="{file_id}">
    <contenthash>{logo_info["contenthash"]}</contenthash>
    <contextid>{CTX_COURSE}</contextid>
    <component>course</component>
    <filearea>section</filearea>
    <itemid>{SECTION0_ID}</itemid>
    <filepath>/</filepath>
    <filename>{he(logo_info["filename"])}</filename>
    <userid>$@NULL@$</userid>
    <filesize>{logo_info["filesize"]}</filesize>
    <mimetype>{logo_info["mimetype"]}</mimetype>
    <status>0</status>
    <timecreated>{NOW_TS}</timecreated>
    <timemodified>{NOW_TS}</timemodified>
    <source>{he(logo_info["filename"])}</source>
    <author>$@NULL@$</author>
    <license>allrightsreserved</license>
    <sortorder>0</sortorder>
    <repositorytype>$@NULL@$</repositorytype>
    <repositoryid>$@NULL@$</repositoryid>
    <reference>$@NULL@$</reference>
  </file>""")

    body = "\n".join(all_entries)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<files>\n{body}\n</files>'


# ─── Main generation ─────────────────────────────────────────────────────────

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  + {path.relative_to(REPO_ROOT)}")


def write_static_files_for_forum(activity_dir: Path, mod_id: int):
    """Write static boilerplate XML files into a forum activity directory."""
    for name, content in STATIC_XML.items():
        if name == "inforef.xml":
            continue  # already handled (empty for forums)
        write_file(activity_dir / name, content)
    write_file(activity_dir / "inforef.xml", STATIC_XML["inforef.xml"])
    write_file(activity_dir / "grading.xml", gen_grading_xml(mod_id))


def write_static_files_for_customcert(activity_dir: Path):
    """Write static boilerplate XML files into a customcert activity directory."""
    for name, content in {
        "calendar.xml": STATIC_XML["calendar.xml"],
        "competencies.xml": STATIC_XML["competencies.xml"],
        "filters.xml": STATIC_XML["filters.xml"],
        "grades.xml": STATIC_XML["grades.xml"],
        "grade_history.xml": STATIC_XML["grade_history.xml"],
        "roles.xml": STATIC_XML["roles.xml"],
    }.items():
        write_file(activity_dir / name, content)


def copy_cert_image_to_files(src_hash_path: Path, out_files_dir: Path):
    """Copy a certificate image (identified by SHA1 hash) into out_files_dir/<xx>/<hash>."""
    dest_dir  = out_files_dir / src_hash_path.parent.name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / src_hash_path.name
    if not dest_file.exists():
        shutil.copy2(src_hash_path, dest_file)


EXTENSION_TO_MIME = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
    ".svg":  "image/svg+xml",
}


def get_institutional_logos():
    """
    Return list of dicts for innodems.png, kms.png, idems.png from assets/logos/.
    Each dict: filename, contenthash, filesize, mimetype, filepath.
    """
    logos_dir = REPO_ROOT / "assets" / "logos"
    logos = []
    for fname in ["innodems.png", "kms.png", "idems.png"]:
        fpath = logos_dir / fname
        if fpath.exists():
            h = sha1_of_file(fpath)
            ext = fpath.suffix.lower()
            logos.append({
                "filename": fname,
                "contenthash": h,
                "filesize": fpath.stat().st_size,
                "mimetype": EXTENSION_TO_MIME.get(ext, "application/octet-stream"),
                "filepath": fpath,
            })
        else:
            print(f"  WARNING: institutional logo not found: {fpath}")
    return logos


def generate_course(course: dict, data: dict):
    """Generate the full course folder."""
    lessons       = course["lessons"]
    n_lessons     = len(lessons)
    facilitators  = data["facilitators"]
    lp_base_url   = data["lesson_plan_base_url"]
    course_id     = course.get("moodle_course_id") or 0
    section_fc    = course["section_filecase"]
    folder_name   = course.get("moodle_course_folder") or f"backup-moodle2-course-{course_id}-{section_fc}"

    out_dir = COURSES_OUT / folder_name
    if out_dir.exists():
        answer = input(f"\n  Output folder already exists:\n  {out_dir}\n  Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return
        shutil.rmtree(out_dir)

    print(f"\nGenerating: {folder_name}")
    out_dir.mkdir(parents=True)

    lo_map = lo_lookup(course)
    lesson_forum_ids = [l["forum_id"] for l in lessons]
    cert_section_num = n_lessons + 1  # section number for certificate

    # ── 1. Root-level static XML files ─────────────────────────────────────
    print("\n[Root static files]")
    for fname in ["badges.xml", "completion.xml", "grade_history.xml",
                  "gradebook.xml", "groups.xml", "outcomes.xml",
                  "questions.xml", "roles.xml", "scales.xml"]:
        src = TEMPLATE_DIR / fname
        if src.exists():
            shutil.copy2(src, out_dir / fname)
            print(f"  + {fname}")
        else:
            print(f"  WARNING: template file not found: {fname}")

    # ── 2. course/ directory ─────────────────────────────────────────────────
    print("\n[course/]")
    course_dir = out_dir / "course"
    course_dir.mkdir()
    write_file(course_dir / "course.xml",            gen_course_xml(course, n_lessons))
    write_file(course_dir / "inforef.xml",           COURSE_INFOREF_XML)
    write_file(course_dir / "calendar.xml",          COURSE_CALENDAR_XML)
    write_file(course_dir / "competencies.xml",      COURSE_COMPETENCIES_XML)
    write_file(course_dir / "completiondefaults.xml",COURSE_COMPLETIONDEFAULTS_XML)
    write_file(course_dir / "contentbank.xml",       COURSE_CONTENTBANK_XML)
    write_file(course_dir / "enrolments.xml",        COURSE_ENROLMENTS_XML)
    write_file(course_dir / "filters.xml",           COURSE_FILTERS_XML)
    write_file(course_dir / "roles.xml",             COURSE_ROLES_XML)

    # ── 3. Announcements forum ───────────────────────────────────────────────
    print("\n[activities/]")
    ann_dir = out_dir / "activities" / f"forum_{ANN_FORUM_MOD_ID}"
    ann_dir.mkdir(parents=True)
    write_file(ann_dir / "forum.xml",
               gen_forum_xml(ANN_FORUM_MOD_ID, "news", "Announcements",
                             "General news and announcements", is_announcement=True))
    write_file(ann_dir / "module.xml",
               gen_forum_module_xml(ANN_FORUM_MOD_ID, SECTION0_ID, 0,
                                    is_announcement=True, visible_on_page=1))
    write_static_files_for_forum(ann_dir, ANN_FORUM_MOD_ID)

    # ── 4. Lesson forums ─────────────────────────────────────────────────────
    for i, lesson in enumerate(lessons):
        fid   = lesson["forum_id"]
        sid   = lesson["moodle_section_id"]
        name  = f"Discussion: {lesson_short_name(lesson)}"
        intro = f'Discuss your experience teaching "{lesson_short_name(lesson)}" here'
        f_dir = out_dir / "activities" / f"forum_{fid}"
        f_dir.mkdir(parents=True)
        write_file(f_dir / "forum.xml",
                   gen_forum_xml(fid, "general", name, intro))
        write_file(f_dir / "module.xml",
                   gen_forum_module_xml(fid, sid, i + 1))
        write_static_files_for_forum(f_dir, fid)

    # ── 5. Customcert activity ───────────────────────────────────────────────
    cert_dir = out_dir / "activities" / f"customcert_{CERT_MOD_ID}"
    cert_dir.mkdir(parents=True)

    # Read template customcert.xml and substitute IDs
    template_cert_xml = (TEMPLATE_DIR / "activities" / "customcert_22514" / "customcert.xml").read_text(encoding="utf-8")
    # Replace old IDs with new placeholders
    new_cert_xml = template_cert_xml
    new_cert_xml = new_cert_xml.replace(' id="13"', f' id="{CERT_MOD_ID}"')
    new_cert_xml = new_cert_xml.replace(f'moduleid="22514"', f'moduleid="{CERT_MOD_ID}"')
    new_cert_xml = new_cert_xml.replace(f'contextid="166008"', f'contextid="{CTX_CUSTOMCERT_MOD}"')
    # Keep internal "165404" contextid refs - they are course context refs that Moodle remaps
    write_file(cert_dir / "customcert.xml", new_cert_xml)

    # Copy template inforef.xml for cert (references cert image file IDs)
    template_cert_inforef = TEMPLATE_DIR / "activities" / "customcert_22514" / "inforef.xml"
    if template_cert_inforef.exists():
        shutil.copy2(template_cert_inforef, cert_dir / "inforef.xml")
        print(f"  + activities/customcert_{CERT_MOD_ID}/inforef.xml")
    else:
        write_file(cert_dir / "inforef.xml", STATIC_XML["inforef.xml"])

    write_file(cert_dir / "module.xml",
               gen_customcert_module_xml(CERT_MOD_ID, CERT_SECTION_ID,
                                          cert_section_num, lesson_forum_ids))
    write_static_files_for_customcert(cert_dir)

    # ── 6. Sections ──────────────────────────────────────────────────────────
    print("\n[sections/]")
    # Section 0
    sec0_dir = out_dir / "sections" / f"section_{SECTION0_ID}"
    sec0_dir.mkdir(parents=True)
    write_file(sec0_dir / "section.xml",
               gen_section0_xml(course, facilitators, ANN_FORUM_MOD_ID))

    # Lesson sections
    for i, lesson in enumerate(lessons):
        sec_dir = out_dir / "sections" / f"section_{lesson['moodle_section_id']}"
        sec_dir.mkdir(parents=True)
        write_file(sec_dir / "section.xml",
                   gen_lesson_section_xml(lesson, i, lo_map, lp_base_url))

    # Certificate section
    cert_sec_dir = out_dir / "sections" / f"section_{CERT_SECTION_ID}"
    cert_sec_dir.mkdir(parents=True)
    write_file(cert_sec_dir / "section.xml",
               gen_cert_section_xml(CERT_SECTION_ID, cert_section_num, CERT_MOD_ID))

    # ── 7. files/ directory + files.xml ──────────────────────────────────────
    print("\n[files/]")
    files_dir = out_dir / "files"
    files_dir.mkdir()

    # Get cert file entries from template files.xml
    template_files_xml = TEMPLATE_DIR / "files.xml"
    cert_entries_xml = []
    cert_hashes = set()
    if template_files_xml.exists():
        cert_entries_xml = read_customcert_file_entries(template_files_xml)
        # Extract hashes to copy physical files
        for entry in cert_entries_xml:
            m = re.search(r"<contenthash>([0-9a-f]{40})</contenthash>", entry)
            if m:
                cert_hashes.add(m.group(1))

    # Copy cert image physical files
    template_files_phys = TEMPLATE_DIR / "files"
    for h in cert_hashes:
        if h == EMPTY_DIR_HASH:
            continue
        src_path = template_files_phys / h[:2] / h
        if src_path.exists():
            copy_cert_image_to_files(src_path, files_dir)
            print(f"  + files/{h[:2]}/{h[:12]}... (cert image)")
        else:
            print(f"  WARNING: cert image file not found: {src_path}")

    # Institutional logos (for @@PLUGINFILE@@ in section 0)
    inst_logos = get_institutional_logos()
    for logo in inst_logos:
        dest_dir = files_dir / logo["contenthash"][:2]
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(logo["filepath"], dest_dir / logo["contenthash"])
        print(f"  + files/{logo['contenthash'][:2]}/{logo['contenthash'][:12]}... ({logo['filename']})")

    # Course logo
    logo_info = None
    logo_file = course.get("course_logo_file")
    if logo_file:
        logo_src = COURSE_LOGOS / logo_file
        if logo_src.exists():
            logo_hash = sha1_of_file(logo_src)
            logo_size = logo_src.stat().st_size
            ext = logo_src.suffix.lower()
            logo_mime = EXTENSION_TO_MIME.get(ext, "image/jpeg")
            logo_dest_dir = files_dir / logo_hash[:2]
            logo_dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(logo_src, logo_dest_dir / logo_hash)
            print(f"  + files/{logo_hash[:2]}/{logo_hash[:12]}... ({logo_file})")
            logo_info = {
                "filename": logo_file,
                "contenthash": logo_hash,
                "filesize": logo_size,
                "mimetype": logo_mime,
            }
        else:
            print(f"  WARNING: course logo not found: {logo_src}")

    # Generate files.xml
    write_file(out_dir / "files.xml",
               gen_files_xml(cert_entries_xml, logo_info, inst_logos))

    # ── 8. moodle_backup.xml ─────────────────────────────────────────────────
    print("\n[moodle_backup.xml]")
    act_entries = [
        {"moduleid": ANN_FORUM_MOD_ID, "sectionid": SECTION0_ID,
         "modulename": "forum", "title": "Announcements",
         "directory": f"activities/forum_{ANN_FORUM_MOD_ID}"},
    ]
    for i, lesson in enumerate(lessons):
        act_entries.append({
            "moduleid":   lesson["forum_id"],
            "sectionid":  lesson["moodle_section_id"],
            "modulename": "forum",
            "title":      f"Discussion: {lesson_short_name(lesson)}",
            "directory":  f"activities/forum_{lesson['forum_id']}",
        })
    act_entries.append({
        "moduleid":   CERT_MOD_ID,
        "sectionid":  CERT_SECTION_ID,
        "modulename": "customcert",
        "title":      "Download your completion certificate",
        "directory":  f"activities/customcert_{CERT_MOD_ID}",
    })

    sect_entries = [
        {"sectionid": SECTION0_ID, "title": "0",
         "directory": f"sections/section_{SECTION0_ID}"},
    ]
    for i, lesson in enumerate(lessons):
        sect_entries.append({
            "sectionid": lesson["moodle_section_id"],
            "title":     lesson_title(lesson, i),
            "directory": f"sections/section_{lesson['moodle_section_id']}",
        })
    sect_entries.append({
        "sectionid": CERT_SECTION_ID,
        "title":     "🏅 Completion Certificate",
        "directory": f"sections/section_{CERT_SECTION_ID}",
    })

    write_file(out_dir / "moodle_backup.xml",
               gen_moodle_backup_xml(course, lessons, sect_entries, act_entries, folder_name))

    # ── 9. .ARCHIVE_INDEX ────────────────────────────────────────────────────
    print("\n[.ARCHIVE_INDEX]")
    write_archive_index(out_dir, folder_name)

    print(f"\n✓ Done! Course folder: {out_dir}")
    return out_dir, folder_name


def write_archive_index(out_dir: Path, folder_name: str):
    """Generate .ARCHIVE_INDEX listing all files and directories."""
    lines = []
    ts = str(NOW_TS)

    def add_dir(rel):
        lines.append(f"{rel}\td\t0\t?")

    def add_file(rel, path: Path):
        size = path.stat().st_size
        lines.append(f"{rel}\tf\t{size}\t{ts}")

    # Walk the directory tree in sorted order
    for dirpath, dirnames, filenames in os.walk(out_dir):
        dirnames.sort()
        dir_rel = Path(dirpath).relative_to(out_dir)
        rel_str = str(dir_rel).replace("\\", "/")
        if rel_str != ".":
            add_dir(rel_str + "/")
        for fname in sorted(filenames):
            if fname == ".ARCHIVE_INDEX":
                continue
            fpath = Path(dirpath) / fname
            frel  = (dir_rel / fname) if rel_str != "." else Path(fname)
            add_file(str(frel).replace("\\", "/"), fpath)

    total = sum(1 for l in lines if "\tf\t" in l)
    header = f"Moodle archive file index. Count: {total}"
    content = header + "\n" + "\n".join(lines)
    index_path = out_dir / ".ARCHIVE_INDEX"
    index_path.write_text(content, encoding="utf-8")
    print(f"  + .ARCHIVE_INDEX ({total} files)")


# ─── Entry point ─────────────────────────────────────────────────────────────

# ─── Missing-data collection ──────────────────────────────────────────────────

COURSE_LOGOS_DIR = REPO_ROOT / "assets" / "course-logos"


def _find_course_logo(section_filecase: str) -> str | None:
    for ext in ("jpg", "jpeg", "png", "webp", "gif", "svg"):
        candidate = COURSE_LOGOS_DIR / f"{section_filecase}.{ext}"
        if candidate.exists():
            return candidate.name
    return None


def save_courses_json(data: dict):
    with open(COURSES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def collect_missing_data(course: dict, data: dict):
    """
    Interactively fill in any fields that cannot be sourced from the CSV:
      - chapter_number
      - section_number
      - course_logo_file

    Saves answers back to courses.json immediately so the user is never
    asked the same question twice.
    """
    changed = False
    section  = course["section"]
    chapter  = course["chapter"]

    if course.get("chapter_number") is None:
        while True:
            raw = input(f"  Chapter number for '{chapter}' (e.g. 1, 4, 5): ").strip()
            try:
                course["chapter_number"] = int(raw); changed = True; break
            except ValueError:
                print("    Please enter a whole number.")

    if course.get("section_number") is None:
        while True:
            raw = input(f"  Section number for '{section}' within chapter {course['chapter_number']}: ").strip()
            try:
                course["section_number"] = int(raw); changed = True; break
            except ValueError:
                print("    Please enter a whole number.")

    if "course_logo_file" not in course or course.get("course_logo_file") is None:
        detected = _find_course_logo(course["section_filecase"])
        suggestion = detected or f"{course['section_filecase']}.jpg"
        raw = input(
            f"  Logo filename for '{section}' (in assets/course-logos/)\n"
            f"  [{suggestion}] (or 'none' to skip): "
        ).strip()
        if not raw:
            raw = suggestion
        course["course_logo_file"] = None if raw.lower() == "none" else raw
        changed = True

    if changed:
        # Write the updated course back into the data dict and save.
        for c in data["courses"]:
            if c["section_filecase"] == course["section_filecase"]:
                c.update({
                    "chapter_number":  course["chapter_number"],
                    "section_number":  course["section_number"],
                    "course_logo_file": course["course_logo_file"],
                })
                break
        save_courses_json(data)
        print(f"  ✓ Saved to courses.json\n")


# ─── Main entry point ─────────────────────────────────────────────────────────

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_compress = "--compress" in sys.argv

    data = load_courses_json()
    key  = args[0] if args else None
    course = select_course(data, key)

    print(f"\nSelected: {course['section']}  ({course['chapter']})")
    print(f"  Lessons: {len(course['lessons'])}")

    # Ask for any data that couldn't come from the CSV
    print()
    collect_missing_data(course, data)

    print(f"  Logo:    {course.get('course_logo_file') or '(none)'}")

    result = generate_course(course, data)
    if result is None:
        return

    out_dir, folder_name = result

    if do_compress:
        compress_script = REPO_ROOT / "scripts" / "compress_mbz.py"
        if compress_script.exists():
            import subprocess
            mbz_name = f"{folder_name}.mbz"
            print(f"\nCompressing to {mbz_name}...")
            subprocess.run(
                [sys.executable, str(compress_script), folder_name, mbz_name],
                cwd=str(REPO_ROOT),
                check=True,
            )
        else:
            print("\ncompress_mbz.py not found; skipping compression.")


if __name__ == "__main__":
    main()
