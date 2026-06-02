import sounddevice as sd
import numpy as np
import queue
import threading

class AudioInterceptor:
    def __init__(self, mic_name, monitor_name, fs=16000):
        self.mic_name = mic_name
        self.monitor_name = monitor_name
        self.fs = fs
        # Limit queue sizes to prevent memory leaks if one stream fails
        self.mic_queue = queue.Queue(maxsize=100)
        self.mon_queue = queue.Queue(maxsize=100)
        self.is_running = False

    def setup(self):
        print(f"Initializing non-intrusive capture...")
        print(f"  Mic: {self.mic_name}")
        print(f"  Monitor: {self.monitor_name}")
        return True

    def cleanup(self):
        self.stop_stream()

    def _mic_callback(self, indata, frames, time, status):
        if status:
            print(f"Mic Status: {status}")
        try:
            self.mic_queue.put_nowait(indata.copy())
        except queue.Full:
            pass # Drop frames if we fall behind

    def _mon_callback(self, indata, frames, time, status):
        if status:
            print(f"Monitor Status: {status}")
        try:
            self.mon_queue.put_nowait(indata.copy())
        except queue.Full:
            pass # Drop frames if we fall behind

    def start_stream(self, combined_callback):
        self.is_running = True
        
        try:
            self.mic_stream = sd.InputStream(samplerate=self.fs, channels=1, 
                                            device=self.mic_name, callback=self._mic_callback)
            self.mon_stream = sd.InputStream(samplerate=self.fs, channels=1, 
                                            device=self.monitor_name, callback=self._mon_callback)
            
            self.mic_stream.start()
            self.mon_stream.start()
            
            self.mixer_thread = threading.Thread(target=self._mixer_loop, args=(combined_callback,))
            self.mixer_thread.daemon = True
            self.mixer_thread.start()
            
            print("Dual-stream capture started.")
        except Exception as e:
            print(f"Error starting dual-stream capture: {e}")
            self.is_running = False
            raise

    def _mixer_loop(self, combined_callback):
        while self.is_running:
            try:
                # Wait for data from both streams with a timeout
                # If one stream is missing, we still want to keep going
                mic_chunk = None
                mon_chunk = None
                
                try:
                    mic_chunk = self.mic_queue.get(timeout=0.2)
                except queue.Empty:
                    pass
                
                try:
                    mon_chunk = self.mon_queue.get(timeout=0.2)
                except queue.Empty:
                    pass
                
                if mic_chunk is not None and mon_chunk is not None:
                    mixed_chunk = (mic_chunk + mon_chunk) / 2.0
                elif mic_chunk is not None:
                    mixed_chunk = mic_chunk
                elif mon_chunk is not None:
                    mixed_chunk = mon_chunk
                else:
                    continue
                
                combined_callback(mixed_chunk, None, None, None)
            except Exception as e:
                print(f"Mixer error: {e}")
                continue

    def stop_stream(self):
        self.is_running = False
        if hasattr(self, 'mic_stream'):
            self.mic_stream.stop()
            self.mic_stream.close()
        if hasattr(self, 'mon_stream'):
            self.mon_stream.stop()
            self.mon_stream.close()
