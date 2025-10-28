#!/bin/bash

echo "TTB COLA Registry Matcher - Setup and Run Script"
echo "================================================"

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Starting the Flask application..."
echo "Access the application at: http://localhost:5000"
echo ""

python app.py