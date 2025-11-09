"""User preferences management system."""
import json
import os
from typing import Dict, Any, Optional

class PreferencesManager:
    def __init__(self, preferences_file: str = "preferences.json"):
        """
        Initialize preferences manager.
        
        Args:
            preferences_file: Path to JSON file storing preferences
        """
        self.preferences_file = preferences_file
        self.preferences = self.load_preferences()
    
    def load_preferences(self) -> Dict[str, Any]:
        """Load preferences from file or create default."""
        if os.path.exists(self.preferences_file):
            try:
                with open(self.preferences_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default preferences
        return {
            'subject_tiredness': {},  # Maps subject names to tiredness multipliers
            'base_break_duration': 60,  # Base break duration in seconds
            'max_break_duration': 300,  # Maximum break duration in seconds
            'drowsiness_threshold': 0.5,  # Drowsiness index threshold to trigger break
            'current_subject': None
        }
    
    def save_preferences(self):
        """Save preferences to file."""
        with open(self.preferences_file, 'w') as f:
            json.dump(self.preferences, f, indent=2)
    
    def set_subject_tiredness(self, subject: str, multiplier: float):
        """
        Set tiredness multiplier for a subject.
        
        Args:
            subject: Name of the subject
            multiplier: Multiplier (higher = more tired, e.g., 1.5 = 50% more tired)
        """
        self.preferences['subject_tiredness'][subject] = multiplier
        self.save_preferences()
    
    def get_subject_tiredness(self, subject: str) -> float:
        """Get tiredness multiplier for a subject (default 1.0)."""
        return self.preferences['subject_tiredness'].get(subject, 1.0)
    
    def set_current_subject(self, subject: str):
        """Set the current subject being studied."""
        self.preferences['current_subject'] = subject
        self.save_preferences()
    
    def get_current_subject(self) -> Optional[str]:
        """Get the current subject."""
        return self.preferences.get('current_subject')
    
    def calculate_break_duration(self, drowsiness_index: float, distraction_index: float, attention_index: float) -> int:
        """
        Calculate break duration based on weighted average of all three indices.
        Light drowsiness/unfocusing = smaller timer, heavy = larger timer.
        
        Args:
            drowsiness_index: Current drowsiness index (0.0-1.0)
            distraction_index: Current distraction index (0.0-1.0)
            attention_index: Current attention index (0.0-1.0)
        
        Returns:
            Break duration in seconds
        """
        base_duration = self.preferences['base_break_duration']
        max_duration = self.preferences['max_break_duration']
        
        # Apply subject tiredness multiplier
        subject = self.get_current_subject()
        if subject:
            multiplier = self.get_subject_tiredness(subject)
            base_duration = int(base_duration * multiplier)
        
        # Calculate weighted average (60% drowsiness, 30% distraction, 10% attention)
        # This gives more weight to drowsiness but considers all factors
        weighted_avg = (
            drowsiness_index * 0.6 +
            distraction_index * 0.3 +
            attention_index * 0.1
        )
        
        # Scale by weighted average: light (low) = small timer, heavy (high) = large timer
        # Map 0.0-1.0 to base_duration-max_duration
        duration = int(base_duration + (max_duration - base_duration) * weighted_avg)
        return min(duration, max_duration)
    
    def get_drowsiness_threshold(self) -> float:
        """Get the drowsiness threshold for triggering breaks."""
        return self.preferences['drowsiness_threshold']

