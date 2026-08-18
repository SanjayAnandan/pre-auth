"""
src/pdf_report.py - Professional Healthcare Prior Authorization PDF Report Generator

Generates enterprise-grade, deterministic Prior Authorization Decision Reports in PDF format
using ReportLab.
"""

import io
import html
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count,
    running headers, and footers on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (on pages 2 and later)
        if self._pageNumber > 1:
            self.drawString(54, 805, "PRIORAUTH AI — Prior Authorization Decision Report")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 797, 541, 797)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 541, 45)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(541, 32, page_str)
        self.drawString(54, 32, "CONFIDENTIAL & PROPRIETARY — PriorAuth AI Healthcare System")
        self.restoreState()


def clean_txt(val: Any, default: str = "N/A") -> str:
    """Safely sanitize text for ReportLab XML Paragraph rendering."""
    if val is None:
        return default
    s = str(val).strip()
    if not s or s.upper() in ("NONE", "NULL", ""):
        return default
    return html.escape(s)


def format_display_date(date_val: Any) -> str:
    """Formats ISO date strings or datetime objects to DD-Mon-YYYY format."""
    if not date_val:
        return "N/A"
    if isinstance(date_val, (datetime,)):
        return date_val.strftime("%d-%b-%Y")
    s = str(date_val).strip()
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%d-%b-%Y")
        dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return dt.strftime("%d-%b-%Y")
    except Exception:
        return clean_txt(s)


