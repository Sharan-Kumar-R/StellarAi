from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from deep_translator import GoogleTranslator
from textblob import TextBlob
from fpdf import FPDF
import os
import uuid
import datetime as dt
import shutil
import shutil
import csv
import io
import pandas as pd
from fastapi import UploadFile, File
import httpx
import subprocess

import database
import transcription
import mongo_upload
from pdf_generator import generate_report_v2


app = FastAPI()

# Mount static files if needed (creating directory just in case)
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount reports directory to serve PDFs
if not os.path.exists("reports"):
    os.makedirs("reports")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# Setup templates
if not os.path.exists("templates"):
    os.makedirs("templates")
templates = Jinja2Templates(directory="templates")

# Ensure reports directory exists
REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)



# Global store for progress updates
# Format: {request_id: "Current status message"}
progress_store = {}

database.init_db()

@app.get("/progress/{request_id}")
async def progress_stream(request_id: str):
    async def event_generator():
        while True:
            if request_id in progress_store:
                # Upgrade to handle dict or string for backward compatibility
                data = progress_store[request_id]
                if isinstance(data, dict):
                    status_msg = data.get("message", "Processing...")
                    status_state = data.get("status", "processing")
                    
                    yield f"data: {status_msg}\n\n"
                    
                    if status_state in ["completed", "failed"]:
                         break
                else:
                    # Old string format support
                    status = data
                    if status == "COMPLETE" or status.startswith("ERROR"):
                        yield f"data: {status}\n\n"
                        break
                    yield f"data: {status}\n\n"
            else:
                # If ID not found yet, it might be starting up
                yield f"data: Initializing...\n\n"
            
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/analyze")
async def analyze_redirect():
    return RedirectResponse(url="/")

from groq import Groq
import json

# ... (Keep existing imports)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ... (Keep existing imports)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Load API credentials for cloud upload
API_TOKEN = os.getenv("API_TOKEN")
API_UID = os.getenv("API_UID")
REPORT_URL = os.getenv("report_url")

async def upload_report_to_api(payload):
    """
    Upload report data to cloud API endpoint in JSON format.
    
    Args:
        payload: Dictionary containing report data
        
    Returns:
        dict: {"success": bool, "message": str, "error": str (optional)}
    """
    try:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "xxxid": API_UID,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client_http:
            response = await client_http.post(
                REPORT_URL,
                headers=headers,
                json=payload
            )
            
            # if response.status_code in [200, 201]:
            #     print(f"✓ Report uploaded successfully to cloud API (Status: {response.status_code})")
            #     return {
            #         "success": True,
            #         "message": "Report uploaded successfully",
            #         "status_code": response.status_code
            #     }
            # else:
            #     error_msg = f"API returned status {response.status_code}: {response.text[:200]}"
            #     print(f"✗ Upload failed: {error_msg}")
            #     return {
            #         "success": False,
            #         "message": "Upload failed",
            #         "error": error_msg
            #     }
            print("[INFO] Cloud API upload disabled.")
            return {"success": True, "message": "Upload disabled"}

                
    except httpx.TimeoutException:
        error_msg = "Upload timeout - API did not respond in time"
        print(f"✗ {error_msg}")
        return {"success": False, "message": "Upload timeout", "error": error_msg}
        
    except Exception as e:
        error_msg = f"Upload error: {str(e)}"
        print(f"✗ {error_msg}")
        return {"success": False, "message": "Upload failed", "error": error_msg}



