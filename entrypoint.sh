#!/bin/bash
set -e

# Dynamically set the PulseAudio server path based on UID
export PULSE_SERVER=unix:/run/user/${USER_ID:-1000}/pulse/native

# Generate asound.conf from environment variables
python3 configure_audio.py

exec "$@"
