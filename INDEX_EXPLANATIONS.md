# Tiredness Detection Indices - Complete Guide

## System Overview

The system uses **9 independent indices** to measure different aspects of tiredness and distraction. Each index is calibrated so that **1.0 represents definitive tiredness or distraction** - not just a theoretical maximum, but a clear indicator that intervention is needed.

---

## Understanding Warnings vs Timer Triggers

### 📊 **UI Warnings (Yellow/Orange Text)**
- **When**: Individual index >= 0.5
- **Purpose**: Informational - shows which specific indicators are elevated
- **Action**: None automatic - just helps you understand what's being detected
- **Example**: "Eye Closure Index: 0.65" in orange text

### ⏰ **Timer/Reminder Triggers**
- **When**: Weighted tiredness >= 0.30 for 3+ consecutive seconds
- **Formula**: `weighted_tiredness = sum(index[i] × weight[i])`
- **Action**: System triggers either a reminder popup OR enforced timer break
- **Alternation**: reminder → timer → reminder → timer...

**Key Point**: The weighted formula is personalized to YOUR task patterns. Some indices matter more for some tasks (e.g., slouching more important for reading, eye closure more important for coding).

---

## The 9 Indices Explained

### 1. 👁️ **Eye Closure Index** (FIXED)
**What it measures**: How closed your eyes are RIGHT NOW + recent prolonged closures

**Why it indicates tiredness**: When tired, eyelids droop and you experience "microsleeps"

**How it's calculated**:
- **Current state (70%)**: Maps current EAR (Eye Aspect Ratio)
  - Wide awake (EAR 0.30+): score = 0.0
  - Getting tired (EAR 0.20): score = 0.5
  - Eyes barely open (EAR 0.15): score = 1.0
- **Recent events (30%)**: Tracks prolonged closures (>0.4s)
  - Each closure event adds severity based on duration and recency
  
**Updates**: Every frame (~10 times/second) - truly dynamic!

**1.0 means**: Eyes barely open OR frequent prolonged closures = definitely drowsy

---

### 2. 💤 **Drowsiness Index** (RECALIBRATED)
**What it measures**: General eye drowsiness from EAR ratio

**Why it indicates tiredness**: Eyes naturally become more closed when tired

**How it's calculated**:
- Compares current EAR to your calibrated baseline
- 100% of baseline = 0.0 (wide awake)
- 80% of baseline = 0.3 (getting tired)
- 60% of baseline = 0.7 (very drowsy)
- 50% of baseline = 1.0 (definitely drowsy)

**Updates**: Every frame

**1.0 means**: Eyes at 50% or less of baseline openness = severe drowsiness

---

### 3. 🎯 **Attention Index**
**What it measures**: How much you're looking away from the screen

**Why it indicates distraction**: Looking away repeatedly = mind wandering

**How it's calculated**:
- Tracks head rotation angles (horizontal & vertical deviation)
- Averages deviation over last 30 seconds
- 0.0 = looking straight at screen
- 0.5 = moderately looking away
- 1.0 = consistently looking away

**Updates**: Continuously based on head pose

**1.0 means**: Consistently looking away from work = definitely distracted

---

### 4. 🥱 **Yawn Score** (RECALIBRATED)
**What it measures**: Number of yawns in the last 60 seconds

**Why it indicates tiredness**: Yawning is a physiological response to fatigue

**How it's calculated**:
- Detects mouth opening wide (MAR > 0.6) for 0.5-3 seconds
- Counts yawns in rolling 60-second window
- 0 yawns = 0.0
- 1 yawn = 0.33
- 2 yawns = 0.67
- 3+ yawns = 1.0

**Updates**: When yawn events occur

**1.0 means**: 3+ yawns in last minute = definitely tired

---

### 5. 👤 **Slouching Index** (RECALIBRATED)
**What it measures**: Shoulder angle deviation from calibrated posture

**Why it indicates tiredness**: Posture degrades when tired or uncomfortable

**How it's calculated**:
- Measures shoulder angle vs your calibrated baseline
- 0-30 degree range mapped to 0-1
- Slight slouch (10°) = 0.33
- Moderate slouch (20°) = 0.67
- Severe slouch (30°+) = 1.0

**Updates**: Every frame

**1.0 means**: 30+ degree slouch = severe poor posture

---

### 6. 🎭 **Head Nodding Index** (FIXED)
**What it measures**: Head dropping forward (nodding off) + current head droop

**Why it indicates tiredness**: When fighting sleep, head repeatedly drops

**How it's calculated**:
- Calculates head pitch from nose-chin vs nose-forehead distances
- **Current droop (60%)**: 
  - Upright = 0.0
  - 20° droop = 0.4
  - 30°+ droop = 0.6
- **Drop events (40%)**:
  - Sudden 10°+ drops detected
  - Each recent drop adds 0.15

**Updates**: Every frame (pitch) + when drops detected

**1.0 means**: Severe head droop OR frequent nodding = fighting sleep

---

### 7. 👀 **Eye Smoothness Index** (TUNED)
**What it measures**: Erratic eye movements (gaze instability)

