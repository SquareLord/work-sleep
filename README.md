# Study Sleep - Drowsiness Detection & Break System

A hackathon project that monitors your posture and eye state to detect drowsiness and enforce breaks during study sessions.

## Features

- **Continuous Monitoring**: Captures images every few seconds via webcam
- **Drowsiness Detection**: Analyzes slouching and eye closure compared to a reference image
- **Smart Breaks**: Automatically enforces breaks based on drowsiness index and user preferences
- **Input Blocking**: Overlays a timer and blocks all user input during breaks

## Installation

### Quick Setup

Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Installation

1. Install system dependencies (Linux):
   ```bash
   sudo apt-get install python3-pip python3-tk
   ```

2. Install Python packages:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Verify installation:
   ```bash
   python3 test_imports.py
   ```

## Usage

```bash
python main.py
```

1. Start the application
2. Capture a reference diagnostic image when you're alert and sitting properly
3. The system will continuously monitor your posture and eye state
4. When drowsiness is detected, breaks will be automatically enforced

## Requirements

- Python 3.8+
- Webcam
- Linux/Windows/macOS

