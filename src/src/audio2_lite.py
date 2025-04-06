# Simplified version of audio2.py with reduced dependencies
import os
import tempfile
from typing import Optional, Dict, Any

# Flag to indicate whether real functionality is available
HAS_DEEPGRAM = False
HAS_AUDIO = False

# Try to import core dependencies
try:
    from deepgram import DeepgramClient, SpeakOptions
    HAS_DEEPGRAM = True
    print("Deepgram SDK imported successfully")
except ImportError as e:
    print(f"Deepgram SDK import failed: {e}")

# Initialize Deepgram client if available
DEEPGRAM_API_KEY = ""
deepgram = None
if HAS_DEEPGRAM:
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        print("Deepgram client initialized successfully")
    except Exception as e:
        print(f"Deepgram client initialization failed: {e}")

# Fixed output filename
AUDIO_FILENAME = "test.mp3"

def speak(text: str) -> bool:
    """
    Text-to-speech function using Deepgram API.
    Returns True if successful, False otherwise.
    """
    if not HAS_DEEPGRAM or deepgram is None:
        print("Deepgram SDK not available, cannot generate speech")
        return False
        
    try:
        # Check if text exceeds the 2000 character limit
        if len(text) > 2000:
            print(f"Text exceeds 2000 character limit ({len(text)} chars). Truncating to first 1950 characters.")
            
            # Find a good truncation point at the end of a sentence
            truncated_text = text[:1950]
            last_period = max(truncated_text.rfind('.'), truncated_text.rfind('!'), truncated_text.rfind('?'))
            
            if last_period > 0:
                truncated_text = truncated_text[:last_period+1]
            
            text = truncated_text + " (Truncated due to length limits.)"
            print(f"Truncated text length: {len(text)} chars")
        
        # Prepare the text for TTS
        speak_text = {"text": text}
        
        # Define TTS options
        options = SpeakOptions(
            model="aura-luna-en",  # Specify the Deepgram voice model
        )

        # Call the save method to generate audio file
        response = deepgram.speak.rest.v("1").save(AUDIO_FILENAME, speak_text, options)
        print(f"✅ Speech saved as {AUDIO_FILENAME}")
        return True

    except Exception as e:
        print(f"🚨 Exception in speak function: {e}")
        return False

def transcribe_audio(file_path: str) -> str:
    """
    Transcribes the recorded audio file using Deepgram's API.
    
    Parameters:
      - file_path: The path to the audio file to transcribe.
    
    Returns:
      The transcribed text, or an error message if transcription fails.
    """
    if not HAS_DEEPGRAM or deepgram is None:
        return "Transcription not available (Deepgram SDK missing)"
        
    try:
        print(f"Opening audio file for transcription: {file_path}")
        
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            return "Audio file not found"
            
        # Check if file is empty
        if os.path.getsize(file_path) == 0:
            print(f"Audio file is empty: {file_path}")
            return "Audio file is empty"
        
        with open(file_path, "rb") as file:
            buffer_data = file.read()
            print(f"Read {len(buffer_data)} bytes from audio file")
            
            if len(buffer_data) == 0:
                print("Audio buffer is empty")
                return "Audio buffer is empty"

        # Create file source payload
        payload = {
            "buffer": buffer_data,
        }

        # Set options for transcription
        options = {
            "smart_format": True,
            "model": "nova-2",  # Use nova-2 model for better accuracy
            "detect_language": True,
        }

        # Call Deepgram API to transcribe the file
        print("Calling Deepgram API for transcription...")
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        # Process the response
        transcript = extract_transcript_from_response(response)
        return transcript

    except Exception as e:
        print(f"❌ Deepgram Exception: {e}")
        print(f"Exception type: {type(e).__name__}")
        return f"Error during transcription: {str(e)}"

def extract_transcript_from_response(response: Any) -> str:
    """Helper function to extract transcript from Deepgram response"""
    try:
        # Convert response to dictionary if it's not already
        if hasattr(response, 'to_dict'):
            json_response = response.to_dict()
        else:
            json_response = response
            
        print(f"Response structure: {json_response.keys() if hasattr(json_response, 'keys') else 'Not a dict'}")

        # Extract transcription text from the response using safe navigation
        if not json_response:
            return "Empty response from Deepgram"
            
        if "results" not in json_response:
            return "No results field in Deepgram response"
            
        if "channels" not in json_response["results"]:
            return "No channels field in Deepgram results"
            
        channels = json_response["results"]["channels"]
        if not channels or len(channels) == 0:
            return "No channel data in transcription"
            
        alternatives = channels[0].get("alternatives", [])
        if not alternatives or len(alternatives) == 0:
            return "No transcription alternatives"
            
        transcript = alternatives[0].get("transcript", "").strip()
        if not transcript:
            return "Empty transcription"
            
        print(f"📝 Transcribed Text: {transcript}")
        return transcript
        
    except Exception as e:
        print(f"Error extracting transcript: {e}")
        return "Error extracting transcription"

def listen() -> str:
    """
    This is a stub function since we're not using PyAudio in this lite version.
    Real audio recording should be done client-side.
    """
    return "Audio recording not available in lite version" 
