import sounddevice as sd
import numpy as np
import time

def test_capture(source_name, duration=2, fs=16000):
    print(f"Testing capture from: {source_name}")
    try:
        # Note: 'pulse' with specific device can sometimes be reached via 'pulse' 
        # and setting the env var, but let's try opening it directly if possible.
        # However, sounddevice/portaudio usually needs an index.
        # We can also try using the name directly in some portaudio builds.
        
        # Fallback: Capture from the default 'pulse' (index 9)
        # We will use pactl to set the default before running the script for each test.
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, device=9)
        sd.wait()
        rms = np.sqrt(np.mean(recording**2))
        print(f"  Captured {len(recording)} samples. RMS: {rms:.6f}")
        return rms > 0
    except Exception as e:
        print(f"  Error capturing from {source_name}: {e}")
        return False

if __name__ == "__main__":
    # This script assumes it will be run twice, with different default sources set via pactl
    import sys
    if len(sys.argv) > 1:
        test_capture(sys.argv[1])
    else:
        print("Usage: python3 audio_test.py <source_name>")
