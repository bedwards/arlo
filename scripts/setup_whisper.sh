#!/usr/bin/env bash
# Build whisper.cpp for Apple Silicon local transcription.
#
# Usage:
#   ./scripts/setup_whisper.sh

set -euo pipefail

WHISPER_DIR="${WHISPER_DIR:-$HOME/whisper.cpp}"

if [ -d "$WHISPER_DIR" ]; then
    echo "whisper.cpp already exists at $WHISPER_DIR"
else
    echo "Cloning whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp "$WHISPER_DIR"
fi

echo "Building whisper.cpp..."
cd "$WHISPER_DIR"
make -j

echo "Downloading base model..."
bash models/download-ggml-model.sh base.en

echo "Done. whisper.cpp is ready at $WHISPER_DIR"
