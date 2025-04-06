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
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import logging
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)
import threading
import asyncio

load_dotenv()

ELEVENLABS_API_KEY = 'sk_a50620c06ec84b0dc46ab3fce3281212b941e16e0915d545'
DEEPGRAM_API_KEY = "f4082955916ed6ca9eacd3fd2c7ae127a1e4516c"
# deepgram = DeepgramClient(DEEPGRAM_API_KEY)


client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

# Initialize Deepgram Client
deepgram: DeepgramClient = DeepgramClient(DEEPGRAM_API_KEY)
# Shared variable for storing the interim result
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
        with open(file_path, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        options = PrerecordedOptions(
            smart_format=True,
            summarize="v2",
        )

        # Call Deepgram API to transcribe the file
        file_response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        json_response = file_response  # Assuming the response is a JSON-like dict

        # Extract transcription text from the response
        transcript = json_response["results"]["channels"][0]["alternatives"][0]["transcript"]
        print(f"📝 Transcribed Text: {transcript}")
        return transcript

    except Exception as e:
        print(f"❌ Deepgram Exception: {e}")
        return None

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

def speak(text):
    
    audio = client.text_to_speech.convert(
    text=text,
    # voice_id="19STyYD15bswVz51nqLf",
    voice_id='EXAVITQu4vr4xnSDxMaL',
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",)
    play(audio)
