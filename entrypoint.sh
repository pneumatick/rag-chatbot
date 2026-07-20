#!/bin/bash

set -e

echo "Starting npm server for Vite..."
npm install
npm run dev &

echo "Starting chromadb server..."
chroma run &

echo "Starting Flask server..."
python main.py