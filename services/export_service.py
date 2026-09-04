import os
import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from config import Config
from models.report_model import Report, ReportStatus

class ExportService:
    @staticmethod
    def export_pdf(report: Report) -> Path:
        """
        Generates a clean, professional clinical intelligence summary PDF using ReportLab.
        """
        Config.EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
        pdf_filename = f"Clinical_Report_{report.patient.patient_code}_{report.id}.pdf"
        pdf_path = Config.EXPORT_FOLDER / pdf_filename

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=45,
            leftMargin=45,
            topMargin=45,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()
        
        # Custom typography styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0F172A'),
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#475569'),
            fontName='Helvetica'
        )
        section_heading = ParagraphStyle(
            'SectionHead',
            parent=styles['Heading2'],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#1E293B'),
            fontName='Helvetica-Bold',
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=15,
            textColor=colors.HexColor('#1E293B'),
            fontName='Helvetica'
        )
        meta_label = ParagraphStyle(
            'MetaLabel',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748B'),
            fontName='Helvetica-Bold'
        )
        meta_val = ParagraphStyle(
            'MetaVal',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#0F172A'),
            fontName='Helvetica'
        )
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#DC2626'),
            fontName='Helvetica-Oblique'
        )

        elements = []

        # 1. Header Banner
        header_text = Paragraph("<b>Clinical Workflow Intelligence Platform</b>", title_style)
        sub_text = Paragraph("Clinical Decision-Support Document Review & Verified Summary Report", subtitle_style)
        elements.extend([header_text, sub_text, Spacer(1, 10)])
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceAfter=14))

        # 2. Patient & Metadata Grid
        patient = report.patient
        meta_data = [
            [
                Paragraph("<b>Patient Name:</b>", meta_label), Paragraph(patient.display_name, meta_val),
                Paragraph("<b>Patient Code:</b>", meta_label), Paragraph(patient.patient_code, meta_val)
            ],
            [
                Paragraph("<b>Date of Birth:</b>", meta_label), Paragraph(patient.date_of_birth, meta_val),
                Paragraph("<b>Gender:</b>", meta_label), Paragraph(patient.gender or "N/A", meta_val)
            ],
            [
                Paragraph("<b>Condition:</b>", meta_label), Paragraph(patient.primary_condition or "N/A", meta_val),
                Paragraph("<b>Report ID:</b>", meta_label), Paragraph(f"REP-{report.id:04d}", meta_val)
            ],
            [
                Paragraph("<b>Review Status:</b>", meta_label), Paragraph(f"<b>{report.status}</b>", meta_val),
                Paragraph("<b>Date Generated:</b>", meta_label), Paragraph(report.created_at.strftime("%Y-%m-%d %H:%M UTC"), meta_val)
            ]
        ]
        
        meta_table = Table(meta_data, colWidths=[90, 170, 90, 170])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.extend([meta_table, Spacer(1, 14)])

        # 3. Clinical Question Queried
        elements.append(Paragraph("Clinical Information Query", section_heading))
        q_box = Table([[Paragraph(f"<i>\"{report.question}\"</i>", body_style)]], colWidths=[520])
        q_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F9FF')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BAE6FD')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        elements.extend([q_box, Spacer(1, 10)])

        # 4. Verified Clinical Answer & Summary
        elements.append(Paragraph("Grounded Summary & Clinical Findings", section_heading))
        answer_paragraphs = report.answer.split("\n")
        answer_formatted = "<br/>".join(answer_paragraphs)
        ans_box = Table([[Paragraph(answer_formatted, body_style)]], colWidths=[520])
        ans_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        elements.extend([ans_box, Spacer(1, 14)])

        # 5. Reviewer Sign-off & Audit Details
        if report.reviewer:
            elements.append(Paragraph("Clinical Review & Verification Sign-Off", section_heading))
            review_info = [
                [
                    Paragraph("<b>Verified By Clinician:</b>", meta_label),
                    Paragraph(f"{report.reviewer.name} ({report.reviewer.role})", meta_val),
                    Paragraph("<b>Approval Timestamp:</b>", meta_label),
                    Paragraph(report.approved_at.strftime("%Y-%m-%d %H:%M UTC") if report.approved_at else "Pending", meta_val)
                ]
            ]
            if report.reviewer_notes:
                review_info.append([
                    Paragraph("<b>Clinician Notes:</b>", meta_label),
                    Paragraph(report.reviewer_notes, meta_val),
                    Paragraph("", meta_label), Paragraph("", meta_val)
                ])
            rev_table = Table(review_info, colWidths=[120, 140, 110, 150])
            rev_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDF4')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#BBF7D0')),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            elements.extend([rev_table, Spacer(1, 14)])

        # 6. Source Document Citations
        if report.sources:
            elements.append(Paragraph("Audited Document Citations & Context Sources", section_heading))
            cite_rows = [
                [
                    Paragraph("<b>#</b>", meta_label),
                    Paragraph("<b>Source Document</b>", meta_label),
                    Paragraph("<b>Page / Section</b>", meta_label),
                    Paragraph("<b>Matched Excerpt</b>", meta_label)
                ]
            ]
            for idx, src in enumerate(report.sources[:5], 1):
                doc_title = src.get("document_filename", "Clinical Document")
                pg_sec = f"Pg {src.get('page_number', 1)} | {src.get('section_title', 'Section')}"
                snippet = src.get("snippet", "")[:120] + "..."
                cite_rows.append([
                    Paragraph(str(idx), meta_val),
                    Paragraph(doc_title, meta_val),
                    Paragraph(pg_sec, meta_val),
                    Paragraph(snippet, meta_val)
                ])

            cite_table = Table(cite_rows, colWidths=[20, 130, 120, 250])
            cite_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            elements.extend([cite_table, Spacer(1, 16)])

        # 7. Safety & Decision Support Disclaimer
        disclaimer_text = (
            "<b>REGULATORY & CLINICAL SAFETY NOTICE:</b> This document is generated by the Clinical Workflow Intelligence Platform "
            "solely as a decision-support and workflow review aid. It does NOT constitute autonomous medical advice, automated disease diagnosis, "
            "or treatment recommendation. All summarized clinical facts must be corroborated by licensed medical personnel against original patient files."
        )
        disc_box = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[520])
        disc_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#FCA5A5')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.extend([Spacer(1, 10), disc_box])

        # Build PDF
        doc.build(elements)
        return pdf_path

    @staticmethod
    def export_json(report: Report) -> Dict[str, Any]:
        """Generates structured JSON bundle for FHIR / EHR integration."""
        return {
            "platform": "Clinical Workflow Intelligence Platform",
            "report_id": report.id,
            "patient": report.patient.to_dict(),
            "query": report.question,
            "grounded_answer": report.answer,
            "raw_answer": report.raw_answer,
            "status": report.status,
            "is_grounded": report.is_grounded,
            "sources": report.sources,
            "reviewed_by": report.reviewer.name if report.reviewer else None,
            "reviewer_role": report.reviewer.role if report.reviewer else None,
            "reviewer_notes": report.reviewer_notes,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "approved_at": report.approved_at.isoformat() if report.approved_at else None,
            "disclaimer": "Clinical decision-support aid only. Not a diagnostic tool or clinician replacement."
        }