def convert_to_wav(input_path):
    """
    Converts any audio file to WAV format (16kHz, Mono, 16-bit PCM) using FFmpeg.
    This ensures compatibility with the chunking logic and speech API.
    """
    try:
        output_path = os.path.splitext(input_path)[0] + "_converted.wav"
        print(f"Converting {input_path} to {output_path}...")
        
        # FFmpeg command:
        # -i input
        # -vn (no video)
        # -acodec pcm_s16le (16-bit PCM)
        # -ar 16000 (16kHz sample rate)
        # -ac 1 (Mono channel)
        # -y (overwrite)
        command = [
            "ffmpeg", "-i", input_path, 
            "-vn", 
            "-acodec", "pcm_s16le", 
            "-ar", "16000", 
            "-ac", "1", 
            "-y", 
            output_path
        ]
        
        # Run conversion
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output_path):
            print(f"Conversion successful: {output_path}")
            return output_path
        else:
            print("Conversion failed: Output file not created.")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg conversion failed: {e}")
        return None
    except Exception as e:
        print(f"Conversion error: {e}")
        return None



# ---------------------------------------------------------
# NEW APIs
# ---------------------------------------------------------

@app.post("/api/upload")
async def upload_audio(background_tasks: BackgroundTasks, audio_file: UploadFile = File(...)):
    """
    API 1: Upload audio, start processing, return 200 + ID.
    """
    request_id = str(uuid.uuid4())
    filename = audio_file.filename
    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        ext = ".wav" # Default
        
    temp_filename = f"temp_{request_id}{ext}"
    
    # Save file
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)
        
    # Init store
    progress_store[request_id] = {
        "status": "queued", 
        "message": "Upload complete. queued for processing.",
        "filename": filename,
        "upload_time": dt.datetime.now().isoformat()
    }
    
    # Start Task
    # We need to link to the existing monolithic logic OR the new refactored one.
    # I will call a wrapper that effectively runs the logic previously in /analyze
    background_tasks.add_task(full_analysis_pipeline, request_id, temp_filename, filename)
    
    return {
        "message": "Audio uploaded successfully",
        "request_id": request_id,
        "status": "processing_started"
    }

@app.get("/api/status/{request_id}")
async def get_status(request_id: str):
    """
    API 2: Check status of the report.
    """
    if request_id not in progress_store:
        raise HTTPException(status_code=404, detail="Request ID not found")
        
    data = progress_store[request_id]
    
    # Handle legacy string format if mainly used by old code (though we are moving away)
    if isinstance(data, str):
         return {"status": "processing", "message": data}
         
    return {
        "request_id": request_id,
        "status": data.get("status"),
        "message": data.get("message"),
        "report_ready": data.get("status") == "completed",
        "report_url": data.get("report_url")
    }

@app.get("/api/report/{request_id}")
async def get_report_info(request_id: str):
    """
    API 3: Get generated audio/report ID and details.
    """
    if request_id not in progress_store:
         raise HTTPException(status_code=404, detail="ID not found")
         
    data = progress_store[request_id]
    
    if isinstance(data, str) or data.get("status") != "completed":
        return {"status": "processing", "message": "Report not ready yet"}
        
    return {
        "request_id": request_id,
        "original_filename": data.get("filename"),
        "generated_report_id": os.path.basename(data.get("report_url", "")),
        "download_url": data.get("report_url"),
        "status": "completed"
    }

