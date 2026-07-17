#!/bin/bash

set -e

echo "Starting chromadb server..."
chroma run &

echo "Starting Flask server..."
python main.py