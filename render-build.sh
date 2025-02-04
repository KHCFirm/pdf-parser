#!/bin/bash

# Update package lists
apt-get update

# Install Tesseract OCR and dependencies
apt-get install -y tesseract-ocr libtesseract-dev libleptonica-dev

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt
