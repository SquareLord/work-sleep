"""Break overlay system that blocks user input and displays timer."""
import tkinter as tk
from tkinter import font
import time
import threading
from pynput import mouse, keyboard
import platform
import subprocess
import sys
from typing import Callable, Optional, Dict

def play_sound(frequency=440, duration=200):
    """Play a gentle sound (beep)."""
    try:
        system = platform.system()
        if system == "Windows":
            try:
                import winsound  # Standard Windows sound API
                beep_fn = getattr(winsound, 'Beep', None)
                if callable(beep_fn):
                    beep_fn(int(frequency), int(duration))  # type: ignore[attr-defined]
                    return
                # Fallback: simple console bell
                print("\a", end="", flush=True)
                return
            except ImportError:
                # Final fallback: attempt PowerShell beep (non-blocking)
                try:
                    subprocess.run(["powershell", "-Command", f"[console]::beep({int(frequency)},{int(duration)})"],
                                   timeout=1, capture_output=True, stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    print("\a", end="", flush=True)
                    return
        elif system == "Linux":
            # Try multiple methods
            try:
                subprocess.run(["beep", "-f", str(frequency), "-l", str(duration)], 
                             check=False, timeout=1, capture_output=True, stderr=subprocess.DEVNULL)
            except:
                try:
                    subprocess.run(["paplay", "--volume=32768", "/usr/share/sounds/freedesktop/stereo/message.ogg"],
                                 timeout=1, capture_output=True, stderr=subprocess.DEVNULL)
                except:
                    try:
                        subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Left.wav"],
                                     timeout=1, capture_output=True, stderr=subprocess.DEVNULL)
                    except:
                        print("\a", end="", flush=True)
        elif system == "Darwin":  # macOS
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], 
                             timeout=1, capture_output=True, stderr=subprocess.DEVNULL)
            except:
                print("\a", end="", flush=True)
        else:
            # Fallback: system bell
            print("\a", end="", flush=True)
    except:
        # Silently fail if sound can't be played
        try:
            print("\a", end="", flush=True)  # Try system bell
        except:
            pass