# ---------------------------------------------------------
# REFACTOR HELPER: Moving the Giant Logic Block
# ---------------------------------------------------------
async def full_analysis_pipeline(request_id, temp_filename, original_filename):
    """
    Contains the logic previously in /analyze endpoint.
    """
    try:
        progress_store[request_id]["status"] = "processing"
        
        # 1. Convert
        progress_store[request_id]["message"] = "Normalizing audio format..."
        converted_path = convert_to_wav(temp_filename)
        if not converted_path:
             raise Exception("Conversion failed")
             
        # 2. Transcribe
        progress_store[request_id]["message"] = "Transcribing..."
        def update_prog(msg):
            if isinstance(progress_store.get(request_id), dict):
                progress_store[request_id]["message"] = msg
        
        tamil_text = await run_in_threadpool(transcription.transcribe_audio_direct, converted_path, update_prog)
        
        # Cleanup
        try:
             if os.path.exists(converted_path) and converted_path != temp_filename:
                 os.remove(converted_path)
             if os.path.exists(temp_filename):
                 os.remove(temp_filename)
        except: pass

        if not tamil_text: raise Exception("No text transcribed")
        
        # 3. Translate
        progress_store[request_id]["message"] = "Translating..."
        translator = GoogleTranslator(source='auto', target='en')
        translated_text = await run_in_threadpool(translator.translate, tamil_text)
        
        # 4. Groq Analysis
        progress_store[request_id]["message"] = "AI Analysis..."
        
        # (Insert Prompt logic here or simplify for this tool call - 
        # I will refer to valid methods to avoid huge code blocks in 'replacement' if possible,
        # but here I must include it or call a sub-function.
        # I will assume the prompt is defined below or copied.)
        
        prompt = f"""
        Analyze the sales call transcript (Tamil translated to English) and return a JSON object matching this EXACT structure.
        
        
        CRITICAL DEFINITIONS FOR PROMISE CLASSIFICATION:
        - "GOOD PROMISE": A realistic commitment (e.g., "I will check stock," "I will visit Tuesday"). Trust-building.
        - "BAD PROMISE": False guarantees, over-committing on things outside control (e.g., "Price will NEVER change," "You will definitely get 100% refund," "No other shop has this"). Trust-damaging.
        
        CRITICAL RULES:
        1. "improvement_roadmap": Must include at least 2-3 specific actionable items. NOT empty.
        2. "product_insights": Must analyze which products were discussed.
        3. "products_analysis": List ALL products mentioned, even generic ones.
        
        JSON Structure:
        {{
            "summary": "Detailed executive summary of the conversation.",
            "sentiment": "Positive/Negative/Neutral",
            "overall_score": 85,
            "performance_metrics": {{"closing_probability": 75, "objection_handling": 60, "empathy_score": 80, "product_knowledge": 90, "conversation_control": 50}},
            "products_analysis": [
                {{"product": "Maida", "mentions": 5, "priority": "High"}},
                {{"product": "Sooji", "mentions": 2, "priority": "Low"}}
            ],
            "product_insights": {{"total_unique": 2, "most_emphasized": "Maida", "recommendation": "Push Sooji more."}},
            "promise_analysis": {{"good_promises_count": 1, "bad_promises_count": 0, "quality_score": "90/100", "problematic_statements": []}},
            "improvement_roadmap": [
                {{"category": "Closing Skills", "observation": "Did not ask for the order.", "recommendation": "Use a direct close next time.", "priority": "HIGH"}},
                {{"category": "Product Knowledge", "observation": "Stumbled on price.", "recommendation": "Memorize price list.", "priority": "MEDIUM"}}
            ],
            "sentiment_details": {{"positive_percent": 60, "negative_percent": 10, "neutral_percent": 30, "enthusiasm_score": "7/10", "professional_tone": "8/10"}},
            "top_recommendations": ["Ask for order earlier", "Mention discount scheme"],
            "product_acceptance_data": {{"total_offered": 5, "total_accepted": 3, "acceptance_rate": 60}},
            "next_actions": {{"rep_improvements": ["Be more confident"], "predicted_next_orders": ["50kg Maida"], "follow_up_date": "Tuesday"}}
        }}
        TRANSCRIPT: {translated_text}
        """
        
        completion = await run_in_threadpool(
            lambda: client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_completion_tokens=8000
            )
        )
        data = json.loads(completion.choices[0].message.content)
        
        # Unpack Data
        summary = data.get("summary", "")
        overall_score = data.get("overall_score", 0)
        # ... (In a full refactor, we map ALL fields. For this step, I'll trust the PDF generator uses these locals 
        # if I paste the PDF generation code here. 
        # CRITICAL: The PDF generation code relies on specific variable names. 
        # I must make sure the variable names match.)
        
        
        # Add Transcripts to data for PDF generator
        data["translated_text"] = translated_text
        data["tamil_text"] = tamil_text
        
        # 5. Generate PDF
        progress_store[request_id]["message"] = "Generating PDF..."
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"sales_analysis_report_{timestamp}.pdf"
        
        # Call the new generator
        try:
            report_path = generate_report_v2(data, report_filename, original_filename)
            
            # Persist to Database for Dashboard
            upload_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            salesman_name = "Sales Rep" # Default, or extract if possible from filename/transcript
            database.add_call(
                filename=original_filename,
                upload_date=upload_date,
                salesman_name=salesman_name,
                overall_score=overall_score,
                summary=summary,
                pdf_path=report_filename
            )
            
        except Exception as pdf_err:
             print(f"PDF Gen/DB Error: {pdf_err}")
             # We still mark as completed if PDF generation worked but DB failed? 
             # Or if PDF failed, we catch it.
             if 'report_path' not in locals():
                 raise pdf_err

        progress_store[request_id] = {
            "status": "completed",
            "message": "Analysis Complete.",
            "generated_report_id": report_filename, # useful for "Open in Browser"
            "report_url": f"/download/{report_filename}", # Use download endpoint
            "filename": original_filename,
            "full_analysis": data # Persist full rich JSON
        }
        
    except Exception as e:
        print(f"Background Process Error: {e}")
        progress_store[request_id] = {"status": "failed", "message": str(e), "error": str(e)}


