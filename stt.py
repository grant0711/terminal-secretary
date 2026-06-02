import torch
from faster_whisper import WhisperModel
import numpy as np

class STTEngine:
    def __init__(self, model_size="small", device=None, compute_type="float16"):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # On Pascal (P5200), float16 is usually faster, but if it fails, int8 is safer.
        if device == "cpu":
            compute_type = "int8"
            
        print(f"Initializing STT Engine ({model_size}) on {device} ({compute_type})...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            print(f"Failed to load on {device}: {e}. Falling back to CPU.")
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def is_speech(self, audio_data, threshold=0.008):
        # Fallback simple energy check for the UI
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > threshold

    def transcribe(self, audio_data):
        # Use faster-whisper's built-in VAD filter and suppression settings
        segments, _ = self.model.transcribe(
            audio_data, 
            beam_size=5, 
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            # Important to prevent repeating same phrase
            condition_on_previous_text=False,
            # Helps ignore low-confidence noise
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0
        )
        return " ".join([segment.text for segment in segments]).strip()
