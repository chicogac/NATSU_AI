#!/usr/bin/env python3
"""
ElevenLabs TTS Integration Module for Natsu AI
This module provides functions to generate speech using ElevenLabs' text-to-speech API.
"""

import os
import requests
import json
import base64
import asyncio
import websockets
import wave
from io import BytesIO
import tempfile
import time
import logging
from pathlib import Path
import importlib.util

# Check if playsound is available
playsound_available = importlib.util.find_spec("playsound") is not None
if playsound_available:
    import playsound
else:
    print("Warning: playsound library not found, audio playback will not be available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eleven_labs")

# Constants
API_KEY = "d7ec9c6eab254747e8a6c20b56a36d5a"  # API key from user
API_URL = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Default voice (Rachel)
AUDIO_FORMAT = "mp3"  # Output format (mp3, mp3_44100_128, pcm_16000, pcm_22050, pcm_24000, pcm_44100)
OUTPUT_DIR = tempfile.gettempdir()  # Directory to save audio files

# Remove conflicting API key 
# ELEVEN_LABS_API_KEY = "sk_4fc509fd5d656cf82a5de6bb245eef2ca293612fe3ac76a7"
WEBSOCKET_URL = "wss://api.elevenlabs.io/v1/text-to-speech"

# Default voice settings
DEFAULT_MODEL_ID = "eleven_monolingual_v1"
DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY_BOOST = 0.8
DEFAULT_STYLE = 0.0
DEFAULT_SPEED = 1.0

