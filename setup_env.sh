#!/bin/bash
# Setup virtual environment for DICOM classification project

echo "Setting up virtual environment for DICOM classification..."

# Create virtual environment
python3 -m venv dicom_env

# Activate virtual environment
source dicom_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

echo "Virtual environment setup complete!"
echo "To activate the environment, run: source dicom_env/bin/activate"
echo "To test the classifier, run: python test_classifier.py"