class BreakOverlay:
    def __init__(self, parent_root, duration: int, on_complete: Optional[Callable] = None, 
                 detector=None, camera=None, show_indices=True,
                 task_learner=None, weightages: Optional[Dict] = None, tiredness_threshold: float = 0.30):
        """
        Initialize break overlay with smart exit logic.
        
        Args:
            parent_root: Parent tkinter root window
            duration: Break duration in seconds
            on_complete: Callback function when break completes.
                        Should accept (alert_before, drowsy_after) parameters.
            detector: DrowsinessDetector instance for monitoring during break
            camera: CameraCapture instance for getting frames
            show_indices: Whether to show drowsiness indices during break
            task_learner: TaskLearner instance for calculating weighted tiredness
            weightages: Current task weightages for tiredness calculation
            tiredness_threshold: Threshold for considering user tired (default 0.30)
        """
        self.parent_root = parent_root
        self.duration = duration
        self.on_complete = on_complete
        self.start_time = None
        self.remaining_time = duration
        self.is_active = False
        self.window = None
        self.detector = detector
        self.camera = camera
        if self.camera and hasattr(self.camera, 'start'):
            self.camera.start()
        self.show_indices = show_indices
        self.task_learner = task_learner
        self.weightages = weightages if weightages else {}
        self.tiredness_threshold = tiredness_threshold
        
        # For alert monitoring after timer
        self.alert_start_time = None
        self.alert_required_duration = 10  # Must be alert for 10 seconds
        self.is_waiting_for_alert = False
        
        # Track user reactions for learning
        self.user_alert_before_timer = False
        self.user_drowsy_after_timer = False
        self.timer_finished_time = None
        self.became_alert_at = None  # Track when user became alert during break (seconds elapsed)
        
        # Input blockers
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # Play start sound
        play_sound(440, 200)  # Gentle beep
    
    def block_input(self):
        """Block mouse and keyboard input."""
        try:
            def on_move(x, y):
                return False
            
            def on_click(x, y, button, pressed):
                return False
            
            def on_scroll(x, y, dx, dy):
                return False
            
            # Removed unused on_press function
            
            def on_release(key):
                return False
            
            self.mouse_listener = mouse.Listener(
                on_move=on_move,
                on_click=on_click,
                on_scroll=on_scroll,
                suppress=True
            )
            
            self.keyboard_listener = keyboard.Listener(
                suppress=True
            )
            
            self.mouse_listener.start()
            self.keyboard_listener.start()
        except Exception as e:
            # Input blocking might fail on some systems (e.g., Linux without permissions)
            # The overlay window itself will still block most interaction
            print(f"Warning: Could not block input: {e}")
    
    def unblock_input(self):
        """Unblock mouse and keyboard input."""
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
    
    def create_overlay(self):
        """Create fullscreen overlay window."""
        print("Creating overlay window...")
        try:
            self.window = tk.Toplevel(self.parent_root)
            print(f"Window created: {self.window}")
            self.window.title("Break Time")
            self.window.attributes('-fullscreen', True)
            self.window.attributes('-topmost', True)
            self.window.configure(bg='#1a1a1a')
            self.window.overrideredirect(True)
            self.window.focus_force()
            self.window.grab_set()  # Grab all events - blocks interaction with other windows
            print("Window configured successfully")
            
            # Make window uncloseable
            self.window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            # Center window immediately after creation
            self.window.update_idletasks()
            if self.window and self.window.winfo_exists():
                width = self.window.winfo_screenwidth()
                height = self.window.winfo_screenheight()
                self.window.geometry(f"{width}x{height}+0+0")
                print(f"Window geometry set: {width}x{height}")
        except Exception as e:
            print(f"Error creating overlay window: {e}")
            import traceback
            traceback.print_exc()
            self.is_active = False
            if self.on_complete:
                self.on_complete(alert_before=False, drowsy_after=False)
            return

        # Center content
        frame = tk.Frame(self.window, bg='#1a1a1a')
        frame.pack(expand=True)
        
        # Title
        title_font = font.Font(family='Arial', size=48, weight='bold')
        title_label = tk.Label(
            frame,
            text="Break Time!",
            font=title_font,
            fg='#ffffff',
            bg='#1a1a1a'
        )
        title_label.pack(pady=20)
        
        # Timer
        timer_font = font.Font(family='Arial', size=72, weight='bold')
        self.timer_label = tk.Label(
            frame,
            text=self.format_time(self.remaining_time),
            font=timer_font,
            fg='#4CAF50',
            bg='#1a1a1a'
        )
        self.timer_label.pack(pady=40)
        
        # Indices display (if enabled)
        if self.show_indices and self.detector and self.camera:
            indices_frame = tk.Frame(frame, bg='#1a1a1a')
            indices_frame.pack(pady=20)
            
            indices_font = font.Font(family='Arial', size=18)
            self.indices_label = tk.Label(
                indices_frame,
                text="Monitoring attention...",
                font=indices_font,
                fg='#cccccc',
                bg='#1a1a1a'
            )
            self.indices_label.pack()
        
        # Message
        message_font = font.Font(family='Arial', size=24)
        self.message_label = tk.Label(
            frame,
            text="Take a break! Input is blocked until you are alert.",
            font=message_font,
            fg='#cccccc',
            bg='#1a1a1a'
        )
        self.message_label.pack(pady=20)
        
        # Mark overlay active before starting timer/monitoring so callbacks run
        self.is_active = True
        print("Overlay marked as active")

        # Start blocking input
        self.block_input()
        print("Input blocking started")

        # Start timer update
        self.start_time = time.time()
        print(f"Timer started at {self.start_time}, duration: {self.duration}s")
        self.window.after(100, self.update_timer)

        # Start monitoring indices if enabled
        if self.show_indices and self.detector and self.camera:
            self.window.after(1000, self.monitor_indices)
            print("Index monitoring scheduled")
        
        # Center window (check if window still exists)
        if self.window and self.window.winfo_exists():
            self.window.update_idletasks()
            width = self.window.winfo_screenwidth()
            height = self.window.winfo_screenheight()
            self.window.geometry(f"{width}x{height}+0+0")
            print(f"Final window geometry: {width}x{height}")
        
        print("Overlay creation complete!")
        
    # self.is_active already set above
    
    def monitor_indices(self):
        """Monitor attention indices during break using weighted tiredness."""
        if not self.is_active or not self.window:
            return
        
        try:
            # Get current frame
            if self.camera and hasattr(self.camera, 'get_current_frame'):
                result = self.camera.get_current_frame()
            else:
                result = None
            if result and self.detector:
                frame, _ = result
                # Get core 4 indices
                drowsiness_index, slouching_index, attention_index, yawn_score, _ = self.detector.calculate_drowsiness_index(frame)
                
                # Calculate weighted tiredness if task_learner is available
                if self.task_learner and self.weightages:
                    indices_dict = {
                        'drowsiness': drowsiness_index,
                        'slouching': slouching_index,
                        'attention': attention_index,
                        'yawn_score': yawn_score
                    }
                    weighted_tiredness = self.task_learner.calculate_weighted_tiredness(indices_dict, self.weightages)
                else:
                    # Fallback to simple average
                    weighted_tiredness = (drowsiness_index + slouching_index + attention_index) / 3.0
                
                # Update display
                if hasattr(self, 'indices_label'):
                    self.indices_label.config(
                        text=f"Weighted Tiredness: {weighted_tiredness:.2f} (Threshold: {self.tiredness_threshold:.2f})",
                        fg='#4CAF50' if weighted_tiredness < self.tiredness_threshold else '#ffaa00' if weighted_tiredness < 0.5 else '#ff4444'
                    )
        except:
            pass
        
        # Continue monitoring
        if self.is_active and self.window:
            self.window.after(1000, self.monitor_indices)  # Update every second
    
    def format_time(self, seconds: int) -> str:
        """Format seconds as MM:SS."""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"
    
    def update_timer(self):
        """Update timer display with smart exit logic."""
        print(f"update_timer called - is_active: {self.is_active}, window exists: {self.window is not None}")
        if not self.is_active:
            print("update_timer: not active, returning")
            return
        
        if not self.window:
            print("update_timer: no window, returning")
            return
        
        try:
            print("update_timer: starting timer logic")
            if self.start_time is None:
                self.start_time = time.time()

            elapsed = time.time() - self.start_time
            self.remaining_time = max(0, int(self.duration - elapsed))

            # Update timer display
            if hasattr(self, 'timer_label'):
                self.timer_label.config(text=self.format_time(self.remaining_time))

            # Track when user becomes alert during break (for learning)
            if self.remaining_time > 0 and self.became_alert_at is None and self.detector and self.camera and self.task_learner and self.weightages:
                try:
                    result = self.camera.get_current_frame()
                    if result:
                        frame, _ = result
                        # Get core 4 indices
                        drowsiness_idx, slouching_idx, attention_idx, yawn_score, _ = self.detector.calculate_drowsiness_index(frame)

                        indices_dict = {
                            'drowsiness': drowsiness_idx,
                            'slouching': slouching_idx,
                            'attention': attention_idx,
                            'yawn_score': yawn_score
                        }
                        weighted_tiredness = self.task_learner.calculate_weighted_tiredness(indices_dict, self.weightages)

                        # Track when user becomes alert (but don't exit early)
                        if weighted_tiredness < self.tiredness_threshold:
                            elapsed = time.time() - self.start_time
                            self.became_alert_at = elapsed
                            self.user_alert_before_timer = True
                            print(f"User became alert at {elapsed:.1f}s into {self.duration}s break")
                except:
                    pass

            if self.remaining_time <= 0:
                if not self.is_waiting_for_alert:
                    self.timer_finished_time = time.time()
                    # Timer finished, check if user is still tired
                    if self.detector and self.camera and self.task_learner and self.weightages:
                        try:
                            result = self.camera.get_current_frame()
                            if result:
                                frame, _ = result
                                # Get core 4 indices
                                drowsiness_idx, slouching_idx, attention_idx, yawn_score, _ = self.detector.calculate_drowsiness_index(frame)
                                
                                indices_dict = {
                                    'drowsiness': drowsiness_idx,
                                    'slouching': slouching_idx,
                                    'attention': attention_idx,
                                    'yawn_score': yawn_score
                                }
                                weighted_tiredness = self.task_learner.calculate_weighted_tiredness(indices_dict, self.weightages)
                                
                                # If still tired, require 10s of alertness
                                if weighted_tiredness >= self.tiredness_threshold:
                                    self.user_drowsy_after_timer = True
                                    self.start_alert_monitoring()
                                else:
                                    # User is alert, exit immediately
                                    self.complete_break()
                                    return
                        except:
                            # If error, just complete the break
                            self.complete_break()
                            return
                    else:
                        # No monitoring available, just complete
                        self.complete_break()
                        return
                else:
                    # Check if alert requirement met
                    if self.check_alert_requirement():
                        self.complete_break()
                        return
                    else:
                        # Still not alert enough, keep waiting
                        self.update_alert_status()
            else:
                # Timer still running, schedule next update
                if self.window and self.is_active:
                    self.window.after(100, self.update_timer)
        except Exception as e:
            # If there's an error, still try to continue
            if self.window and self.is_active:
                self.window.after(100, self.update_timer)
    
    def start_alert_monitoring(self):
        """Start monitoring for alert state after timer finishes."""
        self.is_waiting_for_alert = True
        self.alert_start_time = None
        if hasattr(self, 'message_label'):
            self.message_label.config(
                text="Timer finished! Stay alert for 10 seconds to resume.",
                fg='#ffaa00'
            )
        # Play sound to indicate timer finished
        play_sound(550, 200)
    
    def check_alert_requirement(self) -> bool:
        """Check if user has been alert for required duration using weighted tiredness."""
        if not self.detector or not self.camera or not self.task_learner or not self.weightages:
            # If no detector, just return True after timer
            return True
        
        try:
            result = self.camera.get_current_frame()
            if result:
                frame, _ = result
                # Get all 8 indices
                drowsiness_idx, slouching_idx, attention_idx, yawn_score, _ = self.detector.calculate_drowsiness_index(frame)
                
                indices_dict = {
                    'drowsiness': drowsiness_idx,
                    'slouching': slouching_idx,
                    'attention': attention_idx,
                    'yawn_score': yawn_score
                }
                weighted_tiredness = self.task_learner.calculate_weighted_tiredness(indices_dict, self.weightages)
                
                # Consider alert if weighted tiredness is below threshold
                is_alert = weighted_tiredness < self.tiredness_threshold
                
                if is_alert:
                    if self.alert_start_time is None:
                        self.alert_start_time = time.time()
                    
                    # Check if alert for required duration
                    alert_duration = time.time() - self.alert_start_time
                    return alert_duration >= self.alert_required_duration
                else:
                    # Not alert - reset alert start time
                    if weighted_tiredness >= 0.5:
                        self.user_drowsy_after_timer = True
                    # Reset timer
                    self.alert_start_time = None
                    return False
        except:
            # On error, allow continuation
            return True
        
        return False
    
    def update_alert_status(self):
        """Update alert monitoring status display using weighted tiredness."""
        if not self.is_waiting_for_alert or not self.detector or not self.camera or not self.task_learner or not self.weightages:
            return
        
        try:
            result = self.camera.get_current_frame()
            if result:
                frame, _ = result
                # Get all 8 indices
                drowsiness_idx, slouching_idx, attention_idx, yawn_score, _ = self.detector.calculate_drowsiness_index(frame)
                
                indices_dict = {
                    'drowsiness': drowsiness_idx,
                    'slouching': slouching_idx,
                    'attention': attention_idx,
                    'yawn_score': yawn_score
                }
                weighted_tiredness = self.task_learner.calculate_weighted_tiredness(indices_dict, self.weightages)
                
                is_alert = weighted_tiredness < self.tiredness_threshold
                
                if is_alert and self.alert_start_time:
                    remaining = self.alert_required_duration - (time.time() - self.alert_start_time)
                    if remaining > 0:
                        if hasattr(self, 'message_label'):
                            self.message_label.config(
                                text=f"Stay alert! {remaining:.1f} seconds remaining...",
                                fg='#4CAF50'
                            )
                    else:
                        if hasattr(self, 'message_label'):
                            self.message_label.config(
                                text="Alert! Resuming in a moment...",
                                fg='#4CAF50'
                            )
                else:
                    if hasattr(self, 'message_label'):
                        self.message_label.config(
                            text="Please focus on your screen and stay alert.",
                            fg='#ffaa00'
                        )
                    self.alert_start_time = None
        except:
            pass
        
        # Continue checking
        if self.is_active and self.window:
            self.window.after(100, self.update_alert_status)
    
    def complete_break(self):
        """Complete the break and close overlay."""
        self.is_active = False
        self.unblock_input()
        
        # Play completion sound
        play_sound(660, 200)
        
        if self.window:
            self.window.grab_release()
            self.window.destroy()
        
        if self.on_complete:
            # Pass user reaction data to callback
            self.on_complete(
                alert_before=self.user_alert_before_timer,
                drowsy_after=self.user_drowsy_after_timer,
                became_alert_at=self.became_alert_at  # When user became alert (seconds into break)
            )
    
    def start(self):
        """Start the break overlay (must be called from main thread for tkinter)."""
        # Note: Tkinter must run in main thread, so this should be called
        # via root.after() from the main application
        self.create_overlay()
