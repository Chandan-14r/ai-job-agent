"""ATS-Optimized Word Document (.docx) Resume Generator for Kiran A N."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from candidate_profile.loader import CandidateProfile
from candidate_profile.resume_verifier import verify_profile_against_guardrails


class ResumeVariant(str, Enum):
    RESUME_A = "RESUME_A"  # Python Full Stack Developer
    RESUME_B = "RESUME_B"  # Python Backend Developer
    RESUME_C = "RESUME_C"  # SQL / Database Developer


def set_font(run, font_name="Calibri", font_size=11, color=RGBColor(30, 30, 30), bold=False, italic=False):
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.color.rgb = color
    run.bold = bold
    run.italic = italic


def add_section_heading(doc: Document, title: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(title.upper())
    set_font(run, font_size=11, color=RGBColor(16, 44, 87), bold=True)
    # Bottom border simulation via underline or rule in clean ATS style


def generate_docx_resume(
    profile: CandidateProfile,
    variant: ResumeVariant | str = ResumeVariant.RESUME_A,
    output_dir: Optional[Path | str] = None,
) -> str:
    """Generate ATS-optimized DOCX resume variant strictly adhering to zero-fabrication rules."""
    variant_enum = ResumeVariant(variant) if isinstance(variant, str) else variant

    if output_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
        out_path = base_dir / "output" / "resumes"
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    filename = f"Kiran_A_N_Resume_{variant_enum.value}.docx"
    file_path = out_path / filename

    doc = Document()

    # Set 0.6 inch standard ATS margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.6)
        s.bottom_margin = Inches(0.6)
        s.left_margin = Inches(0.6)
        s.right_margin = Inches(0.6)

    # 1. Header (Name, Title & Contact Info)
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_name.paragraph_format.space_after = Pt(2)
    run_name = p_name.add_run(profile.full_name)
    set_font(run_name, font_size=18, color=RGBColor(16, 44, 87), bold=True)

    # Variant-specific headline
    if variant_enum == ResumeVariant.RESUME_A:
        headline = "Entry-Level Python Full Stack Developer | Django & Web Solutions"
    elif variant_enum == ResumeVariant.RESUME_B:
        headline = "Python Backend Developer | Django, REST APIs & Relational Databases"
    else:
        headline = "SQL & Database Developer | Relational Schema Design & Django ORM"

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run(headline)
    set_font(run_title, font_size=11, color=RGBColor(60, 60, 60), bold=True)

    # Contact line (strictly using verified items)
    contact_parts = [profile.contact.current_location]
    if profile.contact.email:
        contact_parts.append(profile.contact.email)
    if profile.contact.phone:
        contact_parts.append(profile.contact.phone)
    contact_parts.append("GitHub: github.com/kiranan2004-lgtm")
    contact_parts.append("LinkedIn: linkedin.com/in/kiran-an-6a365137")

    p_contact = doc.add_paragraph()
    p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_contact.paragraph_format.space_after = Pt(8)
    run_contact = p_contact.add_run(" | ".join(contact_parts))
    set_font(run_contact, font_size=9, color=RGBColor(80, 80, 80))

    # 2. Professional Summary
    add_section_heading(doc, "Professional Summary")
    p_sum = doc.add_paragraph()
    p_sum.paragraph_format.space_after = Pt(6)
    if variant_enum == ResumeVariant.RESUME_A:
        summary_text = (
            "Motivated Computer Science Engineering graduate with intensive Python Full Stack training at QSpiders "
            "and hands-on project experience engineering responsive, database-backed web applications using Python, "
            "Django MVT architecture, SQL/Oracle SQL, and JavaScript (ES6+). Proven ability to deliver structured "
            "code, implement user authentication, dynamic charts, and responsive UI components."
        )
    elif variant_enum == ResumeVariant.RESUME_B:
        summary_text = (
            "Detail-oriented Backend Developer equipped with strong foundations in Python core OOP, exception handling, "
            "and Django backend architecture. Experienced in designing relational database schemas, executing complex "
            "SQL queries, integrating RESTful API endpoints, and implementing secure user authentication models."
        )
    else:
        summary_text = (
            "Database-focused Software Developer with demonstrated proficiency in SQL and Oracle SQL relational query "
            "construction, CRUD operations, complex Joins, Subqueries, and GROUP BY aggregations. Skilled in translating "
            "business requirements into normalized relational schemas and integrating databases seamlessly via Django ORM."
        )
    run_sum = p_sum.add_run(summary_text)
    set_font(run_sum, font_size=10, color=RGBColor(40, 40, 40))

    # 3. Technical Skills
    add_section_heading(doc, "Technical Skills")
    if variant_enum == ResumeVariant.RESUME_A:
        skill_groups = [
            ("Programming Languages", "Python, JavaScript (ES6+), SQL"),
            ("Backend Framework", "Django, Django MVT Architecture, ORM, URL Routing, Forms, Authentication"),
            ("Database Management", "SQL, Oracle SQL (CRUD Operations, Joins, Subqueries, Aggregations)"),
            ("Frontend Engineering", "HTML5, CSS3, Flexbox, CSS Grid, Media Queries, Responsive Design, Fetch API"),
            ("Developer Tools", "Git, GitHub, Visual Studio Code"),
            ("Testing & Automation", "Selenium WebDriver (In Training)"),
        ]
    elif variant_enum == ResumeVariant.RESUME_B:
        skill_groups = [
            ("Core Programming", "Python (OOP, Data Structures, Exception Handling, File Handling, Modules)"),
            ("Backend Architecture", "Django, Django ORM, Authentication, URL Routing, Views, Template Rendering"),
            ("APIs & Integration", "REST API Fundamentals, JSON Serialization, Fetch API"),
            ("Relational Databases", "SQL, Oracle SQL (Complex Joins, Subqueries, GROUP BY, Aggregate Queries)"),
            ("Version Control & Tools", "Git, GitHub, VS Code"),
            ("Automation Testing", "Selenium WebDriver (Basics)"),
        ]
    else:
        skill_groups = [
            ("Database Technologies", "SQL, Oracle SQL, Relational Schema Design, Normalization Fundamentals"),
            ("Query Proficiency", "CRUD Operations, Multi-Table Joins, Nested Subqueries, GROUP BY, HAVING, Aggregates"),
            ("Backend Integration", "Python, Django ORM, Database Models, Data Migration, Query Optimization Basics"),
            ("Frontend & Web", "HTML5, CSS3, JavaScript (DOM, Fetch API)"),
            ("Tools & Environment", "Git, GitHub, Visual Studio Code"),
        ]

    # 4. Professional Experience & Training
    add_section_heading(doc, "Professional Experience & Training")

    # QSpiders Training
    p_tr = doc.add_paragraph()
    p_tr.paragraph_format.space_before = Pt(3)
    p_tr.paragraph_format.space_after = Pt(1)
    r_tr_title = p_tr.add_run("Python Full Stack Development Training — QSpiders, Basavanagudi, Bengaluru | 2026 – Present\n")
    set_font(r_tr_title, font_size=10, bold=True)
    qspiders_bullets = [
        "Learned and practiced Python programming: structured programming, OOP, exception handling, file handling, collections, modules and packages, and data handling.",
        "Learned Django backend development: MVT architecture, URLs, views, templates, models, forms, authentication, static files, and backend integration with databases.",
        "Learned SQL and database concepts including CRUD operations, joins, subqueries, grouping, filtering, and aggregate queries.",
        "Gained hands-on command of JavaScript: ES6+ features, functions, arrays, DOM manipulation, BOM, form validation, and promises; currently learning Selenium.",
    ]
    for b in qspiders_bullets:
        p_b = doc.add_paragraph()
        p_b.paragraph_format.left_indent = Inches(0.2)
        p_b.paragraph_format.space_after = Pt(1)
        p_b.paragraph_format.space_before = Pt(1)
        r_b = p_b.add_run(f"- {b}")
        set_font(r_b, font_size=9)

    # Prinston Smart Engineer Internship (Verified from resume)
    p_pr = doc.add_paragraph()
    p_pr.paragraph_format.space_before = Pt(4)
    p_pr.paragraph_format.space_after = Pt(1)
    r_pr_title = p_pr.add_run("Prinston Smart Engineer — Internship\n")
    set_font(r_pr_title, font_size=10, bold=True)
    prinston_bullets = [
        "Completed a Smart Engineer internship and gained practical exposure to a professional technical/work environment.",
        "Developed practical understanding through internship-based technical work and problem-solving.",
    ]
    for b in prinston_bullets:
        p_b = doc.add_paragraph()
        p_b.paragraph_format.left_indent = Inches(0.2)
        p_b.paragraph_format.space_after = Pt(1)
        p_b.paragraph_format.space_before = Pt(1)
        r_b = p_b.add_run(f"- {b}")
        set_font(r_b, font_size=9)

    # 5. Verified Technical Projects
    add_section_heading(doc, "Projects")

    # Project 1: Stock Market Analysis (Django Full Stack)
    p_p1 = doc.add_paragraph()
    p_p1.paragraph_format.space_before = Pt(4)
    p_p1.paragraph_format.space_after = Pt(1)
    r_p1_title = p_p1.add_run("Stock Market Analysis — Django Full Stack Project")
    set_font(r_p1_title, font_size=10, bold=True)
    r_p1_stack = p_p1.add_run(" | Python, Django, SQL database, HTML, CSS, JavaScript")
    set_font(r_p1_stack, font_size=9, italic=True, color=RGBColor(80, 80, 80))

    if variant_enum == ResumeVariant.RESUME_C:
        p1_bullets = [
            "Designed Django models and the database layer to store and retrieve company information and stock price data.",
            "Engineered complex SQL queries with joins, grouping, and aggregations to calculate market metrics.",
            "Processed historical price data to build interactive charts with selectable ranges such as 1M and 1Y.",
            "Integrated predictive forecasting and news features, maintaining clean relational database persistence."
        ]
    elif variant_enum == ResumeVariant.RESUME_B:
        p1_bullets = [
            "Developed Django full stack application for stock analysis using Python, Django, SQL database, HTML, CSS, and JavaScript.",
            "Designed Django models and the database layer to store and retrieve company information and stock price data.",
            "Implemented user authentication and stock-specific pages using Django URLs, views, templates, and forms.",
            "Applied object-oriented, modular, and structured coding practices across the Django application."
        ]
    else:
        p1_bullets = [
            "Developed a Django full stack application for stock analysis using Python, Django, SQL database, HTML, CSS, and JavaScript.",
            "Designed Django models and the database layer to store and retrieve company information and stock price data.",
            "Implemented user authentication and stock-specific pages using Django URLs, views, templates, and forms.",
            "Processed historical price data to build interactive charts with selectable ranges such as 1M and 1Y.",
            "Added forecasting and news-related features, integrating backend logic with the frontend."
        ]

    for b in p1_bullets:
        p_b = doc.add_paragraph()
        p_b.paragraph_format.left_indent = Inches(0.2)
        p_b.paragraph_format.space_after = Pt(1)
        p_b.paragraph_format.space_before = Pt(1)
        r_b = p_b.add_run(f"- {b}")
        set_font(r_b, font_size=9)

    # Project 2: Food Delivery Web Page
    if variant_enum in [ResumeVariant.RESUME_A, ResumeVariant.RESUME_B]:
        p_p2 = doc.add_paragraph()
        p_p2.paragraph_format.space_before = Pt(4)
        p_p2.paragraph_format.space_after = Pt(1)
        r_p2_title = p_p2.add_run("Food Delivery Web Page — HTML, CSS, JavaScript")
        set_font(r_p2_title, font_size=10, bold=True)

        p2_bullets = [
            "Built a responsive food-delivery webpage using semantic HTML, CSS Flexbox/Grid, media queries, positioning, and animations.",
            "Used JavaScript extensively: DOM manipulation, event handling, functions, arrays and objects, and array methods to dynamically render and update page content.",
            "Implemented interactive features such as cart updates and form validation with clean, reusable JavaScript logic."
        ]
        for b in p2_bullets:
            p_b = doc.add_paragraph()
            p_b.paragraph_format.left_indent = Inches(0.2)
            p_b.paragraph_format.space_after = Pt(1)
            p_b.paragraph_format.space_before = Pt(1)
            r_b = p_b.add_run(f"- {b}")
            set_font(r_b, font_size=9)

    # 6. Education
    add_section_heading(doc, "Education")

    p_edu1 = doc.add_paragraph()
    p_edu1.paragraph_format.space_before = Pt(2)
    p_edu1.paragraph_format.space_after = Pt(1)
    r_deg1 = p_edu1.add_run("B.E. in Computer Science & Engineering — JSS Academy of Technical Education, Bengaluru | CGPA: 7.98")
    set_font(r_deg1, font_size=9.5, bold=True)

    p_edu2 = doc.add_paragraph()
    p_edu2.paragraph_format.space_before = Pt(1)
    p_edu2.paragraph_format.space_after = Pt(1)
    r_deg2 = p_edu2.add_run("12th (Pre-University) — Aishwarya Public College, Maddur | 89%")
    set_font(r_deg2, font_size=9.5)

    p_edu3 = doc.add_paragraph()
    p_edu3.paragraph_format.space_before = Pt(1)
    p_edu3.paragraph_format.space_after = Pt(2)
    r_deg3 = p_edu3.add_run("10th (SSLC) — Bethel International Public School, Ramanagara | 90%")
    set_font(r_deg3, font_size=9.5)

    # 7. Core Strengths
    add_section_heading(doc, "Core Strengths")
    p_cs = doc.add_paragraph()
    p_cs.paragraph_format.space_before = Pt(2)
    p_cs.paragraph_format.space_after = Pt(2)
    r_cs = p_cs.add_run("Problem Solving | Logical Thinking | Structured Programming | Willingness to Learn | Team Collaboration")
    set_font(r_cs, font_size=9.5)

    # Strict compliance check before saving
    full_text = " ".join([p.text for p in doc.paragraphs])
    verify_result = verify_profile_against_guardrails(profile, full_text)
    if not verify_result.is_valid:
        raise ValueError(f"DOCX Resume generated violates guardrails: {verify_result.violations}")

    doc.save(str(file_path))
    return str(file_path)
