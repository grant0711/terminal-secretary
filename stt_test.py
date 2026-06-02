import os
import queue
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import collections

class TranscriptionEngine:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        print(f"Loading Whisper model '{model_size}' on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.audio_queue = queue.Queue()
        self.fs = 16000
        self.chunk_duration = 0.5 # seconds
        self.chunk_samples = int(self.fs * self.chunk_duration)

    def transcribe_chunk(self, audio_data):
        # faster-whisper expects a float32 numpy array
        segments, info = self.model.transcribe(audio_data, beam_size=5)
        text = ""
        for segment in segments:
            text += segment.text
        return text.strip()

    def run_live(self, device_index=9):
        print("Starting live transcription... Press Ctrl+C to stop.")
        
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self.audio_queue.put(indata.copy())

        with sd.InputStream(samplerate=self.fs, 
                            channels=1, 
                            device=device_index, 
                            callback=callback, 
                            blocksize=self.chunk_samples):
            
            aggregated_audio = []
            while True:
                try:
                    chunk = self.audio_queue.get()
                    aggregated_audio.append(chunk)
                    
                    # Process every 3 seconds of audio for better context
                    if len(aggregated_audio) >= 6: 
                        audio_to_process = np.concatenate(aggregated_audio).flatten()
                        text = self.transcribe_chunk(audio_to_process)
                        if text:
                            print(f"Transcript: {text}")
                        aggregated_audio = [] # Reset after processing
                except KeyboardInterrupt:
                    break

if __name__ == "__main__":
    # Test script
    engine = TranscriptionEngine(model_size="tiny") # Use tiny for faster testing
    # We should ensure the default source is set to MIC for this test
    engine.run_live(device_index=9)