**Why it indicates tiredness/distraction**: Tired or distracted = jerky, unfocused eye movements

**How it's calculated**:
- Tracks eye position velocity and variance over last 3 seconds
- **Variance component (70%)**: Erratic changes
  - Normal focused: 0.0001 variance = 0.0
  - Moderate: 0.001 variance = 0.33
  - Erratic: 0.003+ variance = 1.0
- **Mean velocity component (30%)**: Rapid scanning
  - Combines with variance for final score

**Updates**: Continuously from gaze tracking

**1.0 means**: Very erratic eye movements = distracted or tired

---

### 8. 🌟 **Blink Variance Index** (FIXED)
**What it measures**: Irregularity in blinking pattern + blink rate

**Why it indicates tiredness**: Tired = irregular blinking (slower rate, inconsistent timing)

**How it's calculated**:
- **Detects blinks**: EAR drops below 0.20 then recovers above 0.23
- **Coefficient of Variation**: std_deviation / mean_interval
  - Regular blinking (CV 0.3) = 0.0
  - Moderate irregularity (CV 0.6) = 0.3
  - Very irregular (CV 1.0+) = 1.0
- **Slowness penalty**: <8 blinks/minute adds up to 0.4

**Updates**: When blinks detected (continuously monitored)

**1.0 means**: Very irregular blinking OR too slow = drowsy

---

### 9. 😐 **Facial Stillness Index** (RECALIBRATED)
**What it measures**: How long since last facial movement

**Why it indicates tiredness**: Zoning out = face becomes frozen/expressionless

**How it's calculated**:
- Tracks time since last facial landmark movement
- 0-3s = 0.0 (normal concentration)
- 8s = 0.25 (starting to zone out)
- 15s = 0.6 (clearly zoned out)
- 20s+ = 1.0 (definitely out of it / microsleep)

**Updates**: Continuously monitors facial movement

**1.0 means**: 20+ seconds no facial movement = zoned out or microsleeping

---

## Calibration: What "1.0" Really Means

Every index has been **recalibrated** based on realistic thresholds:

| Index | 1.0 Represents | Example |
|-------|----------------|---------|
| Eye Closure | Eyes at 50% baseline openness | Eyelids drooping heavily |
| Drowsiness | EAR at 50% of baseline | Very drowsy state |
| Attention | Consistently looking away | Not watching screen |
| Yawn | 3+ yawns in 60 seconds | Definitely fatigued |
| Slouching | 30+ degree shoulder deviation | Severe poor posture |
| Head Nodding | Severe droop + frequent nods | Fighting sleep |
| Eye Smoothness | 3x baseline variance in gaze | Very erratic eye movement |
| Blink Variance | CV >1.0 OR <8 blinks/min | Very irregular pattern |
| Facial Stillness | 20+ seconds no movement | Zoned out / microsleep |

---

## How The Weighted System Works

### Your Personalized Formula
```
weighted_tiredness = (
    drowsiness × 0.12 +
    slouching × 0.08 +
    attention × 0.15 +
    yawn × 0.11 +
    eye_closure × 0.14 +
    head_nodding × 0.13 +
    eye_smoothness × 0.10 +
    blink_variance × 0.09 +
    facial_stillness × 0.08
)
```
*(Example weights - yours will adapt based on YOUR patterns!)*

### Why 0.30 Threshold?
With personalized weights, a weighted score of 0.30 means roughly 30% of your personalized "maximum tiredness" - enough to warrant a break or reminder.

### Trigger Rules
1. **Weighted tiredness >= 0.30** for 3 consecutive seconds
2. **First trigger**: Reminder popup (gentle warning with specific index)
3. **Second trigger**: Timer break (enforced rest)
4. **Pattern continues**: reminder → timer → reminder → timer...

---

## What You See in the Application

### Green Text (Index < 0.5)
✅ Normal - no concern

### Yellow/Orange Text (Index >= 0.5)
⚠️ Warning - that specific indicator is elevated (informational only)

### Reminder Popup
💬 "Your [index] is elevated. Consider taking a break soon."
- Appears when weighted tiredness hits threshold (first time)
- Index-specific message
- Dismissible

### Timer Overlay
⏰ Full-screen break timer with countdown
- Appears when weighted tiredness hits threshold (second time)
- **Smart exit**: Exits early if you become alert
- **Alert requirement**: If still tired when timer ends, must stay alert for 10s
- **Adaptive duration**: Timer length adjusts based on your response patterns

---

## Adaptive Learning

The system learns YOUR patterns:
- **Weights**: Which indices matter most for each task
- **Timer coefficient**: Optimal break duration (0.5-2.0x multiplier)
- **Learning rate**: 15% adjustment per break for fast adaptation

**Example**: If you consistently become alert before the timer ends during "Reading", the system will:
1. Reduce timer duration for reading (coefficient × 0.85)
2. Increase weight on the dominant index that triggered the break
3. Adjust other weights proportionally

This creates a truly personalized fatigue detection system! 🎯
