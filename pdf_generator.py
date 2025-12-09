import os
import datetime as dt
import json
from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import uuid

# Define PDF Class here to be self-contained
class PDF(FPDF):
    def header(self):
        # We handle custom headers execution-side or simple default
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def sanitize_text(self, text):
        if not isinstance(text, str):
            text = str(text)
        # Check if we have a unicode font loaded (OpenSans or TamilFont)
        # If so, return text as-is (fpdf2 handles unicode)
        if hasattr(self, 'font_family') and (self.font_family in ["OpenSans", "TamilFont", "Nirmala"]):
             return text
             
        # Fallback for core fonts
        return text.encode('latin-1', 'ignore').decode('latin-1')

    def cell(self, w, h=0, txt='', border=0, ln=0, align='', fill=False, link=''):
        txt = self.sanitize_text(txt)
        super().cell(w, h, txt, border, ln, align, fill, link)

    def multi_cell(self, w, h, txt, border=0, align='J', fill=False):
        txt = self.sanitize_text(txt)
        super().multi_cell(w, h, txt, border, align, fill)

def create_bar_chart(products):
    if not products:
        return None
    
    names = [p['product'] for p in products]
    mentions = [p['mentions'] for p in products]
    
    # Sort by mentions
    zipped = sorted(zip(mentions, names), reverse=True)
    if not zipped: return None
    mentions, names = zip(*zipped)
    
    # Limit to top 10
    names = names[:10]
    mentions = mentions[:10]
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(names, mentions, color='#4e73df')
    plt.xlabel('Mentions')
    plt.title('Product/Competitor Mention Frequency')
    plt.gca().invert_yaxis()
    
    # Add values
    for i, v in enumerate(mentions):
        plt.text(v + 0.1, i, str(v), va='center')
        
    filename = f"chart_{uuid.uuid4()}.png"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    return filename

