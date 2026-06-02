# Terminal Secretary

A local conversation capture tool that intercepts your microphone and system audio, transcribes the conversation, and generates searchable summaries using local AI.

## Features
- **Dual Audio Capture**: Captures both your microphone and system audio (e.g., colleagues on a call).
- **Local STT**: Uses `faster-whisper` for fast, private transcription.
- **Local LLM**: Summarizes conversations using `Ollama`.
- **Semantic Search**: Stores summaries in `ChromaDB` for easy retrieval.

## Prerequisites
- **Docker** and **docker-compose**
- **PulseAudio** or **PipeWire** (Linux)
- **Ollama** installed and running on the host machine.
  - Pull Llama 3: `ollama pull llama3`

## How to Use

### 1. Build the container
```bash
sudo docker-compose build
```

### 2. Capture a conversation
```bash
./secretary record
```
Press `Ctrl+C` when the conversation is finished to stop recording and generate the summary.

### 3. Search past conversations
```bash
./secretary search "What did we decide about the database?"
```

## Installation (Optional: Global Command)
To run `secretary` from anywhere in your terminal, create a symlink in your local bin:
```bash
sudo ln -sf $(pwd)/secretary /usr/local/bin/secretary
```
Then you can just run `secretary record` or `secretary search` without the `./`.

## Architecture
- **audio.py**: Sets up a virtual PulseAudio sink and loops back Mic/Monitor sources to it.
- **stt.py**: Handles Speech-to-Text and Voice Activity Detection.
- **llm.py**: Interfaces with local Ollama for summarization.
- **db.py**: Relational (SQLite) and Vector (ChromaDB) storage.
- **main.py**: CLI entry point.
