import os
import wave
from google.cloud import speech
from google.cloud.speech_v1 import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Google Cloud credentials
credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
if os.path.exists(credentials_path):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
else:
    print(f"Warning: Google Cloud credentials file not found at {credentials_path}")

def transcribe_audio_direct(file_path, progress_callback=None):
    """
    Transcribes an audio file. 
    - If WAV and > 10MB, splits into chunks.
    - If MP3, uses MP3 encoding.
    - Otherwise tries direct send (limit 10MB).
    """
    print(f"Processing audio file: {file_path}")
    if progress_callback:
        progress_callback("Initializing transcription service...")
        
    client = speech.SpeechClient()
    
    # Check for MP3
    if file_path.lower().endswith(".mp3"):
        print("Detected MP3 file. Using MP3 encoding...")
        if progress_callback:
            progress_callback("Detected MP3. Starting long-running transcription...")
            
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
            
        audio = types.RecognitionAudio(content=content)
        config = types.RecognitionConfig(
            encoding=types.RecognitionConfig.AudioEncoding.MP3,
            language_code="ta-IN"
        )
        
        # Use long_running for potentially large MP3s
        print("Starting MP3 transcription...")
        operation = client.long_running_recognize(config=config, audio=audio)
        
        if progress_callback:
            progress_callback("Processing MP3 audio (this may take a while)...")
            
        response = operation.result()
        
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
        return transcript.strip()

    # Try processing as WAV first
    try:
        with wave.open(file_path, "rb") as wf:
            print("Detected WAV file. Checking size/duration...")
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            total_frames = wf.getnframes()
            duration = total_frames / float(sample_rate)
            
            # Check Limits: Sync recognize limit is ~60s
            file_size = os.path.getsize(file_path)
            
            if duration < 59 and file_size < 9 * 1024 * 1024:
                print(f"Short audio ({duration:.2f}s), sending directly...")
                if progress_callback:
                    progress_callback("Processing short audio...")
                    
                wf.rewind()
                frames = wf.readframes(total_frames)
                audio = types.RecognitionAudio(content=frames)
                config = types.RecognitionConfig(
                    encoding=types.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=sample_rate,
                    language_code="ta-IN",
                    audio_channel_count=channels
                )
                response = client.recognize(config=config, audio=audio)
                transcript = " ".join([result.alternatives[0].transcript for result in response.results])
                return transcript.strip()
            
            # If large, chunk it
            print(f"Large WAV file ({file_size/1024/1024:.2f} MB, {duration:.2f}s). Chunking...")
            if progress_callback:
                progress_callback(f"Large file detected ({duration:.0f}s). Splitting into chunks...")
            
            chunk_duration = 50 # seconds
            frames_per_chunk = int(sample_rate * chunk_duration)
            full_transcript = []
            
            total_chunks = int(total_frames / frames_per_chunk) + 1
            
            wf.rewind()
            chunk_idx = 0
            while True:
                frames = wf.readframes(frames_per_chunk)
                if not frames:
                    break
                
                # Check if chunk is empty
                if len(frames) == 0:
                    break
                
                chunk_idx += 1
                if progress_callback:
                    progress_callback(f"Transcribing chunk {chunk_idx}/{total_chunks}...")

                audio = types.RecognitionAudio(content=frames)
                config = types.RecognitionConfig(
                    encoding=types.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=sample_rate,
                    language_code="ta-IN",
                    audio_channel_count=channels
                )
                
                try:
                    print("Transcribing chunk...")
                    response = client.recognize(config=config, audio=audio)
                    for result in response.results:
                        full_transcript.append(result.alternatives[0].transcript)
                except Exception as e:
                    print(f"Chunk transcription error: {e}")
                    
            return " ".join(full_transcript).strip()

    except wave.Error:
        print("Not a valid WAV file or header issue. Falling back to raw read...")
    except Exception as e:
        print(f"WAV processing error: {e}. Falling back...")

    # Fallback for non-WAV or failed WAV processing
    with open(file_path, "rb") as audio_file:
        content = audio_file.read()
        
    if len(content) > 10 * 1024 * 1024:
        raise Exception("File too large (>10MB) and not a valid WAV for chunking. Please convert to WAV or use a smaller file.")

    audio = types.RecognitionAudio(content=content)
    config = types.RecognitionConfig(
        encoding=types.RecognitionConfig.AudioEncoding.LINEAR16, 
        language_code="ta-IN", 
    )

    print("Starting transcription (direct fallback)...")
    if progress_callback:
        progress_callback("Starting fallback transcription...")
        
    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result()
    
    transcript = ""
    for result in response.results:
        transcript += result.alternatives[0].transcript + " "
        
    return transcript.strip()
