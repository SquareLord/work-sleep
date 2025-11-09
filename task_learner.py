"""AI learning system that adjusts weightages based on user reactions."""
from task_database import TaskDatabase
from typing import Dict, List, Optional
import numpy as np

class TaskLearner:
    def __init__(self, database: TaskDatabase):
        """
        Initialize task learning system.
        
        Args:
            database: TaskDatabase instance
        """
        self.db = database
    
    def get_initial_weightages(self, task_id: int, task_name: str) -> Dict[str, float]:
        """
        Get initial weightages for a task across 4 indices.
        For existing tasks (even with 0 sessions), use stored weights.
        For new tasks with no stored weights, attempt semantic transfer from similar tasks.
        If no similar tasks, fall back to curated default distribution (not uniform) to
        reflect empirically chosen priors, then normalize.
        
        Uses AI-powered semantic similarity to find related tasks and transfer their
        learned weights, even when task names don't share exact words.
        """
        index_keys = ['drowsiness', 'slouching', 'attention', 'yawn_score']

        # 1. Direct retrieval if task already exists
        weightages = self.db.get_task_weightages(task_id)
        if weightages:
            ts = weightages.get('total_sessions', 0)
            print(f"✓ Using stored weights for '{task_name}' (sessions={ts})")
            return {k: weightages.get(f'{k}_weight', 0.0) for k in index_keys}

        # 2. Semantic transfer from similar tasks
        similar_tasks = self.db.get_similar_tasks(task_name, limit=3)
        if similar_tasks:
            print(f"✓ Found {len(similar_tasks)} similar task(s) for '{task_name}':")
            for _, similar_name, similarity in similar_tasks:
                print(f"  - '{similar_name}' ({similarity*100:.1f}% match)")
            total_similarity = sum(sim for _, _, sim in similar_tasks)
            if total_similarity > 0:
                sums = {k: 0.0 for k in index_keys}
                for similar_task_id, _, similarity in similar_tasks:
                    similar_weights = self.db.get_task_weightages(similar_task_id)
                    if similar_weights:
                        weight = similarity / total_similarity
                        for k in index_keys:
                            sums[k] += similar_weights.get(f'{k}_weight', 0.0) * weight
                total = sum(sums.values())
                if total > 0:
                    transferred = {k: v / total for k, v in sums.items()}
                    print("  → Transferred weights from similar tasks")
                    return transferred

    # 3. Equal baseline (1/4 each)
        print(f"ℹ  No stored or similar tasks for '{task_name}'. Using equal defaults.")
        default = 1.0 / len(index_keys)
        return {k: default for k in index_keys}
    
    def calculate_break_duration(self, indices: Dict[str, float], weightages: Dict[str, float], scaler: float = 300.0) -> int:
        """
        Calculate recommended break duration based on weighted score and learned scaler.
        
        Args:
            indices: Dict with keys for 4 indices (each 0.0-1.0)
            weightages: Dict with same keys as indices (weights sum to 1.0)
            scaler: Learned multiplier representing user's burnout tendency (default 300.0 = 5 minutes at max tiredness)
        
        Returns:
            Recommended break duration in seconds
        
        Formula: duration = scaler × weighted_score
        
        The scaler adapts based on user behavior:
        - User alert before timer ends → scaler decreases (shorter breaks needed)
        - User drowsy after timer ends → scaler increases (longer breaks needed)
        - User alert right when timer ends → scaler unchanged (perfect timing)
        """
        index_keys = ['drowsiness', 'slouching', 'attention', 'yawn_score']
        # Calculate weighted tiredness score (0.0-1.0)
        weighted_score = sum(indices.get(k, 0.0) * weightages.get(k, 0.0) for k in index_keys)
        
        # Direct formula: duration = scaler × weighted_score
        duration = int(scaler * weighted_score)
        
        # Ensure minimum duration of 30 seconds (for very low tiredness)
        return max(30, duration)
    
    def calculate_weighted_tiredness(self, indices: Dict[str, float], weightages: Dict[str, float]) -> float:
        """
        Calculate weighted tiredness score for flagging.
        
        Args:
            indices: Dict with keys for 4 indices (each 0.0-1.0)
            weightages: Dict with same keys as indices (weights sum to 1.0)
        
        Returns:
            Weighted tiredness score (0.0-1.0)
        """
        index_keys = ['drowsiness', 'slouching', 'attention', 'yawn_score']
        return sum(indices.get(k, 0.0) * weightages.get(k, 0.0) for k in index_keys)

    def update_scaler(self, current_scaler: float, user_alert_before: bool, 
                      user_drowsy_after: bool, became_alert_at: Optional[float] = None, 
                      break_duration: float = 180.0, learning_rate: float = 0.15) -> float:
        """
        Update scaler based on user alertness during break.

        The scaler determines break duration via: duration = scaler × weighted_score
        This function adjusts the scaler based on when the user became alert, learning
        their individual burnout tendency over time.

        Args:
            current_scaler: Current scaler value (higher = longer breaks)
            user_alert_before: True if user was alert before timer finished
            user_drowsy_after: True if user was still drowsy after timer finished
            became_alert_at: When user became alert (seconds into break), None if never became alert
            break_duration: Total break duration in seconds
            learning_rate: How quickly to adapt (0.0-1.0, higher = faster)

        Returns:
            Updated scaler value
        """
        if user_alert_before and became_alert_at is not None:
            # User became alert before timer finished - adjust based on HOW early
            # If they became alert very early (< 50% through), decrease more aggressively
            # If they became alert near the end (> 80% through), only decrease slightly
            progress_ratio = became_alert_at / break_duration

            if progress_ratio < 0.3:
                # Very early - timer way too long
                adjustment = learning_rate * 1.5
            elif progress_ratio < 0.6:
                # Moderately early - timer somewhat too long
                adjustment = learning_rate * 1.0
            else:
                # Near the end - timer only slightly too long
                adjustment = learning_rate * 0.5

            new_scaler = current_scaler * (1.0 - adjustment)
            print(f"User became alert at {became_alert_at:.1f}s / {break_duration}s ({progress_ratio:.1%}) - decreasing scaler by {adjustment:.2%}")

        elif user_drowsy_after:
            # User was still drowsy after timer - timer was too short, increase scaler
            new_scaler = current_scaler * (1.0 + learning_rate)
            print(f"User still drowsy after timer - increasing scaler by {learning_rate:.2%}")
        else:
            # User was alert right as timer finished - perfect timing, keep scaler
            new_scaler = current_scaler
            print("User alert at timer end - perfect timing, keeping scaler")

        # Clamp scaler to reasonable range (50 to 600 seconds at max tiredness)
        return max(50.0, min(600.0, new_scaler))
    
    def adjust_weightages(self, task_id: int, break_history: List[Dict]) -> Dict[str, float]:
        """
    Adjust weightages based on user reactions to breaks for 4 indices.
        
        Learning rules:
        - If user is alert before timer: reduce weight of the dominant index
        - If user is drowsy after timer: increase weight of the dominant index
        - Balance weights based on which index is most predictive
        
        Args:
            task_id: Task ID
            break_history: List of break events with user reactions and all 4 indices
        
        Returns:
            Adjusted weightages dict with all 7 keys
        """
        index_keys = ['drowsiness', 'slouching', 'attention', 'yawn_score']
        if not break_history:
            # No history, return current weights
            current = self.db.get_task_weightages(task_id)
            if current:
                return {k: current.get(f'{k}_weight', 1.0/len(index_keys)) for k in index_keys}
            default = 1.0 / len(index_keys)
            return {k: default for k in index_keys}
        # Get current weightages
        current = self.db.get_task_weightages(task_id)
        if not current:
            default = 1.0 / len(index_keys)
            weights = {k: default for k in index_keys}
        else:
            weights = {k: current.get(f'{k}_weight', 1.0/len(index_keys)) for k in index_keys}
        # Analyze break history
        total_adjustments = {k: 0.0 for k in index_keys}
        adjustment_count = 0
        for break_event in break_history:
            # Determine dominant index (highest value)
            index_values = {k: break_event.get(f'{k}_index', 0) for k in index_keys}
            dominant = max(index_values.keys(), key=lambda k: index_values[k])
            # Adjust based on user reaction
            if break_event.get('alert_before'):
                total_adjustments[dominant] -= 0.05
                adjustment_count += 1
            elif break_event.get('drowsy_after'):
                total_adjustments[dominant] += 0.05
                adjustment_count += 1
        # Apply adjustments (averaged)
        if adjustment_count > 0:
            for k in index_keys:
                weights[k] += total_adjustments[k] / adjustment_count
        # Ensure weights stay in reasonable range (0.05 to 0.50)
        for k in index_keys:
            weights[k] = max(0.05, min(0.50, weights[k]))
        # Normalize to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            for k in index_keys:
                weights[k] /= total
        return weights
    
    def learn_from_session(self, task_id: int, break_history: List[Dict]):
        """
        Learn from a completed session and update weightages in database for all 7 indices.
        Args:
            task_id: Task ID
            break_history: List of break events from the session
        """
        if not break_history:
            return None
        # Adjust weightages based on session
        new_weightages = self.adjust_weightages(task_id, break_history)
        # Return new weightages to caller so caller (main) can persist them per-subject if desired
        return new_weightages