def generate_report_v2(data, report_filename, original_filename="Unknown"):
    REPORTS_DIR = "reports"
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        
    report_path = os.path.join(REPORTS_DIR, report_filename)
    
    # Helper to clean data types
    def ensure_dict(val):
        if isinstance(val, dict): return val
        if isinstance(val, str):
            try: return json.loads(val)
            except: return {}
        return {}

    def ensure_list(val):
        if isinstance(val, list): return val
        if isinstance(val, str):
            try: return json.loads(val)
            except: return []
        return []

    # Unpack Data with safety
    summary = data.get("summary", "")
    overall_score = data.get("overall_score", 0)
    sentiment = data.get("sentiment", "Neutral")
    metrics = ensure_dict(data.get("performance_metrics", {}))
    products = ensure_list(data.get("products_analysis", []))
    product_insights = ensure_dict(data.get("product_insights", {}))
    promise_analysis = ensure_dict(data.get("promise_analysis", {}))
    roadmap = ensure_list(data.get("improvement_roadmap", []))
    sentiment_details = ensure_dict(data.get("sentiment_details", {}))
    top_recommendations = ensure_list(data.get("top_recommendations", []))
    product_acceptance = ensure_dict(data.get("product_acceptance_data", {}))
    next_actions = ensure_dict(data.get("next_actions", {}))
    
    # Transcripts
    translated_text = data.get("translated_text", "")
    tamil_text = data.get("tamil_text", "")

    pdf = PDF()
    
    # Cross-platform font handling
    # Strategy: Use OpenSans (TTF) as primary for English/Latin.
    # Register NotoSansTamil as "TamilFont" and set it as a FALLBACK.
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    local_font_dir = os.path.join(BASE_DIR, "static", "fonts")
    
    # 1. Load Primary English Font (OpenSans)
    opensans_path = os.path.join(local_font_dir, "OpenSans-Regular.ttf")
    opensans_bold = os.path.join(local_font_dir, "OpenSans-Bold.ttf")
    opensans_italic = os.path.join(local_font_dir, "OpenSans-Italic.ttf")
    
    BODY_FONT = "Arial" # Default fallback
    
    print(f"[DEBUG] Looking for fonts in: {local_font_dir}")
    
    if os.path.exists(opensans_path):
        try:
            pdf.add_font("OpenSans", style="", fname=opensans_path)
            if os.path.exists(opensans_bold):
                pdf.add_font("OpenSans", style="B", fname=opensans_bold)
            if os.path.exists(opensans_italic):
                pdf.add_font("OpenSans", style="I", fname=opensans_italic)
            
            BODY_FONT = "OpenSans"
            print("[DEBUG] Loaded OpenSans successfully.")
        except Exception as e:
            print(f"[WARNING] Failed to load OpenSans: {e}")
    else:
         print(f"[WARNING] OpenSans not found at {opensans_path}")

    # 2. Check for Tamil Font
    tamil_font_path = None
    possible_tamil_fonts = [
         os.path.join(local_font_dir, "NotoSansTamil-Regular.ttf"),
         r"C:\Windows\Fonts\Nirmala.ttf",
    ]
    
    for path in possible_tamil_fonts:
        if os.path.exists(path):
            tamil_font_path = path
            break
            
    # 3. Add Tamil Font (Decoupled from OpenSans)
    if tamil_font_path:
        try:
            print(f"[DEBUG] Loading Tamil font from: {tamil_font_path}")
            pdf.add_font("TamilFont", style="", fname=tamil_font_path)
            
            # Try to find/add bold version
            if "NotoSansTamil-Regular" in tamil_font_path:
                 bold_path = tamil_font_path.replace("Regular", "Bold")
                 if os.path.exists(bold_path):
                     pdf.add_font("TamilFont", style="B", fname=bold_path)
            elif "Nirmala" in tamil_font_path:
                 if os.path.exists(r"C:\Windows\Fonts\NirmalaB.ttf"):
                     pdf.add_font("TamilFont", style="B", fname=r"C:\Windows\Fonts\NirmalaB.ttf")
            
            # SET FALLBACK
            pdf.set_fallback_fonts(["TamilFont"])
            print("[DEBUG] Tamil fallback configured.")
        except Exception as e:
            print(f"[WARNING] Failed to configure Tamil fallback: {e}")
    else:
        print("[WARNING] No Tamil font found.")

    # 4. Set Main Font
    pdf.set_font(BODY_FONT)
    try:
        pdf.font_family = BODY_FONT
    except:
        pass
    
    # Helper for safe text rendering
    def safe_multi_cell(text, font=None, style="", size=10, h=6, color=(0,0,0)):
        if font is None:
            font = BODY_FONT
        if not isinstance(text, str):
            text = str(text)
            
        replacements = {
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', 
            "\u2013": "-", "\u2014": "-", "\u2022": "-", "\u2026": "..."
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        pdf.set_text_color(*color)
        try:
            pdf.set_font(font, style, size)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, h, text)
        except Exception as e:
            pdf.set_font("Arial", 'I', size) # Fallback
            clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
            pdf.multi_cell(0, h, clean_text)
        pdf.set_text_color(0, 0, 0)


    # ===== PAGE 1: PREMIUM COVER PAGE =====
    pdf.add_page()
    
    pdf.set_fill_color(10, 25, 47)  # Deep navy
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.set_fill_color(212, 175, 55)  # Gold
    pdf.rect(0, 0, 8, 297, 'F')
    
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(20, 30, 170, 237, 'F')
    
    pdf.set_y(50)
    pdf.set_font(BODY_FONT, 'B', 16)
    pdf.set_text_color(212, 175, 55)
    pdf.cell(0, 10, "SHARAN ENTERPRISES", ln=1, align='C')
    
    pdf.set_font(BODY_FONT, '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Sales Intelligence Division", ln=1, align='C')
    
    pdf.set_draw_color(212, 175, 55)
    pdf.set_line_width(0.5)
    pdf.line(60, pdf.get_y() + 5, 150, pdf.get_y() + 5)
    
    pdf.ln(20)
    
    pdf.set_font(BODY_FONT, 'B', 28)
    pdf.set_text_color(10, 25, 47)
    pdf.cell(0, 15, "SALES PERFORMANCE", ln=1, align='C')
    pdf.cell(0, 15, "ANALYTICS REPORT", ln=1, align='C')
    
    pdf.ln(10)
    
    pdf.set_y(150)
    pdf.set_draw_color(212, 175, 55)
    pdf.set_line_width(2)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(85, 150, 40, 40, 'D')
    
    pdf.set_font(BODY_FONT, 'B', 32)
    pdf.set_text_color(212, 175, 55)
    pdf.set_y(160)
    pdf.cell(0, 20, str(overall_score), ln=1, align='C')
    
    pdf.set_font(BODY_FONT, '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "OVERALL SCORE", ln=1, align='C')
    
    pdf.ln(20)
    
    # Date and metadata
    pdf.set_font(BODY_FONT, '', 11)
    pdf.set_text_color(80, 80, 80)
    current_date = dt.datetime.now().strftime("%A, %B %d, %Y")
    current_time = dt.datetime.now().strftime("%I:%M %p")
    pdf.cell(0, 8, f"Generated: {current_date} at {current_time}", ln=1, align='C')
    pdf.cell(0, 8, f"Source File: {original_filename}", ln=1, align='C')
    
    # Footer on cover
    pdf.set_y(250)
    pdf.set_font(BODY_FONT, 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Confidential - For Internal Use Only", ln=1, align='C')
    pdf.cell(0, 5, "Powered by Groq AI | Advanced Sales Analytics", ln=1, align='C')
    
    # ===== PAGE 2: EXECUTIVE SUMMARY =====
    pdf.add_page()
    
    # Premium section header
    pdf.set_fill_color(10, 25, 47)  # Navy
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    
    # Gold accent line
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     EXECUTIVE SUMMARY", ln=1)
    
    # Content box with subtle border
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    start_y = pdf.get_y() + 5
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    pdf.set_font(BODY_FONT, '', 10)
    safe_multi_cell(summary, size=10, h=5)
    
    # Draw border around content
    end_y = pdf.get_y()
    pdf.rect(10, start_y, 190, end_y - start_y, 'D')
    
    pdf.ln(10)
    
    # ===== PAGE 3: PERFORMANCE METRICS =====
    pdf.add_page()
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 10, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.cell(0, 10, " Performance Metrics Dashboard", ln=1)
    pdf.ln(5)
    
    def draw_metric_bar(label, value):
        pdf.set_font(BODY_FONT, '', 10)
        pdf.cell(60, 8, label, 0, 0)
        
        # Progress bar
        pdf.set_fill_color(220, 220, 220)
        pdf.rect(pdf.get_x(), pdf.get_y() + 2, 100, 4, 'F')
        
        if value >= 80: pdf.set_fill_color(46, 204, 113)
        elif value >= 50: pdf.set_fill_color(241, 196, 15)
        else: pdf.set_fill_color(231, 76, 60)
        
        bar_width = (value / 100) * 100
        pdf.rect(pdf.get_x(), pdf.get_y() + 2, bar_width, 4, 'F')
        
        pdf.set_x(pdf.get_x() + 105)
        pdf.cell(20, 8, f"{value}%", 0, 1)
    
    if metrics:
        draw_metric_bar("Closing Probability", metrics.get("closing_probability", 0))
        draw_metric_bar("Objection Handling", metrics.get("objection_handling", 0))
        draw_metric_bar("Empathy Score", metrics.get("empathy_score", 0))
        draw_metric_bar("Product Knowledge", metrics.get("product_knowledge", 0))
        draw_metric_bar("Conversation Control", metrics.get("conversation_control", 0))
    
    pdf.ln(10)
    
    # ===== PAGE 4: CALL METADATA =====
    pdf.add_page()
    
    # Calculate metadata
    word_count = len(translated_text.split())
    sentence_count = translated_text.count('.') + translated_text.count('!') + translated_text.count('?')
    speaking_rate = int(word_count / max(1, sentence_count)) if sentence_count > 0 else 0
    
    # Header
    pdf.set_fill_color(10, 25, 47)
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     CALL METADATA", ln=1)
    pdf.ln(8)
    
    # Table
    pdf.set_fill_color(0, 102, 204)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(BODY_FONT, 'B', 11)
    pdf.cell(95, 10, "Metric", 1, 0, 'C', True)
    pdf.cell(95, 10, "Value", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(BODY_FONT, '', 10)
    
    metadata_rows = [
        ("Analysis Date", dt.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")),
        ("Estimated Duration", f"{word_count * 0.18:.2f} seconds ({word_count * 0.18 / 60:.1f} minutes)"),
        ("Word Count", f"{word_count} words"),
        ("Sentence Count", f"{sentence_count} sentences"),
        ("Speaking Rate", f"{speaking_rate} words/min"),
        ("Overall Sentiment", sentiment.upper()),
        ("Products Discussed", f"{len(products)} items ({sum(p.get('mentions', 1) for p in products)} mentions)"),
        ("AI Analysis", "Enabled")
    ]
    
    for i, (label, value) in enumerate(metadata_rows):
        fill_color = (240, 248, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        pdf.cell(95, 8, label, 1, 0, 'L', True)
        pdf.cell(95, 8, value, 1, 1, 'L', True)
    
    # ===== PAGE 5: PROMISE STATEMENT & COMMITMENT ANALYSIS (DETAILED) =====
    pdf.add_page()
    
    # Blue header box
    pdf.set_fill_color(65, 105, 225)
    pdf.rect(10, pdf.get_y(), 190, 12, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, " Promise Statement & Commitment Analysis", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # Summary Table
    pdf.set_font(BODY_FONT, 'B', 10)
    
    # Table headers
    pdf.set_fill_color(128, 0, 128)  # Purple
    pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 8, "Category", 1, 0, 'C', True)
    pdf.cell(40, 8, "Count", 1, 0, 'C', True)
    pdf.cell(50, 8, "Status", 1, 0, 'C', True)
    pdf.cell(40, 8, "Quality Score", 1, 1, 'C', True)
    
    # Table rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(BODY_FONT, '', 10)
    
    good_count = promise_analysis.get('good_promises_count', 0)
    bad_count = promise_analysis.get('bad_promises_count', 0)
    quality_score = promise_analysis.get('quality_score', '0/100')
    
    # Good Promises row
    pdf.set_fill_color(200, 255, 200)  # Light green
    pdf.cell(60, 8, "Good Promises Used", 1, 0, 'L', True)
    pdf.cell(40, 8, str(good_count), 1, 0, 'C', True)
    pdf.cell(50, 8, " Positive", 1, 0, 'L', True)
    pdf.set_fill_color(255, 255, 255)
    pdf.cell(40, 8, "", 1, 1, 'C', True)
    
    # Bad Promises row
    pdf.set_fill_color(255, 200, 200)  # Light red
    pdf.cell(60, 8, "Bad Promises Detected", 1, 0, 'L', True)
    pdf.cell(40, 8, str(bad_count), 1, 0, 'C', True)
    pdf.cell(50, 8, " Flag for Review", 1, 0, 'L', True)
    pdf.set_fill_color(255, 255, 255)
    pdf.cell(40, 8, quality_score, 1, 1, 'C', True)
    
    # Promise Ratio row
    pdf.set_fill_color(255, 230, 255)  # Light purple
    pdf.cell(60, 8, "Promise Ratio (Good:Bad)", 1, 0, 'L', True)
    pdf.cell(40, 8, f"{good_count}:{bad_count}", 1, 0, 'C', True)
    pdf.cell(50, 8, "Needs improvement", 1, 0, 'L', True)
    pdf.cell(40, 8, "", 1, 1, 'C', True)
    
    pdf.ln(8)
    
    # Good Promises Section
    pdf.set_font(BODY_FONT, 'B', 12)
    pdf.set_text_color(0, 128, 0) # Green
    pdf.cell(0, 8, " Good Promises Detected (Trust Builders):", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(BODY_FONT, '', 10)
    pdf.ln(2)
    
    good_list = promise_analysis.get("good_promises", [])
    if good_list:
        for item in good_list:
             # Use a checkmark or similar
             safe_multi_cell(f" + {item}", size=10, h=6)
    else:
         safe_multi_cell("No specific good promises detected.", size=10, h=6)

    pdf.ln(5)
    
    # Bad Promises Section
    pdf.set_font(BODY_FONT, 'B', 12)
    pdf.set_text_color(255, 0, 0) # Red
    pdf.cell(0, 8, " Bad Promises / Problematic Statements (Risks):", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(BODY_FONT, '', 10)
    pdf.ln(2)
    
    # Merge bad_promises and problematic_statements if they exist differently
    bad_list = promise_analysis.get("bad_promises", []) + promise_analysis.get("problematic_statements", [])
    
    # Deduplicate just in case
    bad_list = list(set(bad_list))
    
    if bad_list:
        for item in bad_list:
             # Use an X mark
             safe_multi_cell(f" - {item}", size=10, h=6)
    else:
         safe_multi_cell("No problematic statements detected.", size=10, h=6)
    
    pdf.ln(5)
    
    # Improvement Plan
    pdf.set_fill_color(65, 105, 225)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(BODY_FONT, 'B', 11)
    pdf.cell(0, 8, " Promise Quality Improvement Plan:", ln=1, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(BODY_FONT, '', 9)
    pdf.ln(2)
    
    improvement_points = [
        "- Avoid absolute guarantees (\"never\", \"always\", \"100% sure\")",
        "- Don't make unauthorized commitments on returns, exchanges, or adjustments",
        "- Focus on factual benefits: margin, movement, customer demand",
        "- Use urgency based on real constraints (limited stock, offer period)",
        "- Build credibility through market intelligence, not exclusivity claims"
    ]
    
    for point in improvement_points:
        pdf.cell(0, 5, point, ln=1)
    
    # ===== PAGE 6: SENTIMENT & EMOTIONAL INTELLIGENCE =====
    pdf.add_page()
    pdf.set_fill_color(10, 25, 47)
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     SENTIMENT & EMOTIONAL INTELLIGENCE", ln=1)
    pdf.ln(8)
    
    pdf.set_font(BODY_FONT, '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 7, f"Overall Sentiment: {sentiment}", ln=1)
    pdf.cell(0, 7, f"Positive: {sentiment_details.get('positive_percent', 0)}% | Negative: {sentiment_details.get('negative_percent', 0)}% | Neutral: {sentiment_details.get('neutral_percent', 0)}%", ln=1)
    pdf.cell(0, 7, f"Enthusiasm Score: {sentiment_details.get('enthusiasm_score', '0/100')}", ln=1)
    pdf.cell(0, 7, f"Professional Tone: {sentiment_details.get('professional_tone', '0/100')}", ln=1)
    pdf.ln(10)
    
    # ===== PAGE 7: PRODUCTS ANALYSIS =====
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(10, 25, 47)
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     PRODUCTS DISCUSSED & FREQUENCY ANALYSIS", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
    
    
    # Product chart - smaller size to fit on one page
    chart_path = create_bar_chart(products)
    if chart_path:
        pdf.image(chart_path, x=10, w=120)  # Reduced width from 140 to 120
        pdf.ln(65)  # Reduced spacing from 90 to 65
        try:
            os.remove(chart_path)
        except:
            pass
    
    pdf.ln(3)  # Reduced spacing from 5 to 3
    
    # Table headers
    pdf.set_fill_color(255, 165, 0)  # Orange
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(BODY_FONT, 'B', 10)
    pdf.cell(50, 8, "Product", 1, 0, 'C', True)
    pdf.cell(30, 8, "Mentions", 1, 0, 'C', True)
    pdf.cell(60, 8, "Coverage", 1, 0, 'C', True)
    pdf.cell(50, 8, "Priority Level", 1, 1, 'C', True)
    
    # Table rows - All products on single page
    pdf.set_font(BODY_FONT, '', 9)
    
    for i, product in enumerate(products[:11]):  # Show all 11 products
        if not isinstance(product, dict): continue # Skip invalid items
        name = product.get('product', 'Unknown')
        mentions = product.get('mentions', 1)
        priority = product.get('priority', 'Moderate')
        
        # Alternating row colors
        fill_color = (255, 255, 224) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        
        pdf.cell(50, 7, str(name)[:20], 1, 0, 'L', True)
        pdf.cell(30, 7, f"{mentions}x", 1, 0, 'C', True)
        
        # Coverage bar
        coverage_width = min(mentions * 10, 50)
        pdf.cell(60, 7, "", 1, 0, 'L', True)
        x_pos = pdf.get_x() - 58
        y_pos = pdf.get_y() + 2
        pdf.set_fill_color(255, 0, 0)
        pdf.rect(x_pos, y_pos, coverage_width, 3, 'F')
        
        pdf.cell(50, 7, str(priority), 1, 1, 'C', True)
    
    
    pdf.ln(5)
    
    # ===== PAGE 8: PRODUCT MIX INSIGHTS =====
    pdf.add_page()
    
    # Product Mix Insights
    pdf.set_fill_color(10, 25, 47)
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     PRODUCT MIX INSIGHTS", ln=1)
    pdf.ln(8)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(BODY_FONT, '', 10)
    pdf.ln(2)
    
    total_mentions = sum(p.get('mentions', 1) for p in products)
    avg_mentions = total_mentions / len(products) if products else 0
    most_emphasized = product_insights.get('most_emphasized', 'N/A')
    
    insights = [
        f"- Total unique products: {len(products)}",
        f"- Total product mentions: {total_mentions}",
        f"- Average mentions per product: {avg_mentions:.1f}",
        f"- Most emphasized: {most_emphasized} ({products[0].get('mentions', 1)} mentions)" if products else "- Most emphasized: N/A",
        "- Product diversity score: 100/100",
        f"- Recommendation: {product_insights.get('recommendation', 'Excellent product coverage. Maintain diversity.')}"
    ]
    
    for insight in insights:
        pdf.cell(0, 5, insight, ln=1)
    
    # ===== PAGE 9: IMPROVEMENT ROADMAP =====
    pdf.add_page()
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 10, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.cell(0, 10, " Improvement Roadmap", ln=1)
    pdf.ln(5)
    
    for item in roadmap:
        if not isinstance(item, dict): continue
        category = item.get('category', '')
        observation = item.get('observation', '')
        recommendation = item.get('recommendation', '')
        priority = item.get('priority', 'MEDIUM').upper()
        
        pdf.set_font(BODY_FONT, 'B', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, f"{category} ({priority})", ln=1)
        
        pdf.set_font(BODY_FONT, '', 10)
        pdf.set_text_color(80, 80, 80)
        safe_multi_cell(f"Observation: {observation}", size=10, h=5)
        pdf.set_text_color(39, 174, 96)
        safe_multi_cell(f"Action: {recommendation}", size=10, h=5)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
    

    
    
    # ===== NEW: RECOMMENDATIONS SUMMARY BOX =====
    pdf.add_page()
    
    # Premium header
    pdf.set_fill_color(10, 25, 47)
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     TOP 3 RECOMMENDATIONS", ln=1)
    pdf.ln(5)
    
    # Highlighted recommendation boxes
    for i, rec in enumerate(top_recommendations[:3], 1):
        pdf.set_fill_color(255, 250, 205)  # Light yellow
        pdf.set_draw_color(212, 175, 55)
        pdf.set_line_width(0.5)
        
        start_y = pdf.get_y()
        pdf.set_font(BODY_FONT, 'B', 11)
        pdf.set_text_color(10, 25, 47)
        pdf.cell(0, 8, f"  {i}. {rec[:60]}...", ln=1) if len(rec) > 60 else pdf.cell(0, 8, f"  {i}. {rec}", ln=1)
        
        pdf.rect(10, start_y, 190, 8, 'D')
        pdf.ln(3)
    
    pdf.ln(10)
    
    # ===== NEW: PRODUCT ACCEPTANCE ANALYSIS =====
    # Create simple acceptance chart
    if product_acceptance:
        total_offered = product_acceptance.get('total_offered', 0)
        total_accepted = product_acceptance.get('total_accepted', 0)
        acceptance_rate = product_acceptance.get('acceptance_rate', 0)
        
        pdf.set_fill_color(10, 25, 47)
        pdf.rect(10, pdf.get_y(), 190, 14, 'F')
        pdf.set_fill_color(212, 175, 55)
        pdf.rect(10, pdf.get_y(), 4, 14, 'F')
        pdf.set_font(BODY_FONT, 'B', 14)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 14, "     PRODUCT ACCEPTANCE ANALYSIS", ln=1)
        pdf.ln(8)
        
        # Stats boxes
        pdf.set_font(BODY_FONT, 'B', 12)
        pdf.set_text_color(0, 0, 0)
        
        # Offered box
        pdf.set_fill_color(220, 237, 255)
        pdf.rect(15, pdf.get_y(), 55, 30, 'F')
        pdf.set_xy(15, pdf.get_y() + 5)
        pdf.cell(55, 8, "Products Offered", 0, 1, 'C')
        pdf.set_font(BODY_FONT, 'B', 20)
        pdf.set_xy(15, pdf.get_y())
        pdf.cell(55, 12, str(total_offered), 0, 0, 'C')
        
        # Accepted box
        pdf.set_font(BODY_FONT, 'B', 12)
        pdf.set_fill_color(200, 255, 200)
        pdf.rect(75, pdf.get_y() - 17, 55, 30, 'F')
        pdf.set_xy(75, pdf.get_y() - 12)
        pdf.cell(55, 8, "Products Accepted", 0, 1, 'C')
        pdf.set_font(BODY_FONT, 'B', 20)
        pdf.set_xy(75, pdf.get_y())
        pdf.cell(55, 12, str(total_accepted), 0, 0, 'C')
        
        # Acceptance Rate box
        pdf.set_font(BODY_FONT, 'B', 12)
        pdf.set_fill_color(255, 215, 0)
        pdf.rect(135, pdf.get_y() - 17, 55, 30, 'F')
        pdf.set_xy(135, pdf.get_y() - 12)
        pdf.cell(55, 8, "Acceptance Rate", 0, 1, 'C')
        pdf.set_font(BODY_FONT, 'B', 20)
        pdf.set_xy(135, pdf.get_y())
        pdf.cell(55, 12, f"{acceptance_rate}%", 0, 1, 'C')
        
        pdf.ln(20)
    
    # ===== NEW: CONCLUSION & NEXT ACTIONS =====
    pdf.add_page()
    
    pdf.set_fill_color(10, 25, 47)
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     CONCLUSION & NEXT ACTIONS", ln=1)
    pdf.ln(8)
    
    # Rep Improvements
    pdf.set_font(BODY_FONT, 'B', 12)
    pdf.set_text_color(10, 25, 47)
    pdf.cell(0, 8, " What the Rep Should Improve:", ln=1)
    pdf.ln(2)
    
    pdf.set_font(BODY_FONT, '', 10)
    pdf.set_text_color(0, 0, 0)
    rep_improvements = next_actions.get('rep_improvements', [])
    for imp in rep_improvements:
        pdf.cell(0, 6, f"  - {imp}", ln=1)
    pdf.ln(5)
    
    # Predicted Next Orders
    pdf.set_font(BODY_FONT, 'B', 12)
    pdf.set_text_color(10, 25, 47)
    pdf.cell(0, 8, " Predicted Orders for Next Month:", ln=1)
    pdf.ln(2)
    
    pdf.set_font(BODY_FONT, '', 10)
    pdf.set_text_color(0, 0, 0)
    predicted_orders = next_actions.get('predicted_next_orders', [])
    for order in predicted_orders:
        pdf.cell(0, 6, f"  - {order}", ln=1)
    pdf.ln(5)
    
    # Follow-up Date
    pdf.set_font(BODY_FONT, 'B', 12)
    pdf.set_text_color(10, 25, 47)
    pdf.cell(0, 8, " Recommended Follow-up Date:", ln=1)
    pdf.ln(2)
    
    pdf.set_font(BODY_FONT, '', 11)
    pdf.set_text_color(212, 175, 55)
    follow_up = next_actions.get('follow_up_date', 'TBD')
    pdf.cell(0, 8, f"  {follow_up}", ln=1)
    pdf.ln(10)

    # ===== PAGE 10: TRANSCRIPTS =====
    pdf.add_page()
    pdf.set_fill_color(10, 25, 47)
    pdf.rect(10, pdf.get_y(), 190, 14, 'F')
    pdf.set_fill_color(212, 175, 55)
    pdf.rect(10, pdf.get_y(), 4, 14, 'F')
    pdf.set_font(BODY_FONT, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "     TRANSCRIPTS", ln=1)
    pdf.ln(8)
    
    # English
    pdf.set_font(BODY_FONT, 'B', 12)
    pdf.set_text_color(10, 25, 47)
    pdf.cell(0, 8, " English Translation:", ln=1)
    pdf.ln(2)
    pdf.set_font(BODY_FONT, '', 10)
    pdf.set_text_color(0, 0, 0)
    safe_multi_cell(translated_text, size=10, h=5)
    pdf.ln(10)
    
    # Tamil
    pdf.add_page()
    pdf.set_font(BODY_FONT, 'B', 12)
    pdf.set_text_color(10, 25, 47)
    pdf.cell(0, 8, " Original Transcript:", ln=1)
    pdf.ln(2)
    
    # Try to switch to Tamil font explicitly
    if "TamilFont" in pdf.fonts:
        print("Switching to TamilFont for transcript...")
        pdf.set_font("TamilFont", '', 10)
    else:
        print("TamilFont not found in registered fonts!")
        pdf.set_font(BODY_FONT, '', 10)
        
    pdf.set_text_color(0, 0, 0)
    safe_multi_cell(tamil_text, size=10, h=5)

    pdf.output(report_path)
    return report_path
