#!/usr/bin/env python3
"""Test script to check if all required packages are installed."""
import sys

required_packages = [
    'cv2',
    'mediapipe',
    'numpy',
    'pynput',
    'tkinter'
]

missing = []
for package in required_packages:
    try:
        if package == 'cv2':
            import cv2
        elif package == 'mediapipe':
            import mediapipe
        elif package == 'numpy':
            import numpy
        elif package == 'pynput':
            import pynput
        elif package == 'tkinter':
            import tkinter
        print(f"✓ {package} is installed")
    except ImportError:
        print(f"✗ {package} is NOT installed")
        missing.append(package)

if missing:
    print(f"\nMissing packages: {', '.join(missing)}")
    print("Please install them using: pip install -r requirements.txt")
    sys.exit(1)
else:
    print("\nAll packages are installed! You can run the application.")
    sys.exit(0)

