import argparse
import sys
import time
import os
import re
import numpy as np
import threading
import queue
from datetime import datetime, timedelta
from audio import AudioInterceptor
from stt import STTEngine
from llm import Summarizer
from db import DatabaseManager

class TerminalSecretary:
    def __init__(self, mode="record"):
        self.db = DatabaseManager()
        self.summarizer = Summarizer(model=os.getenv("SUMMARIZER_MODEL", "llama3"))
        
        # Only init STT and Audio if recording
        if mode == "record":
            model_size = os.getenv("MODEL_SIZE", "small")
            self.stt = STTEngine(model_size=model_size)
            # Using custom ALSA device names defined dynamically in /etc/asound.conf
            self.mic = "mic"
            self.monitor = "monitor"
            self.audio = AudioInterceptor(self.mic, self.monitor)
        
        self.transcript_buffer = []
        self.audio_processing_queue = queue.Queue()
        self.is_recording = False
        self.stop_event = threading.Event()

    def record(self):
        if not hasattr(self, 'audio') or not self.audio.setup():
            print("Audio setup failed. Ensure you are in record mode.")
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
                pass 

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
                    chunk = audio_ingestion_queue.get(timeout=0.1)
                    
                    # Signal visualization (max RMS across channels)
                    rms = np.sqrt(np.mean(chunk**2))
                    bar_len = int(min(rms * 500, 50))
                    bar = '*' * bar_len
                    print(f"Signal: {rms:.4f} |{bar:<50}|", end="\r")

                    current_buffer.append(chunk)
                    samples_in_buffer += len(chunk)
                    
                    if samples_in_buffer >= target_samples:
                        audio_to_process = np.concatenate(current_buffer, axis=0)
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
                
                conv_id = self.db.save_conversation(full_transcript, summary)
                print(f"\nConversation saved (ID: {conv_id}).")
                
                # Extract and save tasks
                self._extract_tasks(summary, conv_id)
            else:
                print("No speech detected. Nothing to save.")
            
            self.audio.cleanup()

    def _extract_tasks(self, summary, conv_id):
        """Parses the summary for - [ACTION]: items and saves them as todos."""
        tasks = re.findall(r'^- \[ACTION\]: (.*)', summary, re.MULTILINE)
        if tasks:
            print(f"\nExtracted {len(tasks)} tasks:")
            for task in tasks:
                self.db.add_todo(task.strip(), conversation_id=conv_id)
                print(f"  - [ ] {task.strip()}")

    def _transcription_loop(self):
        """Background thread to handle heavy STT processing for both channels."""
        while not self.stop_event.is_set() or not self.audio_processing_queue.empty():
            try:
                audio_data = self.audio_processing_queue.get(timeout=1.0)
                
                # Split channels (Mic is channel 0, Monitor is channel 1)
                mic_data = audio_data[:, 0]
                mon_data = audio_data[:, 1]
                
                mic_rms = np.sqrt(np.mean(mic_data**2))
                mon_rms = np.sqrt(np.mean(mon_data**2))
                
                # Process Mic
                if mic_rms > 0.005:
                    print(f"\n[Processing ME 10s... Signal: {mic_rms:.4f}]")
                    mic_text = self.stt.transcribe(mic_data)
                    if mic_text:
                        print(f"[ME]: {mic_text}")
                        self.transcript_buffer.append(f"[ME]: {mic_text}")
                
                # Process Monitor
                if mon_rms > 0.005:
                    print(f"\n[Processing OTHERS 10s... Signal: {mon_rms:.4f}]")
                    mon_text = self.stt.transcribe(mon_data)
                    if mon_text:
                        print(f"[OTHERS]: {mon_text}")
                        self.transcript_buffer.append(f"[OTHERS]: {mon_text}")
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"\nTranscription Error: {e}")

    def todo_list(self, show_all=False):
        status = None if show_all else "pending"
        todos = self.db.get_todos(status=status)
        if not todos:
            print("No tasks found.")
            return

        print(f"\n--- {'All' if show_all else 'Pending'} Tasks ---")
        for t in todos:
            check = "[x]" if t[2] == "done" else "[ ]"
            print(f"{t[0]:>3}. {check} {t[1]} ({t[3][:16]})")

    def todo_add(self, text):
        todo_id = self.db.add_todo(text)
        print(f"Added task {todo_id}: {text}")

    def todo_done(self, todo_id):
        self.db.mark_todo_done(todo_id)
        print(f"Marked task {todo_id} as done.")

    def todo_rm(self, todo_id):
        self.db.remove_todo(todo_id)
        print(f"Removed task {todo_id}.")

    def review(self, timeframe):
        now = datetime.now()
        if timeframe == "yesterday":
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')
            end = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59).strftime('%Y-%m-%d %H:%M:%S')
        elif timeframe == "week":
            start = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
            end = now.strftime('%Y-%m-%d %H:%M:%S')
        else:
            print("Invalid timeframe. Use 'yesterday' or 'week'.")
            return

        conversations = self.db.get_conversations_in_range(start, end)
        if not conversations:
            print(f"No conversations found for {timeframe}.")
            return

        print(f"\nGenerating synthesized review for {timeframe}...")
        review_text = self.summarizer.generate_review(conversations, timeframe)
        print(f"\n--- {timeframe.upper()} REVIEW ---")
        print(review_text)

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
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Record
    subparsers.add_parser("record", help="Start capturing audio")

    # Search
    search_parser = subparsers.add_parser("search", help="Search history")
    search_parser.add_argument("query", help="Search query")

    # Todo
    todo_parser = subparsers.add_parser("todo", help="Manage tasks")
    todo_subparsers = todo_parser.add_subparsers(dest="todo_command", help="Todo sub-commands")
    
    list_parser = todo_subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--all", action="store_true", help="Show all tasks including done")
    
    add_parser = todo_subparsers.add_parser("add", help="Add a task manually")
    add_parser.add_argument("text", help="Task description")
    
    done_parser = todo_subparsers.add_parser("done", help="Mark task as done")
    done_parser.add_argument("id", type=int, help="Task ID")
    
    rm_parser = todo_subparsers.add_parser("rm", help="Remove a task")
    rm_parser.add_argument("id", type=int, help="Task ID")

    # Review
    review_parser = subparsers.add_parser("review", help="Generate activity review")
    review_parser.add_argument("timeframe", choices=["yesterday", "week"], help="Timeframe for review")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    app = TerminalSecretary(mode=args.command)
    
    if args.command == "record":
        app.record()
    elif args.command == "search":
        app.search(args.query)
    elif args.command == "todo":
        if args.todo_command == "list":
            app.todo_list(show_all=args.all)
        elif args.todo_command == "add":
            app.todo_add(args.text)
        elif args.todo_command == "done":
            app.todo_done(args.id)
        elif args.todo_command == "rm":
            app.todo_rm(args.id)
        else:
            todo_parser.print_help()
    elif args.command == "review":
        app.review(args.timeframe)

if __name__ == "__main__":
    main()
