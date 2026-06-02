import argparse
import sys
import time
import os
import numpy as np
import threading
import queue
from audio import AudioInterceptor
from stt import STTEngine
from llm import Summarizer
from db import DatabaseManager

class TerminalSecretary:
    def __init__(self):
        self.db = DatabaseManager()
        model_size = os.getenv("MODEL_SIZE", "small")
        self.stt = STTEngine(model_size=model_size)
        
        summarizer_model = os.getenv("SUMMARIZER_MODEL", "llama3")
        self.summarizer = Summarizer(model=summarizer_model)
        
        # Using custom ALSA device names defined dynamically in /etc/asound.conf
        self.mic = "mic"
        self.monitor = "monitor"
        self.audio = AudioInterceptor(self.mic, self.monitor)
        
        self.transcript_buffer = []
        self.audio_processing_queue = queue.Queue()
        self.is_recording = False
        self.stop_event = threading.Event()

    def record(self):
        if not self.audio.setup():
            return

        print("\n--- Recording Started ---")
        print("Listening for conversation... (Press Ctrl+C to stop and summarize)")
        
        audio_ingestion_queue = queue.Queue(maxsize=1000)
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"Audio Status: {status}")
            try:
                audio_ingestion_queue.put_nowait(indata.copy())
            except queue.Full:
                pass # Prevent memory explosion if processing hangs

        # Start transcription thread
        transcription_thread = threading.Thread(target=self._transcription_loop)
        transcription_thread.start()

        self.audio.start_stream(audio_callback)
        self.is_recording = True
        
        samples_in_buffer = 0
        target_samples = self.audio.fs * 10 # 10 seconds
        current_buffer = []
        
        try:
            while self.is_recording:
                try:
                    chunk = audio_ingestion_queue.get(timeout=0.1).flatten()
                    
                    # Signal visualization
                    rms = np.sqrt(np.mean(chunk**2))
                    bar_len = int(min(rms * 500, 50))
                    bar = '*' * bar_len
                    print(f"Signal: {rms:.4f} |{bar:<50}|", end="\r")

                    current_buffer.append(chunk)
                    samples_in_buffer += len(chunk)
                    
                    if samples_in_buffer >= target_samples:
                        audio_to_process = np.concatenate(current_buffer)
                        self.audio_processing_queue.put(audio_to_process)
                        current_buffer = []
                        samples_in_buffer = 0
                except queue.Empty:
                    continue
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.is_recording = False
            self.stop_event.set()
            self.audio.stop_stream()
            
            # Process remaining audio
            if current_buffer:
                self.audio_processing_queue.put(np.concatenate(current_buffer))
            
            print("Waiting for final transcription to complete...")
            transcription_thread.join(timeout=30)
            
            full_transcript = " ".join(self.transcript_buffer)
            if full_transcript.strip():
                print("\nGenerating summary with Ollama...")
                summary = self.summarizer.summarize(full_transcript)
                print(f"\nSummary:\n{summary}")
                
                self.db.save_conversation(full_transcript, summary)
                print("\nConversation saved to database.")
            else:
                print("No speech detected. Nothing to save.")
            
            self.audio.cleanup()

    def _transcription_loop(self):
        """Background thread to handle heavy STT processing."""
        while not self.stop_event.is_set() or not self.audio_processing_queue.empty():
            try:
                audio_data = self.audio_processing_queue.get(timeout=1.0)
                total_rms = np.sqrt(np.mean(audio_data**2))
                
                if total_rms > 0.005:
                    # This print is now thread-safe but might overlap with the signal meter
                    # We'll use a newline to clear the meter
                    print(f"\n[Processing 10s segment... Avg Signal: {total_rms:.4f}]")
                    text = self.stt.transcribe(audio_data)
                    if text:
                        print(f"[Captured]: {text}")
                        self.transcript_buffer.append(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"\nTranscription Error: {e}")

    def search(self, query):
        print(f"Searching for: '{query}'...")
        results = self.db.search(query)
        
        if not results['documents'] or not results['documents'][0]:
            print("No matching conversations found.")
            return

        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            print(f"\n--- Result {i+1} (Date: {metadata['timestamp']}) ---")
            print(f"Summary: {doc}")

def main():
    parser = argparse.ArgumentParser(description="Terminal Secretary")
    parser.add_argument("command", choices=["record", "search"], help="Command to run")
    parser.add_argument("query", nargs="?", help="Search query")
    
    args = parser.parse_args()
    
    app = TerminalSecretary()
    
    if args.command == "record":
        app.record()
    elif args.command == "search":
        if not args.query:
            print("Please provide a search query.")
        else:
            app.search(args.query)

if __name__ == "__main__":
    main()