# --- End of Analysis Pipeline ---

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    rows = database.get_all_calls()
    
    # Calculate some stats
    total_calls = len(rows)
    avg_score = 0
    if total_calls > 0:
        avg_score = sum([row['overall_score'] for row in rows]) / total_calls
        
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "calls": rows,
        "total_calls": total_calls,
        "avg_score": int(avg_score)
    })

@app.get("/download/{filename}")
async def download_report(filename: str):
    file_path = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/pdf', filename=filename)
    return {"error": "File not found"}

@app.get("/delete/{call_id}")
async def delete_call(call_id: int):
    try:
        # Get filename to delete file
        row = database.get_call(call_id)
        
        if row:
            pdf_path = row['pdf_path']
            full_path = os.path.join(REPORTS_DIR, pdf_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                
        database.delete_call_db(call_id)
        return JSONResponse(content={"status": "success", "message": "Record deleted successfully"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/export/csv")
async def export_csv():
    rows = database.get_all_calls()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Date', 'Salesman', 'Filename', 'Score', 'Summary'])
    
    # Data
    for row in rows:
        writer.writerow([
            row['upload_date'],
            row['salesman_name'],
            row['filename'],
            row['overall_score'],
            row['summary']
        ])
        
    output.seek(0)
    
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=sales_report.csv"
    return response

@app.get("/export/excel")
async def export_excel():
    rows = database.get_all_calls()
    
    # Convert to DataFrame
    data = []
    for row in rows:
        data.append({
            'Date': row['upload_date'],
            'Salesman': row['salesman_name'],
            'Filename': row['filename'],
            'Score': row['overall_score'],
            'Summary': row['summary']
        })
        
    df = pd.DataFrame(data)
    
    # Create Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales Analysis')
        
    output.seek(0)
    
    response = StreamingResponse(
        io.BytesIO(output.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response.headers["Content-Disposition"] = "attachment; filename=sales_report.xlsx"
    return response

@app.get("/api/v2/analytics/{request_id}")
async def get_analytics_v2(request_id: str):
    """
    Returns the rich, structural JSON analysis matching the dashboard requirements.
    """
    if request_id not in progress_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    data = progress_store[request_id]
    
    # If processing is not complete, return status
    if data.get("status") != "completed":
         return {"status": data.get("status", "processing"), "message": "Analysis in progress"}
    
    result = data.get("full_analysis", {})
    if isinstance(result, dict):
        result["request_id"] = request_id
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
