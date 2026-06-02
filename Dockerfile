FROM python:3.12-slim

# Install system dependencies for audio and faster-whisper
RUN apt-get update && apt-get install -y \
    build-essential \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libswresample-dev \
    libswscale-dev \
    ffmpeg \
    pulseaudio-utils \
    libasound2-plugins \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models
COPY download_models.py .
RUN python download_models.py

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PULSE_SERVER=unix:/run/user/1000/pulse/native

# Add entrypoint to generate asound.conf dynamically
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py", "record"]
