# Work Sleep - Architecture Overview

## System Components

### 1. Camera Capture Module (`camera_capture.py`)
- Continuously captures frames from webcam
- Configurable capture interval (default: 3 seconds)
- Thread-safe frame retrieval

### 2. Drowsiness Detector (`drowsiness_detector.py`)
- Uses MediaPipe (face mesh + pose) for landmarks
- Computes 4 indices per frame: drowsiness (EAR vs baseline), slouching (shoulder angle deviation), attention (gaze/head deviation), yawn_score (recent yawns)
- Returns indices + debug info to the main loop and break overlay

### 3. Preferences Manager (`preferences.py`)
- Stores user preferences in JSON format
- Subject-specific tiredness multipliers
- Configurable break durations
- Drowsiness threshold settings

### 4. Break Overlay System (`break_overlay.py`)
- Fullscreen overlay window
- Countdown timer display
- Blocks user input using pynput
- Modal window that prevents interaction with other applications

### 5. Main Application (`main.py`)
- Tkinter-based GUI
- Coordinates all components
- Real-time drowsiness monitoring
- Automatic break triggering

## Workflow

1. **Initialization**
   - User starts application
   - Camera initializes

2. **Reference Capture**
   - User captures diagnostic image when alert
   - System stores reference posture and eye state

3. **Monitoring Loop**
   - Camera captures frame every 3 seconds
   - Drowsiness detector analyzes frame
   - Compares current state to reference
   - Calculates drowsiness index

4. **Break Triggering**
   - When drowsiness index exceeds threshold:
     - Calculate break duration (based on preferences + drowsiness)
     - Show break overlay
     - Block all input
     - Display countdown timer
     - Unblock input when timer completes

## Key Features

- **Adaptive Break Duration**: Longer breaks for higher drowsiness
- **Subject Awareness**: Different subjects can have different tiredness multipliers
- **Non-intrusive Monitoring**: Only captures frames periodically
- **Input Blocking**: Prevents bypassing breaks
- **Visual Feedback**: Real-time drowsiness index display

## Technical Details

### Core Index Formulas (Simplified)
```
slouching = clamp(|current_shoulder_angle - ref_angle| / 30, 0, 1)
ear_ratio = current_EAR / ref_EAR
drowsiness = clamp((0.7 - ear_ratio)/0.7, 0, 1) if ear_ratio < 0.7 else 0
attention = weighted(gaze_offset, head_rotation, head_tilt)  # normalized 0..1
yawn_score = scaled count of yawns in last 60s (3+ => 1.0)
```

### Break Duration Calculation
```
weighted_score = sum(index[i] * weight[i])
duration_seconds = scaler * weighted_score   # scaler learns (bounded)
```