def get_headers():
    """Get the HTTP headers needed for API requests"""
    return {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def list_available_voices():
    """List all available voices from ElevenLabs API"""
    try:
        response = requests.get(f"{API_URL}/voices", headers=get_headers())
        response.raise_for_status()
        return response.json().get("voices", [])
    except Exception as e:
        logger.error(f"Error fetching voices: {e}")
        return []

def get_voice_info(voice_id=DEFAULT_VOICE_ID):
    """Get information about a specific voice"""
    try:
        response = requests.get(f"{API_URL}/voices/{voice_id}", headers=get_headers())
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching voice info: {e}")
        return None

def text_to_speech(text, voice_id=DEFAULT_VOICE_ID, output_path=None, model_id="eleven_monolingual_v1"):
    """
    Generate speech from text using ElevenLabs API
    
    Args:
        text (str): The text to convert to speech
        voice_id (str): The voice ID to use
        output_path (str, optional): Path to save the audio file, if None a temp file is created
        model_id (str): The TTS model to use
        
    Returns:
        str: Path to the generated audio file, or None if failed
    """
    if not text.strip():
        logger.warning("Empty text provided, skipping TTS")
        return None
    
    # Prepare data for API request
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": DEFAULT_STABILITY,
            "similarity_boost": DEFAULT_SIMILARITY_BOOST,
            "style": DEFAULT_STYLE,
            "speed": DEFAULT_SPEED
        }
    }
    
    try:
        # Make API request
        response = requests.post(
            f"{API_URL}/text-to-speech/{voice_id}", 
            headers=get_headers(),
            json=data,
            params={"output_format": AUDIO_FORMAT}
        )
        response.raise_for_status()
        
        # Create output path if not provided
        if not output_path:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{AUDIO_FORMAT}", dir=OUTPUT_DIR)
            output_path = temp_file.name
            temp_file.close()
        
        # Save audio content to file
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        logger.info(f"Successfully generated speech, saved to {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        if "response" in locals() and hasattr(response, "text"):
            logger.error(f"API response: {response.text}")
        return None

def speak(text, voice_id=DEFAULT_VOICE_ID):
    """
    Convert text to speech and play it
    
    Args:
        text (str): The text to convert to speech
        voice_id (str): The voice ID to use
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        audio_file = text_to_speech(text, voice_id)
        if not audio_file:
            logger.error("Failed to generate speech")
            return False
        
        # Play the audio
        logger.info(f"Playing audio from {audio_file}")
        
        if playsound_available:
            playsound.playsound(audio_file)
        else:
            # Fallback to system commands
            if os.name == 'nt':  # Windows
                os.system(f'start {audio_file}')
            elif os.name == 'posix':  # Linux/Mac
                if os.uname().sysname == 'Darwin':
                    os.system(f'afplay {audio_file}')
                else:
                    os.system(f'mpg123 {audio_file}')
        
        # Clean up the temporary file
        try:
            os.unlink(audio_file)
        except Exception as e:
            logger.warning(f"Failed to delete temp file {audio_file}: {e}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in speak function: {e}")
        return False

def get_available_models():
    """Get list of available TTS models"""
    try:
        response = requests.get(f"{API_URL}/models", headers=get_headers())
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return []

async def text_to_speech_streaming(text, voice_id=DEFAULT_VOICE_ID, model_id=DEFAULT_MODEL_ID, output_path=None, buffer_size=1024):
    """
    Stream text to speech using WebSockets for real-time audio generation
    
    Args:
        text (str): Text to convert to speech
        voice_id (str): Voice ID to use
        model_id (str): Model ID to use
        output_path (str, optional): Path to save complete audio
        buffer_size (int): Size of audio chunks to process at once
        
    Returns:
        str or None: Path to saved audio file if output_path provided, otherwise None
    """
    ws_url = f"{WEBSOCKET_URL}/{voice_id}/stream-input?model_id={model_id}"
    
    audio_chunks = []
    
    async with websockets.connect(
        ws_url,
        extra_headers={"xi-api-key": ELEVEN_LABS_API_KEY}
    ) as websocket:
        # Send the initial message with voice settings
        await websocket.send(json.dumps({
            "text": " ",  # Empty initial text
            "voice_settings": {
                "stability": DEFAULT_STABILITY,
                "similarity_boost": DEFAULT_SIMILARITY_BOOST,
                "style": DEFAULT_STYLE,
                "speed": DEFAULT_SPEED
            }
        }))
        
        # Send the text to convert to speech
        await websocket.send(json.dumps({
            "text": text,
            "try_trigger_generation": True
        }))
        
        # Send empty text to signal the end of input
        await websocket.send(json.dumps({
            "text": ""
        }))
        
        # Receive and process audio chunks
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                
                if "audio" in data:
                    # Decode base64 audio data
                    audio_chunk = base64.b64decode(data["audio"])
                    audio_chunks.append(audio_chunk)
                    
                    # Process or play audio chunk here if needed
                    # For example, you could send it to an audio device for real-time playback
                    
                    # For debugging: Print chunk size
                    print(f"Received audio chunk: {len(audio_chunk)} bytes")
                
                # Check if this is the final message
                if len(audio_chunks) > 0 and ("audio" not in data or len(data.get("audio", "")) == 0):
                    break
                    
            except websockets.exceptions.ConnectionClosed:
                break
    
    # Combine all audio chunks
    full_audio = b''.join(audio_chunks)
    
    # Save to file if output path is provided
    if output_path and full_audio:
        with open(output_path, "wb") as f:
            f.write(full_audio)
        print(f"Audio saved to {output_path}")
        return output_path
    
    return full_audio if full_audio else None

# Simple voice selection function
def get_voice_id_by_name(voice_name):
    """Get voice ID by name"""
    voices = list_available_voices()
    for voice in voices:
        if voice["name"].lower() == voice_name.lower():
            return voice["voice_id"]
    
    # Default to Rachel if not found
    print(f"Voice '{voice_name}' not found, using default voice")
    return DEFAULT_VOICE_ID

# Example usage if run directly
if __name__ == "__main__":
    print("Testing ElevenLabs TTS...")
    
    # List available voices
    voices = list_available_voices()
    print(f"Found {len(voices)} voices")
    
    # Test TTS
    speak("Hello! This is a test of the ElevenLabs text to speech system. How does it sound?")
    
    # Test streaming (requires async context)
    async def test_streaming():
        await text_to_speech_streaming(
            "This is a test of streaming text to speech from ElevenLabs.",
            output_path="test_streaming.mp3"
        )
    
    # Uncomment to test streaming:
    # asyncio.run(test_streaming()) 