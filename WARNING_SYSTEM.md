# Individual Index Warning System

## Overview

In addition to the weighted tiredness system that triggers work timers, the application now features **individual index warnings** that provide detailed, actionable guidance when specific fatigue indicators become elevated.

---

## How It Works

### Trigger Conditions
- **Threshold**: Any individual index >= 0.5
- **Cooldown**: 60 seconds per index type (independent)
- **Frequency**: Each index can warn once per minute

### Two-Tier Alert System

```
┌─────────────────────────────────────────────────┐
│  TIER 1: Individual Index Warnings (>= 0.5)    │
│  • Informational popups                         │
│  • Specific guidance per index                  │
│  • 60-second cooldown per index                 │
│  • Can have multiple indices warning            │
└─────────────────────────────────────────────────┘
                      ⬇️
┌─────────────────────────────────────────────────┐
│  TIER 2: Weighted Tiredness Trigger (>= 0.3)   │
│  • Enforced action (reminder or timer)          │
│  • Based on personalized weights                │
│  • 3-second sustained threshold                 │
│  • Minimum interval between actions             │
└─────────────────────────────────────────────────┘
```

---

## Warning Messages by Index

### 1. 😴 Drowsiness (>= 0.5)
**Problem**: Eyes showing significant closure

**Immediate Actions**:
- Look away from screen
- Blink deliberately several times
- Take 5 deep breaths
- Stand up and stretch

**Long-term Risks**:
- Reduced productivity and errors
- Eye strain and headaches
- Increased accident risk
- Chronic fatigue if sleep-deprived

---

### 2. 🪑 Slouching (>= 0.5)
**Problem**: Shoulders significantly deviated from proper alignment

**Immediate Actions**:
- Sit up straight with shoulders back
- Adjust chair height
- Position screen at eye level
- Use lumbar support

**Long-term Risks**:
- Chronic back and neck pain
- Spinal misalignment and disc problems
- Reduced lung capacity
- Permanent postural changes

---

### 3. 🎯 Attention Drift (>= 0.5)
**Problem**: Frequently looking away from work area

**Immediate Actions**:
- Refocus on your task
- Remove distractions from view
- Take 2-minute mindfulness break
- Set smaller, achievable goal

**Long-term Risks**:
- Decreased work quality
- Increased time to complete tasks
- Higher stress from unfinished work
- Difficulty maintaining focus

---

### 4. 🥱 Frequent Yawning (>= 0.5)
**Problem**: Yawning repeatedly (2+ times/minute)

**Immediate Actions**:
- Take 5-10 minute break
- Get fresh air or cold water
- Do light physical activity
- Consider power nap (10-20 min)

**Long-term Risks**:
- Accumulated sleep debt
- Weakened immune system
- Impaired cognitive function
- Increased risk of burnout

---

### 5. 👁️ Eye Closure (>= 0.5)
**Problem**: Eyes closing more than normal (microsleeps)

**Immediate Actions**:
- Close eyes for 20 seconds
- Apply 20-20-20 rule (every 20 min, look 20 feet away for 20 sec)
- Use lubricating eye drops
- Take longer break

**Long-term Risks**:
- Computer Vision Syndrome
- Chronic dry eyes
- Blurred vision
- Increased headache frequency

---

### 6. 💤 Head Nodding (>= 0.5)
**Problem**: Head dropping forward - fighting sleep

**Immediate Actions**:
- **STOP working immediately**
- Take 15-minute break or nap
- Walk around to increase alertness
- Splash cold water on face

**Long-term Risks**:
- Microsleep episodes (dangerous!)
- Severe cognitive impairment
- Long-term sleep disorders
- Increased accident risk

---

### 7. 👀 Eye Smoothness (>= 0.5)
**Problem**: Eye movements becoming jerky and unfocused

**Immediate Actions**:
- Focus on single point for 10 seconds
- Close eyes and rest them
- Reduce screen brightness
- Take short walk

**Long-term Risks**:
- Visual fatigue and strain
- Difficulty concentrating
- Reduced reading comprehension
- Potential vision problems

---

### 8. ✨ Blink Variance (>= 0.5)
**Problem**: Blinking too slow or irregular

**Immediate Actions**:
- Consciously blink 10-15 times
- Use artificial tears
- Adjust screen position/brightness
- Increase humidity if possible

**Long-term Risks**:
- Chronic dry eye syndrome
- Corneal damage
- Increased eye infections
- Permanent tear film dysfunction

---

### 9. 😐 Facial Stillness (>= 0.5)
**Problem**: Face still for too long - zoning out

**Immediate Actions**:
- Re-engage with work
- Take mental break
- Talk to someone or read aloud
- Change task or position

**Long-term Risks**:
- Mental fatigue and burnout
- Reduced cognitive processing
- Loss of motivation
- Possible attention disorders

---

## Example Scenarios

### Scenario 1: Single Index Warning
```
Time: 10:05 AM
Eye Closure Index: 0.62
Action: Popup warning appears with eye closure guidance
Result: User takes 20-second eye break
Cooldown: Next eye closure warning earliest at 10:06 AM
```

### Scenario 2: Multiple Index Warnings
```
Time: 2:30 PM
Slouching: 0.58, Attention: 0.65, Yawn: 0.52
Action: Three separate warnings appear (one per index)
Result: User addresses posture, refocuses, and takes break
Cooldown: Each index on separate 60-second timer
```

### Scenario 3: Warning → Timer Trigger
```
Time: 4:15 PM
Individual warnings: Drowsiness (0.55), Eye Closure (0.61)
→ Weighted tiredness reaches 0.32 for 3 seconds
→ Timer break triggered (separate from warnings)
Result: Enforced 3-minute break with smart exit
```

---

## UI Behavior

### Color Coding (Still Active)
- **Green text**: Index < 0.5 (normal)
- **Yellow/Orange text**: Index >= 0.5 (elevated)

### Popup Windows
- **Title**: Icon + descriptive title
- **Current Level**: Shows exact index value
- **Problem**: What's happening
- **Immediate Actions**: What to do right now
- **Long-term Risks**: Why it matters
- **Note**: Clarifies relationship to timer system

### Cooldown Management
- Each index tracked independently
- 60-second cooldown per index type
- Multiple indices can warn simultaneously
- Warnings don't affect timer trigger logic

---

## Benefits

### 1. **Early Intervention**
Catch issues before they require enforced breaks

### 2. **Education**
Users learn what each index means and how to address it

### 3. **Health Focus**
Emphasizes long-term health consequences

### 4. **Actionable Guidance**
Specific, immediate steps to improve each metric

### 5. **Independent Operation**
Warnings complement (not replace) the weighted tiredness system

---

## Configuration

Current settings in `main.py`:
```python
self.index_warning_threshold = 0.5  # Trigger at 50% of max
self.index_warning_cooldown = 60.0  # 1 minute between warnings
```

These can be adjusted based on user preference:
- **Lower threshold (0.4)**: More frequent warnings, earlier intervention
- **Higher threshold (0.6)**: Less frequent warnings, only for severe cases
- **Longer cooldown (120.0)**: Less intrusive, 2 minutes between warnings
- **Shorter cooldown (30.0)**: More frequent reminders

---

## Summary

The individual index warning system provides:
✅ Detailed, educational feedback on specific issues
✅ Actionable guidance for immediate improvement
✅ Long-term health risk awareness
✅ Independent cooldowns per index type
✅ Complements (doesn't replace) weighted tiredness triggers

Users now have both **informational warnings** (index-specific) and **enforced breaks** (weighted system) working together for comprehensive fatigue management! 🎯
