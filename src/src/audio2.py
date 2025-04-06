#this is a deepgram tts with ElevenLabs integration

# audio.py

import pyaudio
import wave
import tempfile
import pyttsx3
from deepgram import DeepgramClient, FileSource, PrerecordedOptions, SpeakOptions
import numpy as np
from collections import deque
import webrtcvad
import time
import speech_recognition as sr
import simpleaudio as sa
import pygame
from PyQt5.QtCore import QThread, pyqtSignal
import os
import importlib.util

# --- Configuration and Initialization ---

# Use your hard-coded Deepgram API key
DEEPGRAM_API_KEY = ""
deepgram = DeepgramClient(DEEPGRAM_API_KEY)
filename = "test.mp3"

# Initialize the text-to-speech engine
engine = pyttsx3.init()

# Check if ElevenLabs module is available
USE_ELEVEN_LABS = False
try:
    # Try different import methods
    eleven_labs_spec = importlib.util.find_spec("eleven_labs", ["References"])
    if eleven_labs_spec:
        from References import eleven_labs
        USE_ELEVEN_LABS = True
    else:
        # Try as a direct module
        eleven_labs_spec = importlib.util.find_spec("eleven_labs")
        if eleven_labs_spec:
            import eleven_labs
            USE_ELEVEN_LABS = True
    
    if USE_ELEVEN_LABS:
        print("✅ ElevenLabs TTS module loaded successfully!")
except ImportError as e:
    print(f"ElevenLabs TTS module not available: {e}")
    print("Using Deepgram TTS as fallback")

# --- Text-to-Speech Function ---

def speak(text):
    """Convert text to speech and play it"""
    if not text or text.strip() == "":
        print("Warning: Empty text provided to speak function")
        return
        
    print(f"Speaking: '{text}'")
    
    if USE_ELEVEN_LABS:
        try:
            # Use ElevenLabs for text-to-speech
            print(f"🔊 Using ElevenLabs TTS")
            success = eleven_labs.speak(text)
            if not success:
                raise Exception("ElevenLabs TTS failed")
            return
        except Exception as e:
            print(f"🚨 ElevenLabs TTS error: {e}")
            print("Falling back to Deepgram TTS")
            # Fall back to Deepgram if ElevenLabs fails
    
    # Use Deepgram as primary or fallback
    _speak_deepgram(text)

def _speak_deepgram(text):
    """Original Deepgram TTS implementation"""
    try:
        # STEP 1: Initialize Deepgram Client
        deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        SPEAK_TEXT = {"text": text}
        # STEP 2: Define TTS options
        options = SpeakOptions(
            model="aura-luna-en",  # Specify the Deepgram voice model
        )

        # STEP 3: Call the save method with correct arguments
        response = deepgram.speak.rest.v("1").save(filename, SPEAK_TEXT, options)

        print(response.to_json(indent=4))
        print(f"✅ Speech saved as {filename}")

         # STEP 4: Play the generated speech file
        play_mp3(filename)

    except Exception as e:
        print(f"🚨 Deepgram Exception: {e}")
        # Fall back to pyttsx3 if all else fails
        try:
            engine.say(text)
            engine.runAndWait()
        except:
            print("🚨 All TTS methods failed")

def play_mp3(file_path):
    """
    Plays an MP3 file using pygame.
    """
    try:
        
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        print("🔊 Playing MP3...")

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)  # Keeps playing until the file ends

        print("🔊 Audio playback complete.")

        pygame.mixer.music.unload()

    except Exception as e:
        print(f"🚨 Error playing MP3: {e}")

