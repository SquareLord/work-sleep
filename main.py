"""Main application for Study Sleep - Drowsiness Detection & Break System."""
import cv2
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from typing import Optional
from camera_capture import CameraCapture
from drowsiness_detector import DrowsinessDetector
from preferences import PreferencesManager
from break_overlay import BreakOverlay
from task_database import TaskDatabase
from task_learner import TaskLearner
from input_monitor import InputMonitor

class StudySleepApp:
    def __init__(self, root):
        """Initialize the main application."""
        self.root = root
        self.root.title("Study Sleep - Drowsiness Detection")
        self.root.geometry("800x800")  # Fixed aspect ratio
        self.root.resizable(False, False)  # Prevent resizing
        
        # Components
        self.camera = CameraCapture(capture_interval=0.3)  # Capture every 0.3 seconds for faster response
        self.detector = DrowsinessDetector()
        self.preferences = PreferencesManager()
        self.task_db = TaskDatabase()
        self.task_learner = TaskLearner(self.task_db)
        
        # State
        self.is_monitoring = False
        self.reference_set = False
        self.diagnostic_photo_valid = True  # Track if diagnostic photo has sufficient data
        self.last_break_time = 0
        self.min_break_interval = 60  # Minimum seconds between breaks
        
        # Track indices over time for weighted threshold
        self.index_history = []  # List of (timestamp, weighted_tiredness, indices_dict)
        self.high_index_start_time = None  # When weighted tiredness first went above threshold
        self.trigger_threshold = 0.30  # Weighted tiredness threshold for triggering
        self.trigger_duration = 3.0  # Must be above threshold for 3 seconds
        
        # Individual index warning tracking (for popup warnings)
        self.index_warning_threshold = 0.5  # Individual index threshold for warnings
        self.index_warning_cooldown = 60.0  # 60 second cooldown per index type
        self.last_index_warning_times = {
            'drowsiness': 0.0, 'slouching': 0.0, 'attention': 0.0,
            'yawn_score': 0.0
        }
        
        # Task tracking
        self.current_task = None
        self.current_task_id = None
        self.current_session_id = None
        self.current_subject_id = None
        self.current_weightages = {
            'drowsiness': 0.25, 'slouching': 0.25, 'attention': 0.25,
            'yawn_score': 0.25
        }
        self.current_scaler = 300.0  # Default 300 seconds at max tiredness (5 minutes)
        self.session_breaks = []  # Track breaks for learning
        self.breaks_triggered = 0
        self.total_break_time = 0
        self.last_action_was_timer = False  # Track reminder/timer alternation
        self.dominant_index_name = None  # Track which index triggered the alert
        self.break_active = False  # Prevent re-triggering while a break is running
        
        # UI Setup
        self.setup_ui()

        # Input monitor (optional)
        try:
            self.input_monitor = InputMonitor()
        except Exception:
            self.input_monitor = None
        
        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Study Sleep - Drowsiness Detection",
            font=('Arial', 20, 'bold')
        )
        title_label.pack(pady=10)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=10)
        # Add warning label for insufficient data
        self.insufficient_data_label = ttk.Label(status_frame, text="", font=('Arial', 10), foreground="red")
        self.insufficient_data_label.grid(row=3, column=0, columnspan=5, pady=5)
        
        self.status_label = ttk.Label(
            status_frame,
            text="Not monitoring",
            font=('Arial', 13)
        )
        self.status_label.grid(row=0, column=0, columnspan=5, pady=5)

        # Indices: split into two rows if needed
        self.drowsiness_label = ttk.Label(status_frame, text="Drowsiness: --", font=('Arial', 9))
        self.drowsiness_label.grid(row=1, column=0, padx=2, pady=2)
        self.slouching_label = ttk.Label(status_frame, text="Slouching: --", font=('Arial', 9))
        self.slouching_label.grid(row=1, column=1, padx=2, pady=2)
        self.attention_label = ttk.Label(status_frame, text="Attention: --", font=('Arial', 9))
        self.attention_label.grid(row=1, column=2, padx=2, pady=2)
        self.yawn_score_label = ttk.Label(status_frame, text="Yawn: --", font=('Arial', 9))
        self.yawn_score_label.grid(row=1, column=3, padx=2, pady=2)
        # Removed eye_closure_label

    # Removed labels for head_nodding, eye_smoothness, blink_variance
        
        # New label for weighted tiredness
        self.weighted_tiredness_label = ttk.Label(status_frame, text="Weighted Tiredness: --", font=('Arial', 10, 'bold'))
        self.weighted_tiredness_label.grid(row=2, column=3, padx=2, pady=2)
        
        # Task input frame
        task_frame = ttk.LabelFrame(main_frame, text="Current Task", padding="10")
        task_frame.pack(fill=tk.X, pady=10)
        
        task_input_frame = ttk.Frame(task_frame)
        task_input_frame.pack(fill=tk.X)
        
        ttk.Label(task_input_frame, text="Task:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.task_entry = ttk.Entry(task_input_frame, font=('Arial', 10), width=40)
        self.task_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.task_entry.bind('<Return>', lambda e: self.set_task())
        
        ttk.Button(
            task_input_frame,
            text="Set Task",
            command=self.set_task
        ).pack(side=tk.LEFT, padx=5)
        
        self.task_status_label = ttk.Label(
            task_frame,
            text="No task set",
            font=('Arial', 9),
            foreground='gray'
        )
        self.task_status_label.pack(pady=5)
        
        # Reference image frame
        ref_frame = ttk.LabelFrame(main_frame, text="Reference Image", padding="10")
        ref_frame.pack(fill=tk.X, pady=10)
        
        self.reference_status_label = ttk.Label(
            ref_frame,
            text="No reference image set",
            font=('Arial', 10)
        )
        self.reference_status_label.pack()
        
        ttk.Button(
            ref_frame,
            text="Capture Reference Image",
            command=self.capture_reference
        ).pack(pady=5)
        
        # Preferences frame
        pref_frame = ttk.LabelFrame(main_frame, text="Preferences", padding="10")
        pref_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            pref_frame,
            text="Set Current Subject",
            command=self.set_subject
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            pref_frame,
            text="Set Subject Tiredness",
            command=self.set_tiredness
        ).pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=20)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        self.start_button = ttk.Button(
            button_frame,
            text="Start Monitoring",
            command=self.start_monitoring
        )
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="Stop Monitoring",
            command=self.stop_monitoring,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        # Debug frame (moved after controls so it doesn't push buttons off screen)
        debug_frame = ttk.LabelFrame(main_frame, text="Debug Values (Raw Weights)", padding="10")
        debug_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create scrollable text widget for debug output
        debug_text_frame = ttk.Frame(debug_frame)
        debug_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.debug_text = tk.Text(debug_text_frame, height=8, font=('Courier', 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(debug_text_frame, orient=tk.VERTICAL, command=self.debug_text.yview)
        self.debug_text.configure(yscrollcommand=scrollbar.set)
        
        self.debug_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def capture_reference(self):
        """Capture reference diagnostic image."""
        if not self.camera.is_running:
            if not self.camera.start():
                messagebox.showerror("Error", "Failed to start camera")
                return
        
        # Get current frame
        result = self.camera.get_current_frame()
        if result:
            frame, _ = result
            self.detector.set_reference(frame)
            
            # Check if reference data is valid (has non-zero values)
            ref_vec = self.detector.get_reference_vector()
            if ref_vec.get('shoulder_ratio') is not None and ref_vec.get('eye_aspect_ratio') is not None:
                self.diagnostic_photo_valid = True
                self.insufficient_data_label.config(text="")
            else:
                self.diagnostic_photo_valid = False
                self.insufficient_data_label.config(
                    text="Insufficient data for tracking. Please take a better diagnostic photo in good lighting.",
                    foreground='red'
                )
            
            self.reference_set = True
            self.reference_status_label.config(
                text="Reference image captured successfully",
                foreground='green'
            )
            # Ask for subject name to associate with reference
            subject = simpledialog.askstring("Subject Name", "Enter subject name (optional):")
            try:
                ref_vec = self.detector.get_reference_vector()
                fp = self.detector.get_reference_fingerprint()
                # store subject in DB
                subject_id = None
                try:
                    subject_id = self.task_db.get_or_create_subject(fp, reference_json=str(ref_vec), name=subject)
                    self.current_subject_id = subject_id
                except Exception:
                    subject_id = None

                # Set current subject in preferences if name provided
                if subject:
                    self.preferences.set_current_subject(subject)

                # Start session with subject if we have a current task
                if self.current_task_id and subject_id:
                    # use subject-aware session starter
                    self.current_session_id = self.task_db.start_session_with_subject(self.current_task_id, subject_id)

            except Exception:
                pass

            messagebox.showinfo("Success", "Reference image captured!")
        else:
            messagebox.showerror("Error", "Failed to capture frame")
    
    def set_task(self):
        """Set the current task and initialize learning."""
        task_name = self.task_entry.get().strip()
        if not task_name:
            messagebox.showwarning("Warning", "Please enter a task name")
            return
        
        # Get or create task in database
        task_id = self.task_db.get_or_create_task(task_name)
        self.current_task = task_name
        self.current_task_id = task_id
        
        # Get initial weightages (from learning or equal)
        # Try to get subject-specific weightages if we have a current subject
        indices_keys = ['drowsiness', 'slouching', 'attention', 'yawn_score']

        if self.current_subject_id:
            w = self.task_db.get_task_weightages_for_subject(task_id, self.current_subject_id)
            if w:
                self.current_weightages = {k: w.get(f'{k}_weight', 0.1) for k in indices_keys}
                # Load scaler from database
                self.scaler = w.get('scaler', 300.0)
            else:
                self.current_weightages = self.task_learner.get_initial_weightages(task_id, task_name)
                self.scaler = 300.0  # Default for new task
        else:
            self.current_weightages = self.task_learner.get_initial_weightages(task_id, task_name)
            self.scaler = 300.0  # Default for new task
        
        # Start new session
        self.current_session_id = self.task_db.start_session(task_id)
        self.session_breaks = []
        self.breaks_triggered = 0
        self.total_break_time = 0
        
        # Update UI
        self.task_status_label.config(
            text=(
                f"Task: {task_name} | Weights: "
                f"D={self.current_weightages['drowsiness']:.2f}, "
                f"S={self.current_weightages['slouching']:.2f}, "
                f"A={self.current_weightages['attention']:.2f}, "
                f"Y={self.current_weightages['yawn_score']:.2f}"
            ),
            foreground='green'
        )
        
        messagebox.showinfo("Task Set", f"Task '{task_name}' set. Learning system initialized.")
    
    def set_subject(self):
        """Set the current subject."""
        subject = simpledialog.askstring(
            "Set Subject",
            "Enter current subject name:"
        )
        if subject:
            # Try to find subject in DB and load reference if present
            subj = self.task_db.get_subject_by_name(subject)
            if subj:
                self.current_subject_id = subj['id']
                # attempt to load reference_json
                ref_json = self.task_db.get_subject_reference(self.current_subject_id)
                if ref_json:
                    try:
                        import json
                        ref = json.loads(ref_json.replace("'", '"'))
                        # Set detector references if values present
                        if 'eye_aspect_ratio' in ref and ref['eye_aspect_ratio'] is not None:
                            self.detector.reference_eye_aspect_ratio = ref['eye_aspect_ratio']
                        if 'shoulder_angle' in ref and ref['shoulder_angle'] is not None:
                            self.detector.reference_shoulder_angle = ref['shoulder_angle']
                        if 'head_pose' in ref and ref['head_pose'] is not None:
                            self.detector.reference_head_pose = ref['head_pose']
                    except Exception:
                        pass
            else:
                # create a simple subject entry with no reference yet
                try:
                    fp = ''
                    sid = self.task_db.get_or_create_subject(fp, reference_json=None, name=subject)
                    self.current_subject_id = sid
                except Exception:
                    self.current_subject_id = None

            self.preferences.set_current_subject(subject)
            messagebox.showinfo("Success", f"Current subject set to: {subject}")
    
    def set_tiredness(self):
        """Set tiredness multiplier for a subject."""
        subject = simpledialog.askstring(
            "Set Tiredness",
            "Enter subject name:"
        )
        if not subject:
            return
        
        multiplier_str = simpledialog.askstring(
            "Set Tiredness",
            f"Enter tiredness multiplier for {subject} (e.g., 1.5 for 50% more tired):"
        )
        if multiplier_str:
            try:
                multiplier = float(multiplier_str)
                self.preferences.set_subject_tiredness(subject, multiplier)
                messagebox.showinfo(
                    "Success",
                    f"Tiredness multiplier for {subject} set to {multiplier}"
                )
            except ValueError:
                messagebox.showerror("Error", "Invalid multiplier value")
    
    def start_monitoring(self):
        """Start monitoring for drowsiness."""
        # Check if task name is set
        if not self.current_task or not self.current_task.strip():
            messagebox.showwarning(
                "Warning",
                "Please enter a task name first!"
            )
            return
        
        if not self.reference_set:
            messagebox.showwarning(
                "Warning",
                "Please capture a reference image first!"
            )
            return
        
        # Start camera if not already running
        if not self.camera.is_running:
            if not self.camera.start():
                messagebox.showerror("Error", "Failed to start camera")
                return
        
        self.is_monitoring = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Monitoring...", foreground='green')
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        # Start input monitor if available
        try:
            if self.input_monitor:
                self.input_monitor.start()
        except Exception:
            pass
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.is_monitoring = False
        self.camera.stop()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Not monitoring", foreground='black')
        self.drowsiness_label.config(text="Drowsiness Index: --")
        self.slouching_label.config(text="Slouching Index: --")
        self.attention_label.config(text="Attention Index: --")
        self.yawn_score_label.config(text="Yawn Score: --")
        
        # End session and learn from it
        if self.current_session_id:
            self.end_session()
        # Stop input monitor
        try:
            if self.input_monitor:
                self.input_monitor.stop()
        except Exception:
            pass
    
    def monitoring_loop(self):
        """Main monitoring loop running in separate thread."""
        while self.is_monitoring:
            result = self.camera.capture_frame()
            if result:
                frame, timestamp = result
                
                # Calculate core 4 indices
                drowsiness_index, slouching_index, attention_index, yawn_score, debug_info = self.detector.calculate_drowsiness_index(frame)
                
                current_time = time.time()
                
                # Create indices dict for calculations
                indices_dict = {
                    'drowsiness': drowsiness_index,
                    'slouching': slouching_index,
                    'attention': attention_index,
                    'yawn_score': yawn_score
                }
                
                # Calculate weighted tiredness using task-specific weightages
                weighted_tiredness = self.task_learner.calculate_weighted_tiredness(
                    indices_dict,
                    self.current_weightages
                )
                
                # Track index history (keep last 10 seconds)
                self.index_history.append((current_time, weighted_tiredness, indices_dict.copy()))
                # Remove old entries (older than 10 seconds)
                self.index_history = [
                    entry for entry in self.index_history 
                    if current_time - entry[0] < 10.0
                ]
                
                # If a break is currently active, skip triggering logic
                if self.break_active:
                    self.high_index_start_time = None
                    self.root.after(0, lambda d_idx=drowsiness_index, sl_idx=slouching_index,
                        att_idx=attention_index, y_idx=yawn_score: 
                        self.update_display(d_idx, sl_idx, att_idx, y_idx))
                    time.sleep(0.05)
                    continue

                # Update UI (must be done in main thread)
                # Add input monitor metrics if available
                try:
                    if hasattr(self, 'input_monitor') and self.input_monitor:
                        input_metrics = self.input_monitor.get_metrics()
                        debug_info['input_metrics'] = input_metrics
                except Exception:
                    pass

                self.root.after(0, lambda d_idx=drowsiness_index, sl_idx=slouching_index,
                    att_idx=attention_index, y_idx=yawn_score, dbg=debug_info: 
                    self.update_display(d_idx, sl_idx, att_idx, y_idx, debug_info=dbg))
                
                # Remove popup warnings for individual indices
                # Remove reminder alternation logic
                if weighted_tiredness >= 0.20:
                    if self.high_index_start_time is None:
                        self.high_index_start_time = current_time
                    time_above_threshold = current_time - self.high_index_start_time
                    if time_above_threshold >= 4.0:
                        # Always trigger timer, no alternation
                        if current_time - self.last_break_time >= self.min_break_interval:
                            # Find highest raw value index (not weighted)
                            highest_index = max(indices_dict.keys(), key=lambda k: indices_dict[k])
                            self.dominant_index_name = highest_index
                            self.high_index_start_time = None

                            # --- Compute average index values over session ---
                            index_keys = ['drowsiness', 'slouching', 'attention', 'yawn_score']
                            # Gather all index_dicts since last break
                            recent_indices = [entry[2] for entry in self.index_history]
                            avg_indices = {k: 0.0 for k in index_keys}
                            if recent_indices:
                                for k in index_keys:
                                    avg_indices[k] = sum(d[k] for d in recent_indices) / len(recent_indices)
                                # Normalize so sum is 1.0
                                total = sum(avg_indices.values())
                                if total > 0:
                                    for k in index_keys:
                                        avg_indices[k] /= total

                            # --- Blend normalized averages with stored weights ---
                            for k in index_keys:
                                self.current_weightages[k] = (self.current_weightages[k] + avg_indices[k]) / 2.0

                            # Calculate weighted score for tiredness
                            break_duration = self.task_learner.calculate_break_duration(indices_dict, self.current_weightages, self.current_scaler)
                            self.root.after(0, lambda dur=break_duration, r=highest_index, 
                                d_idx=drowsiness_index, sl_idx=slouching_index,
                                att_idx=attention_index, y_idx=yawn_score: 
                                self.trigger_break(dur, r, d_idx, sl_idx, att_idx, y_idx))
                            self.last_break_time = current_time
                else:
                    self.high_index_start_time = None
            
            time.sleep(0.05)  # Smaller delay for faster response (0.05s = 20 checks per second)
    
    def update_display(self, drowsiness_idx: float, slouching_idx: float, attention_idx: float,
                      yawn_score_idx: float, debug_info: Optional[dict] = None):
        """Update all index displays and debug info."""
        # Debug: Print attention tracking info every 5 seconds
        if hasattr(self, '_last_attention_debug_time'):
            if time.time() - self._last_attention_debug_time > 5:
                if debug_info and 'raw_values' in debug_info:
                    print(f"\n=== Attention Debug ===")
                    print(f"Attention Index: {attention_idx:.3f}")
                    if 'attention_history_count' in debug_info['raw_values']:
                        print(f"History count: {debug_info['raw_values']['attention_history_count']}")
                    if 'attention_recent_vals' in debug_info['raw_values']:
                        print(f"Recent vals: {debug_info['raw_values']['attention_recent_vals']}")
                    if 'attention_gaze_deviation' in debug_info['raw_values']:
                        print(f"Current gaze deviation: {debug_info['raw_values']['attention_gaze_deviation']:.3f}")
                    if 'attention_iris_error' in debug_info['raw_values']:
                        print(f"Iris error: {debug_info['raw_values']['attention_iris_error']}")
                    if 'attention_no_history' in debug_info['raw_values']:
                        print("No attention history!")
                    print("=====================\n")
                self._last_attention_debug_time = time.time()
        else:
            self._last_attention_debug_time = time.time()
        
        # Calculate weighted tiredness for display
        indices_dict = {
            'drowsiness': drowsiness_idx,
            'slouching': slouching_idx,
            'attention': attention_idx,
            'yawn_score': yawn_score_idx
        }
        weighted_tiredness = self.task_learner.calculate_weighted_tiredness(indices_dict, self.current_weightages)
        self.weighted_tiredness_label.config(
            text=f"Weighted Tiredness: {weighted_tiredness:.2f}",
            foreground='red' if weighted_tiredness >= self.trigger_threshold else 'black'
        )
        # Note: insufficient data message is now set once during diagnostic capture, not here
        self.drowsiness_label.config(
            text=f"Drowsiness Index: {drowsiness_idx:.2f}",
            foreground='red' if drowsiness_idx >= 0.5 else 'black'
        )
        self.slouching_label.config(
            text=f"Slouching Index: {slouching_idx:.2f}",
            foreground='orange' if slouching_idx >= 0.5 else 'black'
        )
        self.attention_label.config(
            text=f"Attention Index: {attention_idx:.2f}",
            foreground='orange' if attention_idx >= 0.5 else 'black'
        )
        self.yawn_score_label.config(
            text=f"Yawn Score Index: {yawn_score_idx:.2f}",
            foreground='orange' if yawn_score_idx >= 0.5 else 'black'
        )
        # Removed UI updates for removed indices
        
        # Update debug display
        if debug_info:
            self.update_debug_display(debug_info)
    
    def update_debug_display(self, debug_info: dict):
        """Update the debug text widget with raw values."""
        self.debug_text.delete(1.0, tk.END)
        
        output = "=== RAW VALUES ===\n\n"
        
        # EAR values
        if 'ear_debug' in debug_info.get('raw_values', {}):
            ear_debug = debug_info['raw_values']['ear_debug']
            output += "EYE ASPECT RATIO (EAR):\n"
            output += f"  Left EAR:  {ear_debug.get('left_ear', 0):.4f}\n"
            output += f"  Right EAR: {ear_debug.get('right_ear', 0):.4f}\n"
            output += f"  Average:   {debug_info['raw_values'].get('ear_current', 0):.4f}\n"
            if 'left_debug' in ear_debug and 'horizontal' in ear_debug['left_debug']:
                output += f"  Left Eye - Vertical1: {ear_debug['left_debug'].get('vertical_1', 0):.6f}\n"
                output += f"  Left Eye - Vertical2: {ear_debug['left_debug'].get('vertical_2', 0):.6f}\n"
                output += f"  Left Eye - Horizontal: {ear_debug['left_debug'].get('horizontal', 0):.6f}\n"
            if 'right_debug' in ear_debug and 'horizontal' in ear_debug['right_debug']:
                output += f"  Right Eye - Vertical1: {ear_debug['right_debug'].get('vertical_1', 0):.6f}\n"
                output += f"  Right Eye - Vertical2: {ear_debug['right_debug'].get('vertical_2', 0):.6f}\n"
                output += f"  Right Eye - Horizontal: {ear_debug['right_debug'].get('horizontal', 0):.6f}\n"
            output += f"  Reference EAR: {debug_info['reference'].get('ear', 'N/A')}\n"
            output += f"  EAR Ratio: {debug_info['raw_values'].get('ear_ratio', 0):.4f}\n\n"
        
        # Shoulder angle
        if 'shoulder_angle' in debug_info.get('raw_values', {}):
            output += "SHOULDER ANGLE:\n"
            output += f"  Current:   {debug_info['raw_values']['shoulder_angle']:.2f}°\n"
            output += f"  Reference: {debug_info['reference'].get('shoulder_angle', 'N/A')}\n"
            output += f"  Difference: {debug_info['raw_values'].get('shoulder_angle_diff', 0):.2f}°\n\n"
        
        # Head pose
        if 'head_pose' in debug_info.get('raw_values', {}):
            hp = debug_info['raw_values']['head_pose']
            output += "HEAD POSE:\n"
            output += f"  Face Center: ({hp.get('center_x', 0):.3f}, {hp.get('center_y', 0):.3f})\n"
            output += f"  Center Offset: {hp.get('center_offset', 0):.4f}\n"
            output += f"  Rotation Angle: {hp.get('rotation_angle', 0):.2f}°\n"
            output += f"  Eye Horizontal Diff: {hp.get('eye_horizontal_diff', 0):.6f}\n\n"
        
        # Scores
        output += "=== SCORES ===\n\n"
        scores = debug_info.get('scores', {})
        if 'eye_score' in scores:
            output += f"Eye Score: {scores['eye_score']:.4f}\n"
        if 'slouch_score' in scores:
            output += f"Slouch Score: {scores['slouch_score']:.4f}\n"
        if 'drowsiness_index' in scores:
            output += f"Drowsiness Index: {scores['drowsiness_index']:.4f}\n\n"
        
        # Vision-derived scores (5-index system)
        if 'yawn_score' in scores:
            output += f"Yawn Score: {scores['yawn_score']:.3f}\n"

        # Input monitor metrics (if available from detector debug or live monitor)
        input_metrics = debug_info.get('input_metrics') if debug_info else None
        if input_metrics:
            output += "\nINPUT METRICS:\n"
            output += f"  Typing Speed (cpm): {input_metrics.get('typing_speed_cpm', 0):.1f}\n"
            output += f"  Typing Errors Rate: {input_metrics.get('typing_errors_rate', 0):.2f}\n"
            output += f"  Mouse Entropy: {input_metrics.get('mouse_entropy', 0):.3f}\n"
            output += f"  Idle Seconds: {input_metrics.get('idle_seconds', 0):.1f}\n"
        
        self.debug_text.insert(1.0, output)
    
    def get_index_warning_info(self, index_name: str) -> dict:
        """Get detailed warning information for a specific index."""
        warnings = {
            'drowsiness': {
                'title': '😴 Drowsiness Detected',
                'problem': 'Your eyes are showing significant closure, indicating drowsiness.',
                'immediate_fix': '• Look away from the screen\n• Blink deliberately several times\n• Take 5 deep breaths\n• Stand up and stretch',
                'long_term_risk': 'Continued work while drowsy can lead to:\n• Reduced productivity and increased errors\n• Eye strain and headaches\n• Increased accident risk\n• Chronic fatigue if sleep-deprived',
                'score': 'High drowsiness'
            },
            'slouching': {
                'title': '🪑 Poor Posture Detected',
                'problem': 'Your shoulders are significantly deviated from proper alignment.',
                'immediate_fix': '• Sit up straight with shoulders back\n• Adjust your chair height\n• Position screen at eye level\n• Use lumbar support',
                'long_term_risk': 'Prolonged poor posture can cause:\n• Chronic back and neck pain\n• Spinal misalignment and disc problems\n• Reduced lung capacity\n• Permanent postural changes',
                'score': 'Severe slouching'
            },
            'attention': {
                'title': '🎯 Attention Drift Detected',
                'problem': 'You\'re frequently looking away from your work area.',
                'immediate_fix': '• Refocus on your task\n• Remove distractions from view\n• Take a 2-minute mindfulness break\n• Set a smaller, achievable goal',
                'long_term_risk': 'Consistent attention problems can lead to:\n• Decreased work quality and productivity\n• Increased time to complete tasks\n• Higher stress from unfinished work\n• Difficulty maintaining focus over time',
                'score': 'High distraction'
            },
            'yawn_score': {
                'title': '🥱 Frequent Yawning Detected',
                'problem': 'You\'re yawning repeatedly, indicating significant fatigue.',
                'immediate_fix': '• Take a 5-10 minute break\n• Get some fresh air or cold water\n• Do light physical activity\n• Consider a power nap (10-20 min)',
                'long_term_risk': 'Ignoring fatigue signals can result in:\n• Accumulated sleep debt\n• Weakened immune system\n• Impaired cognitive function\n• Increased risk of burnout',
                'score': 'High fatigue'
            },
            # Removed warnings for head_nodding, eye_smoothness, blink_variance
        }
        return warnings.get(index_name, {
            'title': '⚠️ Tiredness Alert',
            'problem': 'Elevated tiredness indicator detected.',
            'immediate_fix': '• Take a short break\n• Rest and recharge',
            'long_term_risk': 'Continued strain may affect health and productivity.',
            'score': 'Elevated'
        })
    
    def show_index_warning(self, index_name: str, index_value: float):
        """Show detailed popup warning for an elevated index."""
        info = self.get_index_warning_info(index_name)
        
        message = f"{info['title']}\n"
        message += f"Current Level: {index_value:.2f} / 1.00 ({info['score']})\n\n"
        message += f"📊 WHAT'S HAPPENING:\n{info['problem']}\n\n"
        message += f"✅ IMMEDIATE ACTIONS:\n{info['immediate_fix']}\n\n"
        message += f"⚠️ LONG-TERM RISKS:\n{info['long_term_risk']}\n\n"
        message += "Note: This is an informational warning. Work timers trigger separately based on overall tiredness."
        
        messagebox.showwarning(info['title'], message)
    
    def show_reminder(self, reason: str):
        """Show reminder popup based on dominant index."""
        index_messages = {
            'drowsiness': "⚠️ Drowsiness Alert\n\nYou're showing signs of drowsiness. Consider taking a short break to rest your eyes and refresh.",
            'slouching': "⚠️ Posture Alert\n\nYou're slouching too much! Poor posture can lead to back problems in the long run. Please sit up straight.",
            'attention': "⚠️ Attention Alert\n\nYour attention seems to be drifting. Consider refocusing or taking a brief break.",
            'yawn_score': "⚠️ Fatigue Alert\n\nYou're yawning frequently, indicating fatigue. A short break might help you recharge."
        }
        
        message = index_messages.get(reason, "⚠️ Tiredness Alert\n\nYou're showing signs of tiredness. Consider taking a break.")
        messagebox.showwarning("Reminder", message)
        
        # Mark that last action was a reminder (next will be timer)
        self.last_action_was_timer = True
        self.last_break_time = time.time()
    
    def trigger_break(self, duration: int, reason: str = "drowsiness",
                     drowsiness_idx: float = 0.0, slouching_idx: float = 0.0,
                     attention_idx: float = 0.0, yawn_score_idx: float = 0.0):
        """Trigger a break overlay with smart exit logic."""
        # Show break message with info for highest raw value index
        info = self.get_index_warning_info(reason)
        message = f"Break needed! ({reason.capitalize()})\n\n"
        message += f"{info['title']}\n\n"
        message += f"📊 WHAT'S HAPPENING:\n{info['problem']}\n\n"
        message += f"✅ IMMEDIATE ACTIONS:\n{info['immediate_fix']}\n\n"
        message += f"⚠️ LONG-TERM RISKS:\n{info['long_term_risk']}\n\n"
        message += f"Break duration: {duration} seconds. Use this time to test the suggested actions!"
        messagebox.showinfo("Break Time", message)
        
        # Track break for learning
        break_start_time = time.time()
        self.breaks_triggered += 1
        
        # Create and start overlay (runs in main thread)
        # Pass detector, camera, and task learner for smart exit
        def start_overlay():
            overlay = BreakOverlay(
                self.root, 
                duration, 
                on_complete=lambda alert_before=False, drowsy_after=False, became_alert_at=None: 
                    self.on_break_complete(duration, drowsiness_idx, slouching_idx, 
                                          attention_idx, yawn_score_idx,
                                          alert_before, drowsy_after, became_alert_at),
                detector=self.detector,
                camera=self.camera,
                show_indices=True,
                task_learner=self.task_learner,
                weightages=self.current_weightages,
                tiredness_threshold=self.trigger_threshold
            )
            overlay.start()
        # Mark break active immediately to avoid race with monitor thread
        self.break_active = True
        try:
            print(f"[break] activated at {time.strftime('%H:%M:%S')} | reason={reason} | duration={duration}s")
        except Exception:
            pass
        self.root.after(0, start_overlay)
        
        # Mark that last action was a timer (next will be reminder)
        self.last_action_was_timer = False
    
    def on_break_complete(self, break_duration: int, drowsiness_idx: float,
                         slouching_idx: float, attention_idx: float,
                         yawn_score_idx: float,
                         alert_before: bool = False, drowsy_after: bool = False, became_alert_at: Optional[float] = None):
        """Callback when break completes."""
        # Break finished; allow monitoring to trigger again
        self.break_active = False
        try:
            print(f"[break] completed at {time.strftime('%H:%M:%S')} | actual_duration={break_duration}s | alert_before={alert_before} | drowsy_after={drowsy_after} | became_alert_at={became_alert_at}")
        except Exception:
            pass

        # Record break in database
        if self.current_session_id:
            self.task_db.record_break(
                self.current_session_id,
                break_duration,
                drowsiness_idx,
                slouching_idx,
                attention_idx,
                yawn_score_idx,
                alert_before,
                drowsy_after
            )
            # Store for session learning
            self.session_breaks.append({
                'drowsiness_index': drowsiness_idx,
                'slouching_index': slouching_idx,
                'attention_index': attention_idx,
                'yawn_score_index': yawn_score_idx,
                'alert_before': alert_before,
                'drowsy_after': drowsy_after,
                'break_duration': break_duration,
                'became_alert_at': became_alert_at  # Track when user became alert
            })
            
            self.total_break_time += break_duration
            
            # Update scaler based on user alertness and when they became alert
            new_scaler = self.task_learner.update_scaler(
                self.current_scaler,
                alert_before,
                drowsy_after,
                became_alert_at,
                break_duration
            )
            self.current_scaler = new_scaler

            # Update scaler in database if we have task
            if self.current_task_id:
                # Get current weightages from database
                subject_id = self.current_subject_id if self.current_subject_id else None
                weightages_data = self.task_db.get_task_weightages_for_subject(
                    self.current_task_id,
                    subject_id
                )
                if weightages_data:
                    # Update weightages with new scaler
                    self.task_db.update_task_weightages(
                        self.current_task_id,
                        weightages_data['drowsiness_weight'],
                        weightages_data['slouching_weight'],
                        weightages_data['attention_weight'],
                        weightages_data['yawn_score_weight'],
                        subject_id=subject_id,
                        scaler=new_scaler
                    )
        
        messagebox.showinfo("Break Complete", "Break finished! You can continue studying.")
    
    def end_session(self):
        """End current session and learn from it."""
        if not self.current_session_id:
            return
        
        # End session in database
        self.task_db.end_session(
            self.current_session_id,
            self.breaks_triggered,
            self.total_break_time
        )
        
        # Persist blended weights to database for current task/subject
        if self.current_task_id:
            indices_keys = ['drowsiness', 'slouching', 'attention', 'yawn_score']
            try:
                self.task_db.update_task_weightages(
                    self.current_task_id,
                    self.current_weightages['drowsiness'],
                    self.current_weightages['slouching'],
                    self.current_weightages['attention'],
                    self.current_weightages['yawn_score'],
                    subject_id=self.current_subject_id
                )
            except Exception:
                self.task_db.update_task_weightages(
                    self.current_task_id,
                    self.current_weightages['drowsiness'],
                    self.current_weightages['slouching'],
                    self.current_weightages['attention'],
                    self.current_weightages['yawn_score']
                )
                # If you want to update related prompts, fix and re-enable this block:
                # for related_id, related_name, similarity in related_tasks:
                #     rel_weights = self.task_db.get_task_weightages(related_id)
                #     if rel_weights:
                #         rel_vec = [rel_weights[f'{k}_weight'] for k in indices_keys]
                #         updated_vec = [max(0.05, min(0.50, rel + 0.5 * d)) for rel, d in zip(rel_vec, delta_vec)]
                #         total = sum(updated_vec)
                #         if total > 0:
                #             updated_vec = [v / total for v in updated_vec]
                #         self.task_db.update_task_weightages(
                #             related_id,
                #             updated_vec[0],
                #             updated_vec[1],
                #             updated_vec[2],
                #             updated_vec[3],
                #             updated_vec[4],
                #             updated_vec[5],
                #             updated_vec[6],
                #             updated_vec[7]
                #         )
                # print(f"Updated related prompt '{related_name}' weights to {updated_vec}")
                # Update UI
                if self.current_task:
                    self.task_status_label.config(
                        text=f"Task: {self.current_task} | Updated Weights: "
                             f"D={self.current_weightages['drowsiness']:.2f}, "
                             f"S={self.current_weightages['slouching']:.2f}, "
                             f"A={self.current_weightages['attention']:.2f}, "
                             f"Y={self.current_weightages['yawn_score']:.2f}",
                        foreground='blue'
                    )
        
        # Reset session tracking
        self.current_session_id = None
        self.session_breaks = []
        self.breaks_triggered = 0
        self.total_break_time = 0
    
    def on_closing(self):
        """Handle application closing."""
        self.stop_monitoring()  # This will call end_session()
        self.detector.cleanup()
        self.root.destroy()

def main():
    """Main entry point."""
    root = tk.Tk()
    app = StudySleepApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

