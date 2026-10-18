"""ATS-Optimized PDF Resume Generator for Kiran A N using ReportLab."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable

from candidate_profile.loader import CandidateProfile
from candidate_profile.resume_verifier import verify_profile_against_guardrails
from .builder_docx import ResumeVariant


def generate_pdf_resume(
    profile: CandidateProfile,
    variant: ResumeVariant | str = ResumeVariant.RESUME_A,
    output_dir: Optional[Path | str] = None,
) -> str:
    """Generate professional, selectable-text, ATS-friendly PDF resume variant."""
    variant_enum = ResumeVariant(variant) if isinstance(variant, str) else variant

    if output_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
        out_path = base_dir / "output" / "resumes"
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    filename = f"Kiran_A_N_Resume_{variant_enum.value}.pdf"
    file_path = out_path / filename

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,  # Center
        textColor=colors.HexColor("#102C57"),
    )

    sub_title_style = ParagraphStyle(
        "ResumeSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        alignment=1,  # Center
        textColor=colors.HexColor("#333333"),
        spaceAfter=3,
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=1,  # Center
        textColor=colors.HexColor("#555555"),
        spaceAfter=6,
    )

    heading_style = ParagraphStyle(
        "ResumeSectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#102C57"),
        spaceBefore=7,
        spaceAfter=2,
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#222222"),
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#222222"),
        leftIndent=12,
        spaceAfter=2,
    )

    story = []

    # 1. Header
    story.append(Paragraph(profile.full_name, title_style))

    if variant_enum == ResumeVariant.RESUME_A:
        headline = "Entry-Level Python Full Stack Developer | Django & Web Solutions"
    elif variant_enum == ResumeVariant.RESUME_B:
        headline = "Python Backend Developer | Django, REST APIs & Relational Databases"
    else:
        headline = "SQL & Database Developer | Relational Schema Design & Django ORM"

    story.append(Paragraph(headline, sub_title_style))

    contact_parts = [profile.contact.current_location]
    if profile.contact.email:
        contact_parts.append(profile.contact.email)
    if profile.contact.phone:
        contact_parts.append(profile.contact.phone)
    contact_parts.append("github.com/kiranan2004-lgtm")
    contact_parts.append("linkedin.com/in/kiran-an-6a365137")

    story.append(Paragraph(" &bull; ".join(contact_parts), contact_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#102C57"), spaceBefore=1, spaceAfter=4))

    # 2. Professional Summary
    story.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
    if variant_enum == ResumeVariant.RESUME_A:
        sum_txt = (
            "Motivated Computer Science Engineering graduate with intensive Python Full Stack training at QSpiders "
            "and hands-on project experience engineering responsive, database-backed web applications using Python, "
            "Django MVT architecture, SQL/Oracle SQL, and JavaScript (ES6+). Proven ability to deliver structured "
            "code, implement user authentication, dynamic charts, and responsive UI components."
        )
    elif variant_enum == ResumeVariant.RESUME_B:
        sum_txt = (
            "Detail-oriented Backend Developer equipped with strong foundations in Python core OOP, exception handling, "
            "and Django backend architecture. Experienced in designing relational database schemas, executing complex "
            "SQL queries, integrating RESTful API endpoints, and implementing secure user authentication models."
        )
    else:
        sum_txt = (
            "Database-focused Software Developer with demonstrated proficiency in SQL and Oracle SQL relational query "
            "construction, CRUD operations, complex Joins, Subqueries, and GROUP BY aggregations. Skilled in translating "
            "business requirements into normalized relational schemas and integrating databases seamlessly via Django ORM."
        )
    story.append(Paragraph(sum_txt, body_style))

    # 3. Technical Skills
    story.append(Paragraph("TECHNICAL SKILLS", heading_style))
    if variant_enum == ResumeVariant.RESUME_A:
        skills = [
            ("Programming Languages", "Python, JavaScript (ES6+), SQL"),
            ("Backend Framework", "Django, Django MVT Architecture, ORM, URL Routing, Forms, Authentication"),
            ("Database Management", "SQL, Oracle SQL (CRUD Operations, Relational Joins, Subqueries, Aggregations)"),
            ("Frontend Engineering", "HTML5, CSS3, Flexbox, CSS Grid, Media Queries, Responsive Design, Fetch API"),
            ("Developer Tools", "Git, GitHub, Visual Studio Code"),
            ("Testing & Automation", "Selenium WebDriver (In Training)"),
        ]
    elif variant_enum == ResumeVariant.RESUME_B:
        skills = [
            ("Core Programming", "Python (OOP, Data Structures, Exception Handling, File Handling, Modules)"),
            ("Backend Architecture", "Django, Django ORM, Authentication, URL Routing, Views, Template Rendering"),
            ("APIs & Integration", "REST API Fundamentals, JSON Serialization, Fetch API"),
            ("Relational Databases", "SQL, Oracle SQL (Complex Joins, Subqueries, GROUP BY, Aggregate Queries)"),
            ("Version Control & Tools", "Git, GitHub, Visual Studio Code"),
            ("Automation Testing", "Selenium WebDriver (Basics)"),
        ]
    else:
        skills = [
            ("Database Technologies", "SQL, Oracle SQL, Relational Schema Design, Normalization Fundamentals"),
            ("Query Proficiency", "CRUD Operations, Multi-Table Joins, Nested Subqueries, GROUP BY, HAVING, Aggregates"),
            ("Backend Integration", "Python, Django ORM, Database Models, Data Migration, Query Optimization Basics"),
            ("Frontend & Web", "HTML5, CSS3, JavaScript (DOM, Fetch API)"),
            ("Tools & Environment", "Git, GitHub, Visual Studio Code"),
        ]

    for label, val in skills:
        story.append(Paragraph(f"&bull; <b>{label}:</b> {val}", bullet_style))

    # 4. Professional Experience & Training
    story.append(Paragraph("PROFESSIONAL EXPERIENCE & TRAINING", heading_style))

    # QSpiders Training
    story.append(Paragraph("<b>Python Full Stack Development Training — QSpiders, Basavanagudi, Bengaluru | 2026 – Present</b>", body_style))
    qspiders_bullets = [
        "Learned and practiced Python programming: structured programming, OOP, exception handling, file handling, collections, modules and packages, and data handling.",
        "Learned Django backend development: MVT architecture, URLs, views, templates, models, forms, authentication, static files, and backend integration with databases.",
        "Learned SQL and database concepts including CRUD operations, joins, subqueries, grouping, filtering, and aggregate queries.",
        "Gained hands-on command of JavaScript: ES6+ features, functions, arrays, DOM manipulation, BOM, form validation, and promises; currently learning Selenium.",
    ]
    for b in qspiders_bullets:
        story.append(Paragraph(f"- {b}", bullet_style))

    # Prinston Smart Engineer Internship (Verified on resume)
    story.append(Paragraph("<b>Prinston Smart Engineer — Internship</b>", body_style))
    prinston_bullets = [
        "Completed a Smart Engineer internship and gained practical exposure to a professional technical/work environment.",
        "Developed practical understanding through internship-based technical work and problem-solving.",
    ]
    for b in prinston_bullets:
        story.append(Paragraph(f"- {b}", bullet_style))

    # 5. Technical Projects
    story.append(Paragraph("PROJECTS", heading_style))

    # Project 1: Stock Market Analysis
    story.append(Paragraph("<b>Stock Market Analysis — Django Full Stack Project</b> <i>| Python, Django, SQL database, HTML, CSS, JavaScript</i>", body_style))
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
        story.append(Paragraph(f"- {b}", bullet_style))

    story.append(Spacer(1, 2))

    # Project 2: Food Delivery Web Page
    if variant_enum in [ResumeVariant.RESUME_A, ResumeVariant.RESUME_B]:
        story.append(Paragraph("<b>Food Delivery Web Page — HTML, CSS, JavaScript</b>", body_style))
        p2_bullets = [
            "Built a responsive food-delivery webpage using semantic HTML, CSS Flexbox/Grid, media queries, positioning, and animations.",
            "Used JavaScript extensively: DOM manipulation, event handling, functions, arrays and objects, and array methods to dynamically render and update page content.",
            "Implemented interactive features such as cart updates and form validation with clean, reusable JavaScript logic."
        ]
        for b in p2_bullets:
            story.append(Paragraph(f"- {b}", bullet_style))

    # 6. Education
    story.append(Paragraph("EDUCATION", heading_style))
    story.append(Paragraph("<b>B.E. in Computer Science & Engineering — JSS Academy of Technical Education, Bengaluru | CGPA: 7.98</b>", body_style))
    story.append(Paragraph("12th (Pre-University) — Aishwarya Public College, Maddur | 89%", bullet_style))
    story.append(Paragraph("10th (SSLC) — Bethel International Public School, Ramanagara | 90%", bullet_style))

    # 7. Core Strengths
    story.append(Paragraph("CORE STRENGTHS", heading_style))
    story.append(Paragraph("Problem Solving | Logical Thinking | Structured Programming | Willingness to Learn | Team Collaboration", bullet_style))

    # Build PDF
    doc.build(story)
    return str(file_path)
