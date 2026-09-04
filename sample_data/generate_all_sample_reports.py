import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)

def create_report_canvas(output_path: Path, title: str, subtitle: str, patient_meta: list, sections: list):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom Medical Styling
    header_style = ParagraphStyle(
        'ClinicHeader',
        parent=styles['Heading1'],
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    sub_header = ParagraphStyle(
        'ClinicSub',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569'),
        fontName='Helvetica'
    )
    sec_title = ParagraphStyle(
        'SecTitle',
        parent=styles['Heading2'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0284C7'),
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=4
    )
    body_text = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor('#1E293B')
    )
    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#64748B'),
        fontName='Helvetica-Bold'
    )
    meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica'
    )

    elements = []

    # Hospital Header Banner
    elements.append(Paragraph("<b>ST. JUDE NEUROLOGICAL INSTITUTE & ADVANCED BRAIN CLINIC</b>", header_style))
    elements.append(Paragraph(f"<b>Department of Clinical Neuroscience</b> • {subtitle}", sub_header))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0284C7'), spaceAfter=8))

    # Patient Demographic Grid
    grid_rows = []
    for row in patient_meta:
        grid_rows.append([
            Paragraph(f"<b>{row[0]}</b>", meta_label), Paragraph(str(row[1]), meta_val),
            Paragraph(f"<b>{row[2]}</b>", meta_label), Paragraph(str(row[3]), meta_val)
        ])

    meta_table = Table(grid_rows, colWidths=[100, 165, 100, 165])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.extend([meta_table, Spacer(1, 10)])

    # Sections
    for s_title, s_content in sections:
        elements.append(Paragraph(s_title.upper(), sec_title))
        elements.append(Paragraph(s_content, body_text))
        elements.append(Spacer(1, 6))

    # Footer note
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=6))
    elements.append(Paragraph(
        "<i>CONFIDENTIAL MEDICAL RECORD • Generated for Clinical Workflow Intelligence Platform review. Verified by attending specialist.</i>",
        ParagraphStyle('Foot', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#94A3B8'))
    ))

    doc.build(elements)
    print(f"-> Generated: {output_path}")

def generate_all_samples(base_dir: Path):
    sample_dir = base_dir / "sample_data"
    sample_dir.mkdir(parents=True, exist_ok=True)

    # 1. Eleanor Vance (PT-8942) - Epilepsy Evaluation
    create_report_canvas(
        sample_dir / "patient_report_01.pdf",
        "Eleanor Vance",
        "Comprehensive Video-EEG Telemetry & Surgical Resection Assessment",
        [
            ["Patient Name:", "Eleanor Vance", "Patient Code / MRN:", "PT-8942"],
            ["Date of Birth:", "1970-04-12 (Age 54)", "Gender:", "Female"],
            ["Primary Diagnosis:", "Refractory Temporal Lobe Epilepsy", "Attending Physician:", "Dr. Sarah Jenkins, MD"],
            ["Evaluation Date:", "2026-08-18", "Admission Unit:", "Epilepsy Monitoring Unit (EMU)"]
        ],
        [
            ("Chief Complaint & History of Present Illness",
             "Patient Eleanor Vance is a 54-year-old female with a 3-year history of medically refractory focal impaired awareness seizures with temporal lobe semiology. Seizure manifestations consist of stereotypic olfactory auras (burnt rubber sensation) accompanied by epigastric rising, followed by behavioral arrest, left-handed fidgeting, and oro-alimentary automatisms lasting 60–90 seconds with post-ictal speech disturbance."),
            ("Antiseizure Polytherapy & Medical History",
             "Current Antiseizure Medications: Levetiracetam (Keppra) 1500 mg PO BID, Lamotrigine 200 mg PO BID, Lisinopril 10 mg daily for hypertension.<br/>Allergies: Penicillin (severe anaphylaxis and angioedema).<br/>Past Medical History: Essential Hypertension (controlled, BP 124/78 mmHg)."),
            ("Long-Term Continuous Video-EEG Findings (72-Hour Telemetry)",
             "• Baseline Background: Continuous symmetrical 9.5 Hz posterior dominant alpha rhythm.<br/>"
             "• Interictal Abnormalities: Frequent epileptiform sharp and slow wave discharges localized exclusively to the left anterior-mesial temporal electrodes (F7-T3, T3-T5).<br/>"
             "• Ictal Recordings: Two stereotypic electroclinical seizures captured. Ictal onset demonstrated rhythmic 5 Hz theta activity originating from the left mesial temporal region, confirming definitive electroclinical concordance."),
            ("Neuropsychological & Laboratory Panel",
             "• Laboratory Panel: Serum sodium 139 mEq/L, potassium 4.1 mEq/L, BUN 14 mg/dL, creatinine 0.85 mg/dL, AST 22 U/L, ALT 24 U/L, WBC 6.8 x10^3/uL, Platelets 242 x10^3/uL.<br/>"
             "• Neuropsychology: Mild verbal memory encoding deficit with intact visual-spatial perception and preserved executive reasoning."),
            ("Multidisciplinary Assessment & Surgical Recommendations",
             "Multidisciplinary Epilepsy Surgical Conference consensus recommends patient as an excellent candidate for left anterior temporal lobectomy or stereotactic Laser Interstitial Thermal Therapy (LITT) given complete electroclinical concordance. Scheduled for surgical planning consultation in 4 weeks.")
        ]
    )

    # 2. Robert Langdon (PT-3108) - Acute Ischemic Stroke
    create_report_canvas(
        sample_dir / "patient_report_02.pdf",
        "Robert Langdon",
        "Acute Ischemic Stroke & Neuro-Rehabilitation Discharge Summary",
        [
            ["Patient Name:", "Robert Langdon", "Patient Code / MRN:", "PT-3108"],
            ["Date of Birth:", "1962-09-18 (Age 62)", "Gender:", "Male"],
            ["Primary Diagnosis:", "Acute Left MCA Ischemic Infarction", "Attending Physician:", "Dr. Sarah Jenkins, MD"],
            ["Admit Date:", "2026-08-01", "Discharge Date:", "2026-08-14"]
        ],
        [
            ("Clinical Presentation & Emergent Management",
             "62-year-old male admitted through Emergency Department presenting with acute onset right-sided hemiparesis, facial droop, and expressive motor dysphasia starting 90 minutes prior to arrival (Last Known Normal: 08:30 AM). Initial NIHSS Score: 14. Emergency CT perfusion and angiogram confirmed acute thrombus in the left middle cerebral artery (M1 branch). Intravenous thrombolysis (Alteplase 0.9 mg/kg) administered within therapeutic window, followed by successful mechanical thrombectomy with TICI 3 complete reperfusion."),
            ("Diagnostic Findings & Vascular Evaluation",
             "• Brain MRI (Post-thrombectomy): Restricted diffusion in small left subcortical corona radiata, preserved cortical ribbon without hemorrhagic conversion.<br/>"
             "• Carotid Doppler Ultrasound: Left internal carotid artery with 35% non-stenotic calcified atheromatous plaque; right ICA normal.<br/>"
             "• Transthoracic Echocardiogram (TTE): Ejection fraction 58%, normal left ventricular systolic function, bubble study negative for patent foramen ovale (PFO)."),
            ("Hospital Course & Functional Recovery",
             "Patient made substantial motor improvement over 14-day hospitalization. Speech fluency improved with intensive speech-language pathology (SLP). Discharge NIHSS Score reduced to 2. Modified Rankin Scale (mRS) upon discharge: 1 (independent in basic activities of daily living)."),
            ("Discharge Medications & Secondary Stroke Prevention",
             "1. Aspirin 81 mg daily PO.<br/>"
             "2. Clopidogrel (Plavix) 75 mg daily PO (Dual Antiplatelet Therapy for 21 days).<br/>"
             "3. Atorvastatin (Lipitor) 80 mg daily at bedtime (Target LDL < 55 mg/dL).<br/>"
             "4. Amlodipine 5 mg daily PO.<br/>"
             "Follow-up scheduled with Comprehensive Stroke Clinic in 30 days with repeat lipid panel.")
        ]
    )

    # 3. Sophia Chen (PT-7721) - Multiple Sclerosis
    create_report_canvas(
        sample_dir / "patient_report_03.pdf",
        "Sophia Chen",
        "Relapsing-Remitting Multiple Sclerosis (RRMS) Comprehensive Evaluation",
        [
            ["Patient Name:", "Sophia Chen", "Patient Code / MRN:", "PT-7721"],
            ["Date of Birth:", "1981-11-25 (Age 44)", "Gender:", "Female"],
            ["Primary Diagnosis:", "Relapsing-Remitting MS (RRMS)", "Attending Physician:", "Dr. Sarah Jenkins, MD"],
            ["Evaluation Date:", "2026-08-22", "Clinic:", "Neuro-Immunology Center"]
        ],
        [
            ("Clinical Background & Symptom Review",
             "44-year-old female with established diagnosis of Relapsing-Remitting Multiple Sclerosis (RRMS) for 4 years. Patient reports current stability with resolved left optic neuritis episode from February 2026. Current complaints include intermittent bilateral lower extremity paresthesias (Lhermitte's sign positive) and moderate fatigue in the late afternoons. Expanded Disability Status Scale (EDSS): 2.0."),
            ("Neuro-Imaging & Cerebrospinal Fluid (CSF) Analysis",
             "• Brain MRI with IV Gadolinium: Stable chronic periventricular and juxtacortical T2/FLAIR hyperintense demyelinating lesions. No new active enhancing lesions demonstrating disease stabilization.<br/>"
             "• Cervical Spine MRI: Small non-enhancing lesion at C3-C4 dorsal column.<br/>"
             "• Lumbar Puncture CSF Findings: Elevated IgG index (0.88, normal < 0.70), 6 discrete oligoclonal bands present in CSF not mirrored in serum."),
            ("Disease-Modifying Therapy (DMT) & Tolerance",
             "Patient currently maintained on Ocrelizumab (Ocrevus) 600 mg IV infusion every 6 months. Serum B-cell (CD19/CD20) suppression verified (< 1% total lymphocytes). Pre-infusion JC virus antibody index is 0.22 (Low Risk for PML). Liver function tests and immunoglobulin G levels remain within normal reference ranges."),
            ("Plan & Management Directives",
             "Continue Ocrelizumab maintenance infusions every 24 weeks. Prescribed Amantadine 100 mg daily for MS-related fatigue. Routine physical therapy prescribed for gait optimization. Next scheduled MRI brain and cervical spine in 6 months.")
        ]
    )

    # 4. Marcus Thorne (PT-5519) - TBI & Craniotomy
    create_report_canvas(
        sample_dir / "patient_report_04.pdf",
        "Marcus Thorne",
        "Traumatic Brain Injury & Subdural Hematoma Evacuation Report",
        [
            ["Patient Name:", "Marcus Thorne", "Patient Code / MRN:", "PT-5519"],
            ["Date of Birth:", "1978-06-03 (Age 48)", "Gender:", "Male"],
            ["Primary Diagnosis:", "Right Acute-on-Chronic Subdural Hematoma", "Attending Physician:", "Dr. Sarah Jenkins, MD"],
            ["Procedure Date:", "2026-07-29", "Surgical Unit:", "Neuro-Surgical ICU"]
        ],
        [
            ("Trauma Summary & Surgical Intervention",
             "48-year-old male involved in high-impact motor vehicle collision presenting with GCS 11 (E3V3M5) and unequal pupillary response. Non-contrast head CT revealed a 14 mm acute-on-chronic right hemispheric subdural hematoma with 7 mm midline shift and uncal herniation risk. Emergent right fronto-temporoparietal craniotomy and hematoma evacuation performed successfully with intracranial pressure (ICP) monitor placement."),
            ("Post-Operative Neurological Course",
             "Post-operative ICP remained stable below 12 mmHg throughout ICU stay. Repeat CT scan at 48 hours confirmed complete hematoma decompression with resolution of midline shift. Patient extubated on post-op day 3. GCS improved to 15 (E4V5M6) with mild left pronator drift and transient memory processing lag."),
            ("Laboratory & Medication Management",
             "• Prophylactic Levetiracetam 1000 mg BID initiated for early post-traumatic seizure prevention (target 7-day course).<br/>"
             "• Coagulation Profile: INR 1.05, PTT 28 sec, Platelets 210 x10^3/uL.<br/>"
             "• Discharged to inpatient neuro-rehabilitation on post-op day 10."),
            ("Prognosis & Follow-Up",
             "Excellent functional trajectory. Skull bone flap well-healed without sign of infection. Scheduled for follow-up outpatient CT and cognitive reassessment in 6 weeks.")
        ]
    )

    # 5. Clara Oswald (PT-9204) - Parkinson's Disease & DBS
    create_report_canvas(
        sample_dir / "patient_report_05.pdf",
        "Clara Oswald",
        "Parkinson's Disease & Deep Brain Stimulation (DBS) Candidacy Dossier",
        [
            ["Patient Name:", "Clara Oswald", "Patient Code / MRN:", "PT-9204"],
            ["Date of Birth:", "1958-03-14 (Age 68)", "Gender:", "Female"],
            ["Primary Diagnosis:", "Idiopathic Parkinson's Disease (Stage III)", "Attending Physician:", "Dr. Sarah Jenkins, MD"],
            ["Evaluation Date:", "2026-08-30", "Clinic:", "Movement Disorders Center"]
        ],
        [
            ("Clinical Disease Trajectory & Medication Motor Fluctuations",
             "68-year-old female with 8-year history of idiopathic Parkinson's disease presenting with progressive motor fluctuations, 'wearing-off' phenomenon, and peak-dose dyskinesias limiting functional independence despite Carbidopa/Levodopa dose adjustments (taking 250/25 mg 5 times daily)."),
            ("Levodopa Challenge Test & UPDRS Scores",
             "• MDS-UPDRS Part III (Motor Score OFF Medication): 44 points (severe resting tremor, rigidity, bradykinesia).<br/>"
             "• MDS-UPDRS Part III (Motor Score ON Medication): 16 points (63.6% motor score improvement, demonstrating robust levodopa responsiveness, exceeding the 30% candidacy threshold for surgical DBS).<br/>"
             "• Neuropsychological Evaluation: MoCA Score 28/30, indicating absence of dementia or significant frontal-executive impairment."),
            ("Stereotactic Target Assessment",
             "High-resolution 3T MRI volumetric brain protocol completed without motion artifact. Subthalamic Nucleus (STN) bilaterally identified as the primary therapeutic target for bilateral DBS electrode implantation."),
            ("Multidisciplinary Surgical Decision",
             "Surgical board unanimously approves patient for bilateral STN Deep Brain Stimulation. Scheduled for staged frame-based bilateral lead placement next month.")
        ]
    )

if __name__ == "__main__":
    generate_all_samples(Path(__file__).resolve().parent.parent)