def record_audio(samplerate=16000, channels=1, chunk=320, silence_duration=1.5):
    """
    Records audio from the microphone and stops when silence is detected.

    Parameters:
      - samplerate: The sample rate for recording (must be 8000, 16000, 32000, or 48000).
      - channels: Number of audio channels (must be 1 for VAD).
      - chunk: The number of frames per buffer (must align with 10ms audio length for VAD).
      - silence_duration: Time (in seconds) of silence required to stop recording.

    Returns:
      The filename of the recorded WAV file.
    """
    print("🎤 Listening... Speak now!")

    # Initialize PyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=samplerate,
                    input=True,
                    frames_per_buffer=chunk)

    # Initialize WebRTC VAD
    vad = webrtcvad.Vad()
    vad.set_mode(3)  # Most aggressive mode for speech detection

    frames = []
    silence_count = 0
    silence_threshold = int(silence_duration * samplerate / chunk)  # Convert silence time to chunks

    while True:
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        
        # Convert audio to PCM16 little-endian format
        pcm_data = np.frombuffer(data, dtype=np.int16)

        # Check VAD only if chunk size aligns with 10ms audio length
        is_speech = vad.is_speech(pcm_data.tobytes(), samplerate)

        if is_speech:
            silence_count = 0  # Reset silence count when speech is detected
        else:
            silence_count += 1  # Increment silence count when no speech is detected

        if silence_count > silence_threshold:
            print("⏹️ Silence detected, stopping recording.")
            break

    # Cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save to a temporary WAV file
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    with wave.open(temp_wav.name, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(samplerate)
        wf.writeframes(b''.join(frames))

    print(f"✅ Audio recorded: {temp_wav.name}")
    return temp_wav.name


def transcribe_audio(file_path):
    """
    Transcribes the recorded audio file using Deepgram's API.
    
    Parameters:
      - file_path: The path to the audio file to transcribe.
    
    Returns:
      The transcribed text, or None if an error occurs.
    """
    try:
        print(f"Opening audio file for transcription: {file_path}")
        
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            return None
            
        # Check if file is empty
        if os.path.getsize(file_path) == 0:
            print(f"Audio file is empty: {file_path}")
            return None
        
        with open(file_path, "rb") as file:
            buffer_data = file.read()
            print(f"Read {len(buffer_data)} bytes from audio file")
            
            if len(buffer_data) == 0:
                print("Audio buffer is empty")
                return None

        payload: FileSource = {
            "buffer": buffer_data,
        }

        options = PrerecordedOptions(
            smart_format=True,
            model="nova-2",  # Use nova-2 model for better accuracy
            detect_language=True,
        )

        # Call Deepgram API to transcribe the file
        print("Calling Deepgram API for transcription...")
        file_response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        # Convert response to dictionary if it's not already
        if hasattr(file_response, 'to_dict'):
            json_response = file_response.to_dict()
        else:
            json_response = file_response
            
        print(f"Raw Deepgram response: {json_response}")

        # Extract transcription text from the response using safe navigation
        try:
            # Check if the response has the expected structure
            if not json_response:
                print("Empty response from Deepgram")
                return "No transcription available"
                
            if "results" not in json_response:
                print("No results field in Deepgram response")
                return "No results in transcription"
                
            if "channels" not in json_response["results"]:
                print("No channels field in Deepgram results")
                return "No channels in transcription"
                
            channels = json_response["results"]["channels"]
            if not channels or len(channels) == 0:
                print("Empty channels list in Deepgram results")
                return "No channel data in transcription"
                
            alternatives = channels[0].get("alternatives", [])
            if not alternatives or len(alternatives) == 0:
                print("No alternatives in first channel")
                return "No transcription alternatives"
                
            transcript = alternatives[0].get("transcript", "").strip()
            if not transcript:
                print("Empty transcript in first alternative")
                return "Empty transcription"
                
            print(f"📝 Transcribed Text: {transcript}")
            return transcript
        except KeyError as ke:
            print(f"KeyError in Deepgram response processing: {ke}")
            print(f"Response structure: {json_response}")
            return "Error processing transcription"
        except Exception as e:
            print(f"Error extracting transcript from response: {e}")
            return "Error extracting transcription"

    except Exception as e:
        print(f"❌ Deepgram Exception: {e}")
        print(f"Exception type: {type(e).__name__}")
        if hasattr(e, "__dict__"):
            print(f"Exception details: {e.__dict__}")
        return "Error during transcription"

def listen():
    """
    Records audio from the microphone and returns the transcribed text.
    
    Returns:
      The transcribed text as a string, or an empty string on failure.
    """
    audio_file = record_audio()
    if audio_file:
        transcript = transcribe_audio(audio_file)
        return transcript if transcript else ""
    return ""


