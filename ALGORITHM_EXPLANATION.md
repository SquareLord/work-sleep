# How the Drowsiness Detection Algorithm Works (Work Sleep)

## Overview

This application (rebranded to Work Sleep) uses **face and pose detection** (not facial recognition) to detect both **drowsiness** and **distraction**. It does not identify who you are—it analyzes facial landmarks, posture, and head orientation to determine fatigue and focus.

## Technology Stack

The algorithm uses **Google's MediaPipe** framework, which provides:
- **Face Mesh**: Detects 468 facial landmarks
- **Pose Detection**: Detects 33 body landmarks

## How It Works

### Step 1: Face Detection with MediaPipe Face Mesh

MediaPipe Face Mesh processes each camera frame and identifies **468 facial landmarks** (points on your face). These landmarks include:
- Eye contours (left and right)
- Eyebrow positions
- Nose, mouth, and face outline
- Cheek and jaw positions

**Key Landmarks for Eye Detection:**
- Left eye: landmarks at indices [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
- Right eye: landmarks at indices [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

### Step 2: Eye Aspect Ratio (EAR) Calculation

The algorithm calculates the **Eye Aspect Ratio (EAR)** for drowsiness detection:

```
EAR = (vertical_distance_1 + vertical_distance_2) / (2 × horizontal_distance)
```

**How it works:**
1. For each eye, it extracts 6 key points forming a rectangle
2. Calculates two vertical distances (top-to-bottom)
3. Calculates one horizontal distance (left-to-right)
4. EAR = average of vertical distances divided by horizontal distance

**Why EAR works:**
- When eyes are **open**: EAR is relatively high (e.g., 0.25-0.35)
- When eyes are **closed**: EAR drops significantly (approaches 0)
- When eyes are **half-closed/drowsy**: EAR is in between

### Step 3: Pose Detection for Slouching

MediaPipe Pose detects **33 body landmarks**, including:
- Shoulders (left and right)
- Hips, knees, ankles
- Head, neck, and spine positions

**Slouching Detection:**
1. Extracts left and right shoulder positions
2. Calculates the angle between shoulders relative to horizontal
3. Compares current angle to reference angle

**Formula:**
```
shoulder_angle = arctan2(|dy|, |dx|) × 180/π
```
Where:
- `dx` = horizontal distance between shoulders
- `dy` = vertical distance between shoulders

### Step 4: Reference-Based Comparison

The algorithm is **personalized** to each user:

1. **Reference Capture**: When you click "Capture Reference Image", the system:
   - Captures your EAR when alert
   - Captures your shoulder angle when sitting properly
   - Stores these as baseline values

2. **Real-time Comparison**: During monitoring:
   - Compares current EAR to reference EAR
   - Compares current shoulder angle to reference angle
   - Detects deviations that indicate drowsiness

### Step 5: Distraction Detection (NEW!)

The algorithm also detects when you're **not focused on your screen** by analyzing head pose:

**Head Pose Calculation:**
1. Calculates face center position (average of nose, eyes)
2. Measures head rotation angle (left/right turn)
3. Detects head tilt (vertical angle)
4. Compares to reference pose when you were focused

**Distraction Score:**
- **Face Center Offset**: How far your face is from screen center (50% weight)
- **Head Rotation**: How much you've turned left/right (30% weight)
- **Head Tilt**: Vertical angle deviation (20% weight)

### Step 6: Combined Attention Index Calculation

The algorithm combines drowsiness and distraction into a single **Attention Index** (0.0 to 1.0):

**Slouching Score:**
```
slouch_score = min(|current_angle - reference_angle| / 30°, 1.0)
```
- 0° deviation = 0.0 (alert)
- 30°+ deviation = 1.0 (very drowsy)

**Eye Closure Score:**
```
ear_ratio = current_EAR / reference_EAR
eye_score = max(0, (0.7 - ear_ratio) / 0.7) if ear_ratio < 0.7 else 0
```
- EAR at 100% of reference = 0.0 (alert)
- EAR at 70% of reference = 0.0 (still alert)
- EAR below 70% = increasing score (drowsy)
- EAR at 0% = 1.0 (eyes closed)

**Final Indices:**
```
drowsiness_index = (slouch_score + eye_score) / 2
distraction_score = (center_score × 0.5 + rotation_score × 0.3 + tilt_score × 0.2)
attention_index = (drowsiness_index × 0.6 + distraction_index × 0.4)
```

The **Attention Index** is what triggers breaks - it combines both drowsiness and distraction.

## Algorithm Flow Diagram

```
Camera Frame
    ↓
MediaPipe Face Mesh → 468 Facial Landmarks
    ↓
Extract Eye Landmarks → Calculate EAR
    ↓
Compare to Reference EAR → Eye Score
    ↓
Extract Head Pose → Calculate Face Center, Rotation, Tilt
    ↓
Compare to Reference Pose → Distraction Score
    ↓
MediaPipe Pose → 33 Body Landmarks
    ↓
Extract Shoulder Positions → Calculate Angle
    ↓
Compare to Reference Angle → Slouch Score
    ↓
Combine Scores → Drowsiness Index (0.0-1.0)
    ↓
Combine Drowsiness + Distraction → Attention Index (0.0-1.0)
    ↓
If Attention Index ≥ Threshold → Trigger Break
```

## Key Features

1. **Personalized**: Uses your baseline, not generic thresholds
2. **Multi-modal**: Combines eye closure, posture, AND head orientation
3. **Dual Detection**: Detects both drowsiness AND distraction
4. **Real-time**: Processes frames every 3 seconds
5. **Robust**: Handles variations in lighting and camera angle
6. **Smart Triggers**: Breaks triggered by either drowsiness or distraction

## Limitations

- Requires good lighting and clear face visibility
- May have false positives if you look away from camera
- Reference image must be captured when you're alert
- Works best with front-facing camera

## Technical Details

**MediaPipe Models:**
- Face Mesh: Uses a lightweight CNN trained on facial landmark detection
- Pose: Uses BlazePose, a real-time pose estimation model

**Performance:**
- Face detection: ~10-30ms per frame
- Pose detection: ~5-15ms per frame
- Total processing: ~15-45ms per frame (well under 3-second capture interval)