def generate_report(case_data: Dict[str, Any]) -> bytes:
    """
    Generates a complete, professional Prior Authorization Decision Report PDF bytes
    from an existing authorization case record.

    :param case_data: Unified case dictionary containing patient, verification, request,
                      decision, prediction, criteria, and audit data.
    :return: PDF file bytes.
    """
    buffer = io.BytesIO()

    # Document setup: A4 size with 54pt (0.75 in) margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    story = []

    # ---------------------------------------------------------
    # Styles Setup
    # ---------------------------------------------------------
    styles = getSampleStyleSheet()

    # Custom Palette
    c_primary = colors.HexColor("#0F172A")    # Dark Slate Navy
    c_secondary = colors.HexColor("#334155")  # Slate Accent
    c_border = colors.HexColor("#E2E8F0")     # Light Border
    c_bg_light = colors.HexColor("#F8FAFC")   # Section Box Light Slate

    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=2
    )

    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0D9488"), # Teal accent
        spaceAfter=0
    )

    style_meta_header = ParagraphStyle(
        'MetaHeader',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_secondary,
        alignment=2 # Right aligned
    )

    style_section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_primary,
        spaceBefore=12,
        spaceAfter=6
    )

    style_body = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B")
    )

    style_body_bold = ParagraphStyle(
        'BodyDarkBold',
        parent=style_body,
        fontName='Helvetica-Bold'
    )

    style_label = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748B")
    )

    style_val = ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A")
    )

    style_cell_header = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    # ---------------------------------------------------------
    # Extract Case Data Elements safely
    # ---------------------------------------------------------
    patient = case_data.get("patient") or {}
    verification = case_data.get("verification") or {}
    request_info = case_data.get("request") or {}
    decision_info = case_data.get("decision") or {}
    criteria_list = case_data.get("criteria") or case_data.get("results") or []
    audit_info = case_data.get("audit") or {}

    # Extract Key Identifiers & Dates
    req_id = clean_txt(request_info.get("id") or audit_info.get("request_id"), "REQ-UNKNOWN")
    now_dt = datetime.now()
    report_date_str = now_dt.strftime("%d-%b-%Y")
    report_time_str = now_dt.strftime("%H:%M:%S")

    # Final Decision String
    final_decision_raw = str(decision_info.get("decision") or request_info.get("status") or "PENDING").upper().strip()

    # Document Verification Status Flag
    is_verification_passed = verification.get("verified", True)
    if final_decision_raw == "DOCUMENT VERIFICATION FAILED" or verification.get("status") == "MISMATCH":
        is_verification_passed = False

    # ---------------------------------------------------------
    # 1. HEADER SECTION
    # ---------------------------------------------------------
    header_left = [
        Paragraph("PRIORAUTH AI", style_title),
        Paragraph("Prior Authorization Decision Report", style_subtitle)
    ]

    header_right = [
        Paragraph(f"<b>Request ID:</b> {req_id}", style_meta_header),
        Paragraph(f"<b>Report Date:</b> {report_date_str}", style_meta_header),
        Paragraph(f"<b>Report Time:</b> {report_time_str}", style_meta_header)
    ]

    header_table = Table([[header_left, header_right]], colWidths=[300, 187])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D9488"), spaceBefore=2, spaceAfter=10))

    # ---------------------------------------------------------
    # 2. PATIENT INFORMATION SECTION
    # ---------------------------------------------------------
    story.append(Paragraph("PATIENT INFORMATION", style_section_heading))

    p_name = clean_txt(patient.get("patient_name"))
    p_id = clean_txt(patient.get("patient_id"))
    dob = format_display_date(patient.get("date_of_birth") or patient.get("dob"))
    age = clean_txt(patient.get("age"))
    gender = clean_txt(patient.get("gender"))
    member_id = clean_txt(patient.get("member_id") or patient.get("subscriber_id"))
    payer = clean_txt(request_info.get("payer") or patient.get("payer"))
    plan_type = clean_txt(patient.get("plan_type"))
    phone = clean_txt(patient.get("phone"))
    email = clean_txt(patient.get("email"))
    address = clean_txt(patient.get("address"))

    patient_grid_data = [
        [
            Paragraph("Patient Name", style_label), Paragraph(p_name, style_val),
            Paragraph("Patient ID (MRN)", style_label), Paragraph(p_id, style_val)
        ],
        [
            Paragraph("Date of Birth", style_label), Paragraph(dob, style_val),
            Paragraph("Age / Gender", style_label), Paragraph(f"{age} / {gender}", style_val)
        ],
        [
            Paragraph("Member ID", style_label), Paragraph(member_id, style_val),
            Paragraph("Payer", style_label), Paragraph(payer, style_val)
        ],
        [
            Paragraph("Plan Type", style_label), Paragraph(plan_type, style_val),
            Paragraph("Phone", style_label), Paragraph(phone, style_val)
        ],
        [
            Paragraph("Email", style_label), Paragraph(email, style_val),
            Paragraph("Address", style_label), Paragraph(address, style_val)
        ]
    ]

    patient_table = Table(patient_grid_data, colWidths=[100, 143, 100, 144])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 3. DOCUMENT VERIFICATION SECTION
    # ---------------------------------------------------------
    story.append(Paragraph("DOCUMENT VERIFICATION", style_section_heading))

    field_checks = verification.get("fields") or {}
    hist_identity = verification.get("history_identity") or {}
    pa_identity = verification.get("pa_identity") or {}

    ver_hist_status = "VERIFIED" if is_verification_passed else "MISMATCH"
    ver_pa_status = "VERIFIED" if is_verification_passed else "MISMATCH"

    ver_summary_data = [
        [
            Paragraph("<b>Patient History Document:</b>", style_body),
            Paragraph(f"<font color=\"{'#16A34A' if is_verification_passed else '#DC2626'}\"><b>✓ {ver_hist_status}</b></font>", style_body),
            Paragraph("<b>PA Request Form Document:</b>", style_body),
            Paragraph(f"<font color=\"{'#16A34A' if is_verification_passed else '#DC2626'}\"><b>✓ {ver_pa_status}</b></font>", style_body)
        ]
    ]
    ver_summary_table = Table(ver_summary_data, colWidths=[130, 113, 130, 114])
    ver_summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(ver_summary_table)
    story.append(Spacer(1, 6))

    # Field-level verification table
    fields_to_compare = [
        ("Patient Name", "name"),
        ("Patient ID", "patient_id"),
        ("Member ID", "member_id"),
        ("Date of Birth", "date_of_birth"),
        ("Gender", "gender"),
    ]

    ver_field_table_data = [
        [Paragraph("Identity Field", style_cell_header), Paragraph("Verification Status", style_cell_header)]
    ]

    for label, key in fields_to_compare:
        status_val = field_checks.get(key)
        if status_val == "MATCH" or (is_verification_passed and status_val != "MISMATCH"):
            res_p = Paragraph("<font color=\"#16A34A\"><b>✓ MATCH</b></font>", style_body)
        elif status_val == "MISMATCH":
            res_p = Paragraph("<font color=\"#DC2626\"><b>✕ MISMATCH</b></font>", style_body)
        else:
            res_p = Paragraph("<font color=\"#475569\">UNAVAILABLE / UNCHECKED</font>", style_body)
        ver_field_table_data.append([Paragraph(label, style_body), res_p])

    ver_field_table = Table(ver_field_table_data, colWidths=[240, 247])
    ver_field_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(ver_field_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 4. MISMATCH REPORT (IF VERIFICATION FAILED)
    # ---------------------------------------------------------
    if not is_verification_passed:
        story.append(Paragraph("DOCUMENT VERIFICATION FAILED", ParagraphStyle(
            'ErrHeading', parent=style_section_heading, textColor=colors.HexColor("#DC2626")
        )))

        mismatch_table_data = [
            [
                Paragraph("Field", style_cell_header),
                Paragraph("History PDF Value", style_cell_header),
                Paragraph("PA Letter Value", style_cell_header)
            ]
        ]

        # Populate mismatched fields
        for label, key in fields_to_compare:
            if field_checks.get(key) == "MISMATCH":
                h_v = clean_txt(hist_identity.get(key))
                p_v = clean_txt(pa_identity.get(key))
                mismatch_table_data.append([
                    Paragraph(label, style_body_bold),
                    Paragraph(h_v, style_body),
                    Paragraph(p_v, style_body)
                ])

        if len(mismatch_table_data) == 1: # Fallback if no specific field marked
            mismatch_table_data.append([
                Paragraph("Demographic Identity", style_body_bold),
                Paragraph(clean_txt(hist_identity.get("name") or hist_identity.get("patient_id")), style_body),
                Paragraph(clean_txt(pa_identity.get("name") or pa_identity.get("patient_id")), style_body)
            ])

        mismatch_table = Table(mismatch_table_data, colWidths=[140, 173, 174])
        mismatch_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#DC2626")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FEF2F2")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(mismatch_table)

        mismatch_note = Paragraph(
            "<font color=\"#DC2626\"><b>Status: MISMATCH</b><br/>"
            "Authorization processing was stopped due to document identity mismatch between the submitted Patient History and PA Request Form.</font>",
            style_body
        )
        story.append(Spacer(1, 4))
        story.append(mismatch_note)
        story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 5. AUTHORIZATION REQUEST DETAILS
    # ---------------------------------------------------------
    story.append(Paragraph("AUTHORIZATION REQUEST", style_section_heading))

    req_service = clean_txt(request_info.get("requested_service") or patient.get("requested_service"))
    cpt_code = clean_txt(request_info.get("cpt_hcpcs_code") or patient.get("cpt_hcpcs_code"))
    diagnosis = clean_txt(patient.get("diagnosis"))
    icd10 = clean_txt(patient.get("icd10_code"))
    req_type = "Prior Authorization"
    payer_val = clean_txt(request_info.get("payer") or patient.get("payer"))
    plan_val = clean_txt(patient.get("plan_type"))

    req_grid_data = [
        [
            Paragraph("Request ID", style_label), Paragraph(req_id, style_val),
            Paragraph("Requested Service", style_label), Paragraph(req_service, style_val)
        ],
        [
            Paragraph("CPT / HCPCS Code", style_label), Paragraph(cpt_code, style_val),
            Paragraph("Diagnosis", style_label), Paragraph(diagnosis, style_val)
        ],
        [
            Paragraph("ICD-10 Code", style_label), Paragraph(icd10, style_val),
            Paragraph("Request Type", style_label), Paragraph(req_type, style_val)
        ],
        [
            Paragraph("Payer", style_label), Paragraph(payer_val, style_val),
            Paragraph("Plan Type", style_label), Paragraph(plan_val, style_val)
        ]
    ]

    req_table = Table(req_grid_data, colWidths=[100, 143, 100, 144])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(req_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 6. CPT / HCPCS SECTION (HIGH VISIBILITY)
    # ---------------------------------------------------------
    story.append(Paragraph("REQUESTED PROCEDURE", style_section_heading))

    cpt_matched = bool(cpt_code and cpt_code != "N/A" and cpt_code != "NONE")
    cpt_match_str = "<font color=\"#16A34A\"><b>✓ MATCHED</b></font>" if cpt_matched else "<font color=\"#DC2626\"><b>✕ NOT MATCHED</b></font>"

    cpt_box_data = [
        [
            Paragraph("Service:", style_label), Paragraph(req_service, style_body_bold),
            Paragraph("CPT / HCPCS:", style_label), Paragraph(f"<b>{cpt_code}</b>", style_body_bold),
            Paragraph("Policy Match:", style_label), Paragraph(cpt_match_str, style_body)
        ]
    ]
    cpt_table = Table(cpt_box_data, colWidths=[60, 130, 75, 90, 70, 62])
    cpt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")), # Soft blue box
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cpt_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 7. APPLIED POLICY SECTION
    # ---------------------------------------------------------
    story.append(Paragraph("APPLIED POLICY", style_section_heading))

    pol_name = clean_txt(decision_info.get("policy_name"), "Medical Coverage Policy")
    pol_id = clean_txt(decision_info.get("policy_id"), "POL-001")
    pol_payer = clean_txt(request_info.get("payer") or patient.get("payer"))
    pol_ver = clean_txt(decision_info.get("policy_version"), "v1.0")

    policy_grid_data = [
        [
            Paragraph("Policy Name", style_label), Paragraph(pol_name, style_val),
            Paragraph("Policy ID", style_label), Paragraph(pol_id, style_val)
        ],
        [
            Paragraph("Payer", style_label), Paragraph(pol_payer, style_val),
            Paragraph("Policy Version", style_label), Paragraph(pol_ver, style_val)
        ]
    ]

    policy_table = Table(policy_grid_data, colWidths=[100, 143, 100, 144])
    policy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(policy_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 8. POLICY CRITERIA / EVALUATION TABLE
    # ---------------------------------------------------------
    story.append(Paragraph("POLICY EVALUATION", style_section_heading))

    criteria_table_data = [
        [
            Paragraph("Criterion", style_cell_header),
            Paragraph("Status", style_cell_header),
            Paragraph("Reason / Clinical Finding", style_cell_header)
        ]
    ]

    passed_count = 0
    failed_count = 0
    na_count = 0

    if criteria_list:
        for item in criteria_list:
            c_name = clean_txt(item.get("criterion") or item.get("name") or item.get("criterion_name"), "Criterion")
            c_status_raw = str(item.get("status") or item.get("result") or ("PASSED" if item.get("satisfied") else "FAILED")).upper()
            c_reason = clean_txt(item.get("reason") or item.get("details"), "Evaluation completed.")

            if "PASS" in c_status_raw or c_status_raw == "TRUE":
                status_p = Paragraph("<font color=\"#16A34A\"><b>✓ PASSED</b></font>", style_body)
                passed_count += 1
            elif "FAIL" in c_status_raw or c_status_raw == "FALSE":
                status_p = Paragraph("<font color=\"#DC2626\"><b>✕ FAILED</b></font>", style_body)
                failed_count += 1
            else:
                status_p = Paragraph("<font color=\"#64748B\">N/A</font>", style_body)
                na_count += 1

            criteria_table_data.append([
                Paragraph(c_name, style_body_bold),
                status_p,
                Paragraph(c_reason, style_body)
            ])
    else:
        # Fallback if no detailed criteria list present
        failed_list = decision_info.get("failed_criteria") or []
        if failed_list:
            for f_item in failed_list:
                criteria_table_data.append([
                    Paragraph("Clinical Policy Requirement", style_body_bold),
                    Paragraph("<font color=\"#DC2626\"><b>✕ FAILED</b></font>", style_body),
                    Paragraph(clean_txt(f_item), style_body)
                ])
                failed_count += 1
            passed_count = max(0, 5 - failed_count)
        else:
            criteria_table_data.append([
                Paragraph("Clinical Coverage Guidelines", style_body_bold),
                Paragraph("<font color=\"#16A34A\"><b>✓ PASSED</b></font>", style_body),
                Paragraph("All required clinical coverage criteria were evaluated and met.", style_body)
            ])
            passed_count = 1

    total_criteria = len(criteria_table_data) - 1

    eval_table = Table(criteria_table_data, colWidths=[140, 90, 257])
    eval_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(eval_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 9. FINAL DECISION SECTION (PROMINENT BANNER)
    # ---------------------------------------------------------
    story.append(Paragraph("FINAL DECISION", style_section_heading))

    if not is_verification_passed or final_decision_raw == "DOCUMENT VERIFICATION FAILED":
        dec_symbol = "✕"
        dec_title = "DOCUMENT VERIFICATION FAILED"
        dec_desc = "Identity verification between submitted documents failed. Authorization processing was stopped."
        dec_bg = colors.HexColor("#FEF2F2")
        dec_border = colors.HexColor("#FECACA")
        dec_fg = colors.HexColor("#B91C1C")
    elif "AUTO" in final_decision_raw or "NO_PRIOR_AUTH" in final_decision_raw or final_decision_raw == "NO PRIOR AUTH REQUIRED":
        dec_symbol = "✓"
        dec_title = "NO PRIOR AUTHORIZATION REQUIRED"
        dec_desc = "The requested procedure code is exempt from prior authorization guidelines under the active policy."
        dec_bg = colors.HexColor("#EFF6FF")
        dec_border = colors.HexColor("#BFDBFE")
        dec_fg = colors.HexColor("#1D4ED8")
    elif "APPROV" in final_decision_raw:
        dec_symbol = "✓"
        dec_title = "APPROVED"
        dec_desc = "All required authorization criteria were satisfied."
        dec_bg = colors.HexColor("#F0FDF4")
        dec_border = colors.HexColor("#BBF7D0")
        dec_fg = colors.HexColor("#15803D")
    elif "DENI" in final_decision_raw:
        dec_symbol = "✕"
        dec_title = "DENIED"
        dec_desc = "Required authorization criteria were not satisfied."
        dec_bg = colors.HexColor("#FEF2F2")
        dec_border = colors.HexColor("#FECACA")
        dec_fg = colors.HexColor("#B91C1C")
    else: # MANUAL REVIEW
        dec_symbol = "⚠"
        dec_title = "MANUAL REVIEW"
        dec_desc = "Additional clinical review is required by a medical director or specialist."
        dec_bg = colors.HexColor("#FFFBEB")
        dec_border = colors.HexColor("#FDE68A")
        dec_fg = colors.HexColor("#B45309")

    # Override description with actual decision reason if available
    custom_reason = decision_info.get("reason")
    if custom_reason and len(custom_reason.strip()) > 5 and not not is_verification_passed:
        dec_desc = clean_txt(custom_reason)

    decision_banner_data = [
        [
            Paragraph(f"<font size=\"18\" color=\"{dec_fg.hexval()}\"><b>{dec_symbol} {dec_title}</b></font>", styles['Normal']),
        ],
        [
            Paragraph(f"<font size=\"10\" color=\"#334155\">{dec_desc}</font>", styles['Normal'])
        ]
    ]

    decision_banner_table = Table(decision_banner_data, colWidths=[487])
    decision_banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), dec_bg),
        ('BOX', (0, 0), (-1, -1), 1.5, dec_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
    ]))
    story.append(decision_banner_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 10. DECISION SUMMARY & CRITERIA SUMMARY
    # ---------------------------------------------------------
    story.append(Paragraph("DECISION SUMMARY", style_section_heading))

    if not is_verification_passed:
        summary_text = (
            "The authorization request could not be processed due to a document identity mismatch "
            "between the Patient History PDF and the PA Request Form PDF. "
            "Verification stopped downstream policy evaluation."
        )
    else:
        summary_text = (
            f"The authorization request was evaluated against the applicable coverage policy ({pol_name}). "
            f"<b>{passed_count} of {total_criteria}</b> required criteria were satisfied."
        )

    story.append(Paragraph(summary_text, style_body))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>CRITERIA SUMMARY</b>", style_label))
    summary_metrics_data = [
        [
            Paragraph("Total Criteria", style_label), Paragraph(str(total_criteria), style_body_bold),
            Paragraph("Passed", style_label), Paragraph(f"<font color=\"#16A34A\">{passed_count}</font>", style_body_bold),
            Paragraph("Failed", style_label), Paragraph(f"<font color=\"#DC2626\">{failed_count}</font>", style_body_bold),
            Paragraph("Not Applicable", style_label), Paragraph(str(na_count), style_body_bold)
        ]
    ]

    metrics_table = Table(summary_metrics_data, colWidths=[80, 41, 60, 61, 60, 61, 80, 44])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 11. REPORT INFORMATION (METADATA)
    # ---------------------------------------------------------
    story.append(Paragraph("REPORT INFORMATION", style_section_heading))

    meta_grid_data = [
        [
            Paragraph("Request ID", style_label), Paragraph(req_id, style_val),
            Paragraph("Evaluation Date", style_label), Paragraph(report_date_str, style_val)
        ],
        [
            Paragraph("Evaluation Time", style_label), Paragraph(report_time_str, style_val),
            Paragraph("Policy ID", style_label), Paragraph(pol_id, style_val)
        ],
        [
            Paragraph("Policy Version", style_label), Paragraph(pol_ver, style_val),
            Paragraph("System", style_label), Paragraph("PriorAuth AI System v1.0", style_val)
        ]
    ]

    meta_table = Table(meta_grid_data, colWidths=[100, 143, 100, 144])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer.getvalue()
