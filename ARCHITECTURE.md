# Study Sleep - Architecture Overview

## System Components

### 1. Camera Capture Module (`camera_capture.py`)
- Continuously captures frames from webcam
- Configurable capture interval (default: 3 seconds)
- Thread-safe frame retrieval

### 2. Drowsiness Detector (`drowsiness_detector.py`)
- Uses MediaPipe for pose and face detection
- **Slouching Detection**: Calculates shoulder angle deviation from reference
- **Eye Closure Detection**: Uses Eye Aspect Ratio (EAR) to detect closed eyes
- **Drowsiness Index**: Combines both metrics (0.0 = alert, 1.0 = very drowsy)

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

### Drowsiness Calculation
```
Slouching Score = |current_shoulder_angle - reference_angle| / 30°
Eye Closure Score = max(0, (0.7 - current_EAR/reference_EAR) / 0.7)
Drowsiness Index = (Slouching Score + Eye Closure Score) / 2
```

### Break Duration Calculation
```
base_duration = preferences.base_break_duration
subject_multiplier = preferences.get_subject_tiredness(current_subject)
adjusted_base = base_duration * subject_multiplier
break_duration = adjusted_base + (max_duration - adjusted_base) * drowsiness_index
```

