from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_patient_report_01(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    sec_style = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0284C7'),
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )

    elements = []

    # Header
    elements.append(Paragraph("<b>ST. JUDE NEUROLOGICAL INSTITUTE</b>", title_style))
    elements.append(Paragraph("Comprehensive Clinical Evaluation & Discharge Summary", styles['Normal']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceAfter=10))

    # Patient Meta
    meta = [
        ["Patient Name: Eleanor Vance", "MRN / Code: PT-8942", "DOB: 1970-04-12 (Age 54)"],
        ["Admit Date: 2026-08-10", "Discharge Date: 2026-08-18", "Attending: Dr. Sarah Jenkins, MD"]
    ]
    t = Table(meta, colWidths=[200, 160, 170])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
    ]))
    elements.extend([t, Spacer(1, 10)])

    # Clinical Sections
    elements.append(Paragraph("CHIEF COMPLAINT & PRESENT ILLNESS", sec_style))
    elements.append(Paragraph(
        "Patient Eleanor Vance is a 54-year-old female presenting with a 3-year history of medically refractory focal impaired awareness seizures with temporal lobe semiology. Patient reports experiencing stereotypic olfactory auras (burnt rubber odor) followed by behavioral arrest and manual automatisms lasting 60 to 90 seconds, occurring 3 to 4 times per month despite dual anti-seizure polytherapy.",
        body_style
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("PAST MEDICAL HISTORY & MEDICATIONS", sec_style))
    elements.append(Paragraph(
        "1. Refractory Temporal Lobe Epilepsy (diagnosed 2023).<br/>"
        "2. Essential Hypertension (well controlled).<br/>"
        "3. Current Medications: Levetiracetam (Keppra) 1500 mg BID, Lamotrigine 200 mg BID, Lisinopril 10 mg daily.<br/>"
        "4. Allergies: Penicillin (severe urticaria/anaphylaxis).",
        body_style
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("LABORATORY AND DIAGNOSTIC FINDINGS", sec_style))
    elements.append(Paragraph(
        "• Comprehensive Metabolic Panel (CMP): Serum sodium 139 mEq/L, potassium 4.1 mEq/L, creatinine 0.85 mg/dL, AST 22 U/L, ALT 24 U/L.<br/>"
        "• Complete Blood Count (CBC): WBC 6.8 x10^3/uL, Hemoglobin 13.6 g/dL, Platelets 242 x10^3/uL.<br/>"
        "• Long-Term Video-EEG Monitoring (72h): Interictal discharges revealed frequent left anterior temporal sharp and slow wave complexes. Two stereotypic focal electrographic seizures recorded originating from the left mesial temporal region.<br/>"
        "• Neuropsychological Evaluation: Mild left verbal memory encoding deficit with preserved visuospatial performance and intact executive functioning.",
        body_style
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("ASSESSMENT, CLINICAL COURSE AND RECOMMENDATIONS", sec_style))
    elements.append(Paragraph(
        "The patient demonstrated consistent electro-clinical concordance localized to the left mesial temporal lobe. Given medical intractability following failure of two first-line antiseizure medications at target doses, multidisciplinary epilepsy surgical conference recommends evaluation for anterior temporal lobectomy or stereotactic laser interstitial thermal therapy (LITT).<br/>"
        "Discharged in stable neurological condition. Follow-up consultation scheduled in 4 weeks for surgical planning.",
        body_style
    ))

    doc.build(elements)
    print(f"Generated sample PDF at: {output_path}")

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "patient_report_01.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_patient_report_01(out)
