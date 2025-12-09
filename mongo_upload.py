import os
import json
import base64
import sqlite3
from pathlib import Path
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MAX_AUDIO_SIZE = 15 * 1024 * 1024  # 15 MB limit (slightly under server's 16.7 MB to be safe)

# Get API credentials from environment
API_BASE_URL = os.getenv('API_BASE_URL')
API_UID = os.getenv('API_UID')
API_TOKEN = os.getenv('API_TOKEN')

# Collection endpoints
AUDIO_URL = f"{API_BASE_URL}/auth/eCreateCol?colname={API_UID}_vc_aud"
SALES_URL = f"{API_BASE_URL}/auth/eCreateCol?colname={API_UID}_vc_aly"
REPORT_URL = f"{API_BASE_URL}/auth/eCreateCol?colname={API_UID}_vc_rep"

# Headers for API requests
HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_TOKEN}',
    'xxxid': API_UID
}


async def upload_audio_file(audio_path: str, filename: str = None) -> dict:
    """
    Upload a single audio file to MongoDB vc_aud collection.
    
    Args:
        audio_path: Path to the audio file
        filename: Optional custom filename (defaults to original filename)
        
    Returns:
        dict: {"success": bool, "message": str, "error": str (optional)}
    """
    try:
        # Check if file exists
        if not os.path.exists(audio_path):
            return {"success": False, "message": "File not found", "error": f"Audio file not found: {audio_path}"}
        
        # Get file size
        file_size = os.path.getsize(audio_path)
        
        # Read audio file as binary
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        
        # Encode to base64 for JSON transmission
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Use provided filename or extract from path
        if filename is None:
            filename = os.path.basename(audio_path)
        
        # Prepare payload
        payload = {
            "filename": filename,
            "file_size": file_size,
            "audio_data": audio_base64,
            "upload_timestamp": datetime.now().isoformat(),
            "file_type": os.path.splitext(filename)[1]
        }
        
        # Upload to MongoDB
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                AUDIO_URL,
                headers=HEADERS,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Audio uploaded to MongoDB: {filename} ({file_size} bytes)")
                return {
                    "success": True,
                    "message": "Audio uploaded successfully",
                    "filename": filename
                }
            else:
                error_msg = f"API returned status {response.status_code}: {response.text[:200]}"
                print(f"❌ Audio upload failed: {error_msg}")
                return {
                    "success": False,
                    "message": "Upload failed",
                    "error": error_msg
                }
                
    except httpx.TimeoutException:
        error_msg = "Upload timeout - API did not respond in time"
        print(f"❌ {error_msg}")
        return {"success": False, "message": "Upload timeout", "error": error_msg}
        
    except Exception as e:
        error_msg = f"Upload error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "message": "Upload failed", "error": error_msg}


async def upload_sales_db(db_path: str = 'sales_data.db') -> dict:
    """
    Upload sales database to MongoDB vc_aly collection.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        dict: {"success": bool, "message": str, "error": str (optional)}
    """
    try:
        if not os.path.exists(db_path):
            return {"success": False, "message": "Database not found", "error": f"Database file not found: {db_path}"}
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Extract data from all tables
        db_data = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Convert to list of dictionaries
            db_data[table_name] = [
                dict(zip(columns, row)) for row in rows
            ]
        
        conn.close()
        
        # Prepare payload
        payload = {
            "database_name": os.path.basename(db_path),
            "upload_timestamp": datetime.now().isoformat(),
            "tables": db_data,
            "total_tables": len(db_data)
        }
        
        # Upload to MongoDB
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                SALES_URL,
                headers=HEADERS,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Database uploaded to MongoDB: {len(db_data)} tables")
                for table_name, records in db_data.items():
                    print(f"   📊 {table_name}: {len(records)} records")
                return {
                    "success": True,
                    "message": "Database uploaded successfully",
                    "tables_count": len(db_data)
                }
            else:
                error_msg = f"API returned status {response.status_code}: {response.text[:200]}"
                print(f"❌ Database upload failed: {error_msg}")
                return {
                    "success": False,
                    "message": "Upload failed",
                    "error": error_msg
                }
                
    except httpx.TimeoutException:
        error_msg = "Upload timeout - API did not respond in time"
        print(f"❌ {error_msg}")
        return {"success": False, "message": "Upload timeout", "error": error_msg}
        
    except Exception as e:
        error_msg = f"Upload error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "message": "Upload failed", "error": error_msg}


