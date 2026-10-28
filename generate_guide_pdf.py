import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

# -------------------------------------------------------------
# NUMBERED CANVAS (Page X of Y & Clean Header/Footer)
# -------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
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

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 8.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running header on pages 2+
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "RetinaScan - AI Diabetic Retinopathy Screening System Manual")
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "Clinical User Guide")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer on all pages
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(8.5 * inch - 54, 34, page_str)
        self.drawString(54, 34, "CONFIDENTIAL & MEDICAL AI EVALUATION REFERENCE - v1.2.0")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, 46, 8.5 * inch - 54, 46)

        self.restoreState()


def build_pdf(output_path):
    pdf = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Brand Colors
    c_primary = colors.HexColor("#0F6E73")
    c_primary_dark = colors.HexColor("#0A4E52")
    c_dark = colors.HexColor("#0E2A33")
    c_muted = colors.HexColor("#475569")
    c_card_bg = colors.HexColor("#F8FAFC")
    c_border = colors.HexColor("#CBD5E1")

    # Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=c_dark,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=c_primary,
        spaceAfter=12,
    )

    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=c_dark,
    )

    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_muted,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=c_dark,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=c_primary_dark,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=c_dark,
        spaceAfter=6,
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4,
    )

    callout_style = ParagraphStyle(
        "Callout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12.5,
        textColor=c_muted,
    )

    code_block = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # -------------------------------------------------------------
    # HEADER BANNER
    # -------------------------------------------------------------
    story.append(Paragraph("RetinaScan: AI Retinal Screening Suite", title_style))
    story.append(
        Paragraph(
            "Diabetic Retinopathy Classification, Explainable AI (Grad-CAM), and User Guide",
            subtitle_style,
        )
    )

    # Metadata Specification Box
    meta_table = Table(
        [
            [
                Paragraph("<b>System Name:</b> RetinaScan Clinical Suite", meta_label),
                Paragraph("<b>Frontend Framework:</b> React 18, Vite, DM Sans", meta_val),
            ],
            [
                Paragraph("<b>Version:</b> 1.2.0 (Deep Learning + Explainable AI)", meta_label),
                Paragraph("<b>Backend API:</b> FastAPI, Uvicorn, Python 3.12", meta_val),
            ],
            [
                Paragraph("<b>Core Model:</b> EfficientNet-B0 (5-Class ETDRS)", meta_label),
                Paragraph("<b>Explainability:</b> Grad-CAM (tf.GradientTape)", meta_val),
            ],
            [
                Paragraph("<b>Target Input:</b> Digital Retinal Fundus (JPG / PNG)", meta_label),
                Paragraph("<b>Compliance:</b> International Clinical DR Scale", meta_val),
            ],
        ],
        colWidths=[240, 264],
    )
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SECTION 1: PROJECT OVERVIEW
    # -------------------------------------------------------------
    story.append(Paragraph("1. Project Overview & Clinical Objective", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=8))

    story.append(
        Paragraph(
            "<b>Diabetic Retinopathy (DR)</b> is the primary cause of preventable blindness in the working-age "
            "population worldwide. Microvascular damage induced by chronic hyperglycemia triggers retinal ischemia, "
            "microaneurysms, hemorrhages, and neovascular proliferation. Early detection and staging are essential "
            "to prevent irreversible visual impairment.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "<b>RetinaScan</b> is a medical AI screening platform that bridges clinical ophthalmology with deep learning. "
            "It accepts digital retinal fundus photography, performs automated 5-class severity grading matching the "
            "international Early Treatment Diabetic Retinopathy Study (ETDRS) standard, and delivers <b>Explainable AI (Grad-CAM)</b> "
            "activation maps showing clinicians the exact anatomical lesions behind every prediction.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # -------------------------------------------------------------
    # SECTION 2: COMPLETE FEATURES BREAKDOWN
    # -------------------------------------------------------------
    story.append(Paragraph("2. Comprehensive Feature Breakdown", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=8))

    feat_data = [
        [
            Paragraph("<b>Feature Module</b>", body_bold),
            Paragraph("<b>Functional Description</b>", body_bold),
            Paragraph("<b>Clinical Value</b>", body_bold),
        ],
        [
            Paragraph("<b>1. Clinician Authentication & Field Validation</b>", body_style),
            Paragraph("Dual-mode (Sign In / Register) interface with RFC-compliant email regex checking, password complexity rules (letters & numbers, 6+ chars), interactive strength meter, password visibility toggle, and instant 'Auto Fill' demo credentials.", body_style),
            Paragraph("Prevents unauthorized access, enforces secure passwords, and enables instantaneous 1-click clinical testing.", body_style),
        ],
        [
            Paragraph("<b>2. High-Resolution Fundus Uploader</b>", body_style),
            Paragraph("Drag-and-drop and manual file selector with client-side MIME validation (JPG, JPEG, PNG) and strict 10MB payload size restriction.", body_style),
            Paragraph("Eliminates corrupt or unsupported image submissions prior to inference.", body_style),
        ],
        [
            Paragraph("<b>3. 5-Stage ETDRS Classification</b>", body_style),
            Paragraph("Classifies retinal fundus into 5 clinically recognized stages: No DR (Level 0), Mild NPDR (Level 1), Moderate NPDR (Level 2), Severe NPDR (Level 3), and Proliferative DR (Level 4).", body_style),
            Paragraph("Standardized diagnostic staging aligned with international ophthalmic referral guidelines.", body_style),
        ],
        [
            Paragraph("<b>4. Explainable AI: Grad-CAM Heatmaps</b>", body_style),
            Paragraph("Visual gradient-weighted class activation mapping computed from the EfficientNet top convolutional layer. Features 3 viewing modes (Overlay, Side-by-Side, Original), a live 0-100% Opacity Slider, and a color spectrum legend.", body_style),
            Paragraph("Eliminates 'black-box' opacity; clinicians can visually cross-verify AI attention against actual hemorrhages and exudates.", body_style),
        ],
        [
            Paragraph("<b>5. 5-Class Softmax Probability Chart</b>", body_style),
            Paragraph("Horizontal meter breakdown illustrating exact probability percentages for all 5 stages with color-coded severity badges and a highlighted 'Primary Match' tag.", body_style),
            Paragraph("Reveals model confidence distribution; alerts clinicians to borderline multi-stage findings.", body_style),
        ],
        [
            Paragraph("<b>6. Clinical Action Guidance Engine</b>", body_style),
            Paragraph("Dynamic protocol recommendations for each stage (e.g. routine yearly follow-up for Level 0 vs. emergency retina specialist referral within days for Level 4).", body_style),
            Paragraph("Provides clear, evidence-based triage instructions for primary care clinicians.", body_style),
        ],
        [
            Paragraph("<b>7. Screening Session History</b>", body_style),
            Paragraph("Local audit table storing recent evaluations, image identifiers, predicted stages, confidence ratings, and timestamps with 1-click history clearance.", body_style),
            Paragraph("Facilitates longitudinal comparison and patient record keeping during eye camp screenings.", body_style),
        ],
    ]

    feat_table = Table(feat_data, colWidths=[120, 240, 144])
    feat_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F6E73")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, c_border),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_card_bg]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(feat_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SECTION 3: SYSTEM ARCHITECTURE & DATA FLOW
    # -------------------------------------------------------------
    story.append(Paragraph("3. System Architecture & Technical Workflow", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=8))

    story.append(
        Paragraph(
            "The diagram and steps below detail the end-to-end data processing pipeline from "
            "the React client browser to the FastAPI neural inference engine:",
            body_style,
        )
    )

    arch_steps = [
        "<b>1. Client Upload & Validation:</b> The React application validates file format and size, generates a client-side object preview URL, and dispatches an asynchronous HTTP POST multipart/form-data request to <code>http://localhost:8000/predict</code>.",
        "<b>2. Preprocessing & Bilinear Resampling:</b> The FastAPI service receives the raw byte stream, validates the image buffer via Pillow, converts to 3-channel RGB, and performs bilinear interpolation to dimensions (224, 224, 3) followed by float32 batch expansion.",
        "<b>3. Neural Feature Extraction:</b> The image passes through the EfficientNet-B0 backbone. Convolutional feature maps capture vascular patterns, microaneurysms, and retinal lesions across 16 mobile inverted bottleneck convolution (MBConv) stages.",
        "<b>4. Classification Head & Softmax Distribution:</b> The feature representations pass through Global Average Pooling (1280 dims), Batch Normalization, Dropout, Dense (256 units), and a final 5-unit Softmax Dense layer to yield class probability distribution P(C).",
        "<b>5. Grad-CAM Explainable AI Computation:</b> Using <code>tf.GradientTape</code>, the engine watches activations A^k of the final convolutional layer (<code>top_conv</code>) and computes gradients wrt the predicted class score y^c. The channel weights alpha_k = mean(grad) are pooled, and the rectified linear combination L_GradCAM = ReLU(sum(alpha_k * A^k)) is computed and mapped via Matplotlib JET colormap.",
        "<b>6. Alpha Blending & Base64 Response:</b> The 2D heatmap is resized to the exact dimensions of the uploaded image and blended at 42% alpha. Both the blended overlay and the raw heatmap are base64-encoded and returned inside a JSON payload.",
    ]

    for step in arch_steps:
        story.append(Paragraph(f"• {step}", bullet_style))

    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SECTION 4: STEP-BY-STEP USER WALKTHROUGH
    # -------------------------------------------------------------
    story.append(Paragraph("4. Step-by-Step User Instructions (How to Run & Use)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=8))

    guide_steps = [
        ("Step 1: Launch Backend & Frontend Servers", [
            "Open two separate terminal windows (PowerShell or Command Prompt) and execute:",
            "<b>Terminal 1 (FastAPI Neural Backend):</b><br/>"
            "<code>cd e:\\amount_project\\diapatic_detection\\diapatic_detection\\diapatic_detection\\backend<br/>"
            "python -m uvicorn main:app --reload --port 8000</code>",
            "<b>Terminal 2 (React Vite Frontend):</b><br/>"
            "<code>cd e:\\amount_project\\diapatic_detection\\diapatic_detection\\diapatic_detection\\dr-frontend<br/>"
            "npm run dev</code>",
        ]),
        ("Step 2: Access the Application", [
            "Open any modern web browser (Google Chrome, Microsoft Edge, or Mozilla Firefox) and navigate to:<br/>"
            "<b>http://localhost:5173</b>",
        ]),
        ("Step 3: Clinician Authentication & Sign In", [
            "<b>Option A (Fast 1-Click Demo):</b> Click the <b>'Auto Fill'</b> button on the login card. Demo credentials (<code>doctor@retinascan.ai</code> / <code>Password123</code>) will populate automatically. Click <b>'Sign In'</b>.",
            "<b>Option B (Account Registration):</b> Click <b>'Create Account'</b> tab. Enter your full name, valid email address, and a secure password (minimum 6 characters with both letters and numbers). Confirm password and click <b>'Create Account'</b>.",
            "<b>Real-Time Validation:</b> If an invalid email format or short password is entered, immediate field-level error messages will display below the input.",
        ]),
        ("Step 4: Uploading a Retinal Fundus Scan", [
            "On the Screening Dashboard, locate the left card titled <b>'Upload Retinal Fundus Image'</b>.",
            "Drag and drop any standard fundus photograph into the dashed drop area, or click within the box to select a file from your hard drive.",
            "Supported formats: <b>JPG, JPEG, PNG</b> (up to 10 MB). An instant image preview will render.",
        ]),
        ("Step 5: Execute Inference & Interpret Results", [
            "Click the primary button <b>'Run Diagnostic Analysis'</b>.",
            "Within 1 to 2 seconds, the engine generates the complete clinical report on the right:",
            "<b>1. Condition Verdict:</b> Primary predicted stage (e.g. <i>Moderate NPDR</i>) and severity level badge (Level 0 to 4).",
            "<b>2. Explainable AI Heatmap (Grad-CAM):</b> Toggle between <b>[Overlay]</b>, <b>[Side-by-Side]</b>, and <b>[Original]</b>. In Overlay mode, drag the <b>Opacity Slider (0-100%)</b> to examine underlying blood vessels and microaneurysms under the heat map.",
            "<b>3. 5-Class Probability Meter:</b> View the exact confidence percentage for each stage on the animated horizontal bar chart.",
            "<b>4. Suggested Action:</b> Review recommended ophthalmic follow-up timeframe.",
            "<b>5. History Log:</b> The scan is recorded in the bottom table with timestamp for audit.",
        ]),
    ]

    for title, substeps in guide_steps:
        story.append(Paragraph(title, h2_style))
        for sub in substeps:
            story.append(Paragraph(sub, body_style))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SECTION 5: CLINICAL SEVERITY GRADING REFERENCE TABLE
    # -------------------------------------------------------------
    story.append(Paragraph("5. International ETDRS Clinical Severity Scale", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=8))

    etdrs_data = [
        [
            Paragraph("<b>Level</b>", body_bold),
            Paragraph("<b>Clinical Stage</b>", body_bold),
            Paragraph("<b>Ophthalmic Pathological Findings</b>", body_bold),
            Paragraph("<b>Action Protocol</b>", body_bold),
        ],
        [
            Paragraph("<font color='#2f9e6b'><b>Level 0</b></font>", body_style),
            Paragraph("<b>No DR</b>", body_style),
            Paragraph("No retinal vascular abnormalities detected. Normal optic disc and macula.", body_style),
            Paragraph("Routine annual eye screening; maintain glycemic control.", body_style),
        ],
        [
            Paragraph("<font color='#9bb52f'><b>Level 1</b></font>", body_style),
            Paragraph("<b>Mild NPDR</b>", body_style),
            Paragraph("Microaneurysms only. Tiny pouch-like dilations in retinal capillary walls.", body_style),
            Paragraph("Ophthalmologist review within 6 to 12 months; control BP and lipids.", body_style),
        ],
        [
            Paragraph("<font color='#e0a526'><b>Level 2</b></font>", body_style),
            Paragraph("<b>Moderate NPDR</b>", body_style),
            Paragraph("Multiple microaneurysms, dot-and-blot hemorrhages, venous loops, and hard exudates.", body_style),
            Paragraph("Comprehensive eye examination within 3 to 6 months.", body_style),
        ],
        [
            Paragraph("<font color='#e0692a'><b>Level 3</b></font>", body_style),
            Paragraph("<b>Severe NPDR</b>", body_style),
            Paragraph("4-2-1 Rule: Intraretinal hemorrhages in 4 quadrants, venous beading in 2+ quadrants, or IRMA in 1+ quadrant.", body_style),
            Paragraph("Prompt retina specialist evaluation within weeks; evaluate for anti-VEGF therapy.", body_style),
        ],
        [
            Paragraph("<font color='#cf3a3a'><b>Level 4</b></font>", body_style),
            Paragraph("<b>Proliferative DR</b>", body_style),
            Paragraph("Neovascularization of the disc (NVD) or retina (NVE), vitreous/preretinal hemorrhage.", body_style),
            Paragraph("URGENT intervention within days (Panretinal Photocoagulation / Vitrectomy) to prevent vision loss.", body_style),
        ],
    ]

    etdrs_table = Table(etdrs_data, colWidths=[55, 95, 204, 150])
    etdrs_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0E2A33")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, c_border),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_card_bg]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(etdrs_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SECTION 6: TROUBLESHOOTING & FAQ
    # -------------------------------------------------------------
    story.append(Paragraph("6. Frequently Asked Questions & Troubleshooting", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=8))

    faqs = [
        ("Q: What causes 'Cannot reach backend at http://localhost:8000'?",
         "A: The FastAPI server is not currently running. Open a terminal and run 'python -m uvicorn main:app --reload --port 8000'."),
        ("Q: What if login reports 'Invalid email or password'?",
         "A: Use the convenient 'Auto Fill' button to load the preconfigured demo clinician credentials (doctor@retinascan.ai / Password123) or create a new account using the 'Create Account' tab."),
        ("Q: How does the Grad-CAM Heatmap help clinicians?",
         "A: The red and warm-spectrum zones highlight regions where the deep learning model identified high-activation pathology (such as exudates or hemorrhages). The blue and cool zones represent normal background tissue."),
        ("Q: Is RetinaScan an autonomous diagnostic tool?",
         "A: No. RetinaScan is an AI-assisted diagnostic support tool. Final clinical diagnosis and treatment plans must always be confirmed by a licensed ophthalmologist or retinal specialist."),
    ]

    for q, a in faqs:
        story.append(Paragraph(f"<b>{q}</b>", body_style))
        story.append(Paragraph(a, callout_style))
        story.append(Spacer(1, 3))

    # Build the document
    pdf.build(story, canvasmaker=NumberedCanvas)
    print(f"Flawless English PDF generated successfully at: {output_path}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "RetinaScan_User_Guide.pdf"
    build_pdf(out)
