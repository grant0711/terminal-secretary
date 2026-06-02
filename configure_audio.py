import os
import subprocess

def generate_asound_conf():
    mic = os.getenv("MIC_SOURCE", "default")
    monitor = os.getenv("MONITOR_SOURCE", "default")
    
    content = f"""
pcm.mic {{
    type pulse
    device {mic}
}}

pcm.monitor {{
    type pulse
    device {monitor}
}}
"""
    with open("/etc/asound.conf", "w") as f:
        f.write(content)
    print(f"Generated /etc/asound.conf with Mic: {mic}, Monitor: {monitor}")

if __name__ == "__main__":
    generate_asound_conf()
