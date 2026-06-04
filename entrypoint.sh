#!/bin/bash
set -e

# Only perform audio setup if the command is 'record'
if [[ "$*" == *"record"* ]]; then
    # Dynamically set the PulseAudio server path based on UID
    export PULSE_SERVER=unix:/run/user/${USER_ID:-1000}/pulse/native

    # Generate asound.conf from environment variables
    python3 configure_audio.py

    # Safeguard: if the pulse cookie was accidentally created as a directory, remove it
    if [ -d "/root/.config/pulse/cookie" ]; then
        echo "Cleaning up accidental directory at /root/.config/pulse/cookie..."
        rmdir "/root/.config/pulse/cookie"
    fi
fi

exec "$@"