async def upload_report_file(report_path: str, metadata: dict = None) -> dict:
    """
    Upload a single report file to MongoDB vc_rep collection.
    
    Args:
        report_path: Path to the report file
        metadata: Optional metadata dictionary to include in upload
        
    Returns:
        dict: {"success": bool, "message": str, "error": str (optional)}
    """
    try:
        if not os.path.exists(report_path):
            return {"success": False, "message": "Report not found", "error": f"Report file not found: {report_path}"}
        
        # Read report content (for text files)
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
        except:
            # If text reading fails, read as binary and encode
            with open(report_path, 'rb') as f:
                report_data = f.read()
                report_content = base64.b64encode(report_data).decode('utf-8')
        
        filename = os.path.basename(report_path)
        
        # Prepare payload
        payload = {
            "filename": filename,
            "file_size": len(report_content),
            "report_content": report_content,
            "upload_timestamp": datetime.now().isoformat(),
            "file_type": os.path.splitext(filename)[1]
        }
        
        # Add metadata if provided
        if metadata:
            payload.update(metadata)
        
        # Upload to MongoDB
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                REPORT_URL,
                headers=HEADERS,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Report uploaded to MongoDB: {filename}")
                return {
                    "success": True,
                    "message": "Report uploaded successfully",
                    "filename": filename
                }
            else:
                error_msg = f"API returned status {response.status_code}: {response.text[:200]}"
                print(f"❌ Report upload failed: {error_msg}")
                return {
                    "success": False,
                    "message": "Upload failed",
                    "error": error_msg
                }
                
    except httpx.TimeoutException:
        error_msg = "Upload timeout - API did not respond in time"
        print(f"❌ {error_msg}")
        return {"success": False, "message": "Upload timeout", "error": error_msg}
        
    except Exception as e:
        error_msg = f"Upload error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "message": "Upload failed", "error": error_msg}


# Batch upload functions for backward compatibility
async def upload_all_audio_files(audio_dir: str = 'WAV') -> dict:
    """Upload all audio files from a directory."""
    audio_path = Path(audio_dir)
    if not audio_path.exists():
        return {"success": False, "message": "Directory not found"}
    
    audio_files = list(audio_path.glob('*.wav')) + list(audio_path.glob('*.mp3'))
    
    results = []
    for audio_file in audio_files:
        result = await upload_audio_file(str(audio_file))
        results.append(result)
    
    successful = sum(1 for r in results if r.get("success"))
    return {
        "success": successful > 0,
        "message": f"Uploaded {successful}/{len(results)} audio files",
        "results": results
    }


async def upload_all_reports(reports_dir: str = 'reports') -> dict:
    """Upload all report files from a directory."""
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        return {"success": False, "message": "Directory not found"}
    
    report_files = list(reports_path.glob('*.txt')) + list(reports_path.glob('*.json')) + list(reports_path.glob('*.pdf'))
    
    results = []
    for report_file in report_files:
        result = await upload_report_file(str(report_file))
        results.append(result)
    
    successful = sum(1 for r in results if r.get("success"))
    return {
        "success": successful > 0,
        "message": f"Uploaded {successful}/{len(results)} reports",
        "results": results
    }


# CLI utility for manual uploads
async def upload_all():
    """Upload all data: audio files, sales database, and reports"""
    print("\n" + "="*60)
    print("MONGODB UPLOAD UTILITY")
    print("="*60)
    print(f"Base URL: {API_BASE_URL}")
    print(f"User ID: {API_UID}")
    print("="*60)
    
    # Upload audio files
    print(f"\n{'='*60}")
    print("UPLOADING AUDIO FILES")
    print(f"{'='*60}")
    await upload_all_audio_files()
    
    # Upload sales database
    print(f"\n{'='*60}")
    print("UPLOADING SALES DATABASE")
    print(f"{'='*60}")
    await upload_sales_db()
    
    # Upload reports
    print(f"\n{'='*60}")
    print("UPLOADING REPORTS")
    print(f"{'='*60}")
    await upload_all_reports()
    
    print(f"\n{'='*60}")
    print("UPLOAD COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(upload_all())
