# Work Sleep (formerly Study Sleep) - Drowsiness & Break System

An adaptive desktop assistant that monitors posture and eyes to detect tiredness and enforce smart breaks during focused work or study sessions.

## Features

- Continuous monitoring via webcam (no identities stored)
- 4 indices: drowsiness, slouching, attention, yawn score
- Adaptive break timing: duration = scaler × weighted_score (learns over time)
- Input blocking overlay with countdown and early-exit if you become alert

## Installation

### Quick Start

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
python3 main.py
```

1. Start the app
2. Capture a reference when you're alert and sitting properly
3. The system monitors posture/eyes and computes 4 indices
4. When the weighted score crosses threshold, a break overlay is triggered
5. The scaler adapts per-task based on how quickly you recover during breaks

## Requirements

- Python 3.10+
- Webcam
- Linux/Windows/macOS
## License

This project is licensed under the MIT License. See `LICENSE` for details.

