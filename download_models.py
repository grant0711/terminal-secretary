import torch
import os

# Pre-download Silero VAD model
print("Pre-downloading Silero VAD model...")
torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True, trust_repo=True)

# Pre-download Whisper model (faster-whisper handles this, but we can do it here)
from faster_whisper import WhisperModel
print("Pre-downloading Whisper model (base)...")
WhisperModel("base", device="cpu", compute_type="int8")
print("Pre-downloading Whisper model (small)...")
WhisperModel("small", device="cpu", compute_type="int8")
