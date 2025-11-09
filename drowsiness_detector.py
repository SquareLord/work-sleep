"""Drowsiness detection module using MediaPipe for pose and face detection."""
import cv2
import numpy as np
import mediapipe as mp
import time
from typing import Optional, Tuple, Dict

class DrowsinessDetector:
    def __init__(self):
        """Initialize MediaPipe models for pose and face detection."""
        # Use getattr to avoid attribute errors if mediapipe API changes
        self.mp_pose = getattr(mp.solutions, 'pose', None)
        self.mp_face = getattr(mp.solutions, 'face_mesh', None)
        self.mp_drawing = getattr(mp.solutions, 'drawing_utils', None)
        if self.mp_pose:
            self.pose = self.mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.pose = None
        if self.mp_face:
            self.face_mesh = self.mp_face.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.face_mesh = None
        
        # Reference values (will be set from diagnostic image)
        self.reference_shoulder_ratio = None  # Changed from angle to ratio
        self.reference_shoulder_angle = None  # For compatibility
        self.reference_eye_aspect_ratio = None
        self.reference_head_pose = None  # {'x': center_x, 'y': center_y, 'angle': angle}

        # Eye landmarks (MediaPipe Face Mesh) - using standard EAR landmarks
        # Left eye: outer corner (33), inner corner (133), top (159), bottom (145), mid-top (158), mid-bottom (153)
        self.LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        self.RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

        # Key points for EAR calculation (more reliable)
        # Left eye: outer(33), inner(133), top(159), bottom(145)
        self.LEFT_EYE_EAR_POINTS = [33, 133, 159, 145, 158, 153]  # outer, inner, top, bottom, mid-top, mid-bottom
        # Right eye: outer(362), inner(263), top(386), bottom(374)
        self.RIGHT_EYE_EAR_POINTS = [362, 263, 386, 374, 387, 373]  # outer, inner, top, bottom, mid-top, mid-bottom

        # Key face landmarks for head pose estimation
        self.NOSE_TIP = 4
        self.LEFT_EYE_CENTER = 33
        self.RIGHT_EYE_CENTER = 263
        self.CHIN = 152
        self.FOREHEAD = 10

        # State for temporal metrics
        self._ear_history = []  # list of (timestamp, ear)

        # Attention tracking: store recent head rotation angles to detect looking away
        self._attention_history = []  # list of (timestamp, attention_score)

        # NEW INDEX 1: Eye closure duration tracking
        self._eye_closure_events = []  # list of (timestamp, duration) for prolonged closures
        self._eyes_closed = False
        self._eye_close_start = None

        # NEW INDEX 2: Head nodding/dropping detection
        self._head_pitch_history = []  # list of (timestamp, pitch_angle)
        self._head_drop_events = []  # list of timestamps when head dropped

        # NEW INDEX 3: Eye tracking smoothness (gaze stability)
        self._gaze_position_history = []  # list of (timestamp, (x, y)) for gaze tracking

        # NEW INDEX 4: Blink rate variance
        self._blink_times = []  # list of timestamps when blinks occurred

        # NEW INDEX 5: Facial stillness duration
        self._prev_face_landmarks = None
        self._last_movement_time = time.time()
        self._stillness_periods = []  # list of (timestamp, duration) of stillness

        # Yawn detection: track actual yawn events
        self._yawn_events = []  # list of timestamps when yawns occurred
        self._mar_history = []  # list of (timestamp, mar) for detection
        self._is_yawning = False  # current yawn state
        self._yawn_start_time = None  # when current yawn started

        # Reference landmark storage (set during calibration)
        # These are populated by set_reference()
        self.reference_landmark_coords = None  # list of (x,y) for reference face landmarks
        self.reference_anchors = None
        self.reference_eye_landmarks_coords = None
        self.reference_descriptor = None
        self.reference_mouth_coords = None
        
    def calculate_eye_aspect_ratio(self, landmarks, ear_points) -> Tuple[float, Dict]:
        """
        Calculate Eye Aspect Ratio (EAR) for drowsiness detection using standard 6-point method.
        Returns EAR value and debug info.
        
        Args:
            landmarks: MediaPipe face landmarks
            ear_points: List of 6 landmark indices [outer, inner, top, bottom, mid-top, mid-bottom]
        """
        try:
            if len(ear_points) < 6:
                return 0.0, {'error': 'Need 6 points for EAR calculation'}
            
            # Extract the 6 key points. If we have reference landmark coordinates,
            # map the reference points to the closest current-frame landmark indices
            # to allow per-subject reference points to be used instead of hard-coded indices.
            def _coord_of_index(idx):
                return np.array([landmarks[idx].x, landmarks[idx].y])

            used_reference_mapping = False
            alignment_error = None

            # Try to use the per-subject reference mapping if reference anchors and eye coords are available
            if hasattr(self, 'reference_anchors') and self.reference_anchors is not None and hasattr(self, 'reference_eye_landmarks_coords') and self.reference_eye_landmarks_coords:
                try:
                    # Build current anchors from current landmarks (nose, left eye center, right eye center)
                    cur_anchors = np.array([
                        [landmarks[self.NOSE_TIP].x, landmarks[self.NOSE_TIP].y],
                        [landmarks[self.LEFT_EYE_CENTER].x, landmarks[self.LEFT_EYE_CENTER].y],
                        [landmarks[self.RIGHT_EYE_CENTER].x, landmarks[self.RIGHT_EYE_CENTER].y]
                    ], dtype=np.float64)

                    # Compute similarity transform from reference anchors -> current anchors
                    sim = self._compute_similarity_transform(self.reference_anchors, cur_anchors)
                    if sim is not None:
                        s, R, t = sim

                        # Apply transform to the reference eye landmark coords (choose left/right set based on ear_points)
                        side = 'left' if ear_points == self.LEFT_EYE_EAR_POINTS else 'right'
                        ref_eye_pts = self.reference_eye_landmarks_coords.get(side) or self.reference_eye_landmarks_coords.get('left') or self.reference_eye_landmarks_coords.get('right')
                        if ref_eye_pts and len(ref_eye_pts) >= 6:
                            transformed = self._apply_similarity(ref_eye_pts, s, R, t)
                            # transformed is list of (x,y); map into numpy arrays
                            outer = np.array(transformed[0])
                            inner = np.array(transformed[1])
                            top = np.array(transformed[2])
                            bottom = np.array(transformed[3])
                            mid_top = np.array(transformed[4])
                            mid_bottom = np.array(transformed[5])

                            # Compute alignment RMS between transformed anchor positions and current anchors
                            # Transform the reference anchors and compare
                            ref_anchors_transformed = self._apply_similarity(self.reference_anchors.tolist(), s, R, t)
                            ref_anchors_transformed = np.array(ref_anchors_transformed)
                            rms = np.sqrt(np.mean((ref_anchors_transformed - cur_anchors)**2))
                            alignment_error = float(rms)
                            # If alignment error small enough, accept mapping
                            if rms < 0.03:
                                used_reference_mapping = True
                            else:
                                # fallback to index-based below
                                used_reference_mapping = False
                    # else: sim None -> fall back
                except Exception:
                    used_reference_mapping = False

            if not used_reference_mapping:
                # No valid mapping or mapping rejected -> use indices directly
                outer = np.array([landmarks[ear_points[0]].x, landmarks[ear_points[0]].y])
                inner = np.array([landmarks[ear_points[1]].x, landmarks[ear_points[1]].y])
                top = np.array([landmarks[ear_points[2]].x, landmarks[ear_points[2]].y])
                bottom = np.array([landmarks[ear_points[3]].x, landmarks[ear_points[3]].y])
                mid_top = np.array([landmarks[ear_points[4]].x, landmarks[ear_points[4]].y])
                mid_bottom = np.array([landmarks[ear_points[5]].x, landmarks[ear_points[5]].y])
            else:
                # No reference coordinates stored — use indices directly
                outer = np.array([landmarks[ear_points[0]].x, landmarks[ear_points[0]].y])
                inner = np.array([landmarks[ear_points[1]].x, landmarks[ear_points[1]].y])
                top = np.array([landmarks[ear_points[2]].x, landmarks[ear_points[2]].y])
                bottom = np.array([landmarks[ear_points[3]].x, landmarks[ear_points[3]].y])
                mid_top = np.array([landmarks[ear_points[4]].x, landmarks[ear_points[4]].y])
                mid_bottom = np.array([landmarks[ear_points[5]].x, landmarks[ear_points[5]].y])
            
            # Calculate vertical distances (top to bottom)
            vertical_1 = np.linalg.norm(top - bottom)
            vertical_2 = np.linalg.norm(mid_top - mid_bottom)
            
            # Calculate horizontal distance (outer to inner corner)
            horizontal = np.linalg.norm(outer - inner)
            
            if horizontal == 0:
                return 0.0, {'error': 'Zero horizontal distance'}
            
            # Standard EAR formula: average of two vertical distances divided by horizontal
            ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
            
            debug_info = {
                'vertical_1': float(vertical_1),
                'vertical_2': float(vertical_2),
                'horizontal': float(horizontal),
                'ear': float(ear),
                'outer_point': [float(outer[0]), float(outer[1])],
                'inner_point': [float(inner[0]), float(inner[1])],
                'top_point': [float(top[0]), float(top[1])],
                'bottom_point': [float(bottom[0]), float(bottom[1])]
            }
            # add mapping metadata
            debug_info['used_reference_mapping'] = bool(used_reference_mapping)
            # alignment_error is float when available; use -1.0 sentinel when not
            debug_info['alignment_error'] = float(alignment_error) if alignment_error is not None else -1.0
            
            return float(ear), debug_info
        except Exception as e:
            return 0.0, {'error': str(e)}

    def calculate_mouth_aspect_ratio(self, landmarks) -> Tuple[float, Dict]:
        """
        Approximate Mouth Aspect Ratio (MAR) for yawn detection.
        Uses a small set of mouth-related landmarks if available. Returns (mar, debug).
        """
        try:
            # Use a few mouth landmarks if present (MediaPipe indices are approximate)
            # We'll try a few commonly available indices; if missing, return 0.
            idx_top = 13 if len(landmarks) > 13 else None
            idx_bottom = 14 if len(landmarks) > 14 else None
            idx_left = 61 if len(landmarks) > 61 else None
            idx_right = 291 if len(landmarks) > 291 else None

            # Try to use reference mapping if available
            used_reference_mapping = False
            alignment_error = None
            if hasattr(self, 'reference_anchors') and self.reference_anchors is not None and self.reference_mouth_coords:
                try:
                    cur_anchors = np.array([
                        [landmarks[self.NOSE_TIP].x, landmarks[self.NOSE_TIP].y],
                        [landmarks[self.LEFT_EYE_CENTER].x, landmarks[self.LEFT_EYE_CENTER].y],
                        [landmarks[self.RIGHT_EYE_CENTER].x, landmarks[self.RIGHT_EYE_CENTER].y]
                    ], dtype=np.float64)
                    sim = self._compute_similarity_transform(self.reference_anchors, cur_anchors)
                    if sim is not None:
                        s, R, t = sim
                        transformed = self._apply_similarity(self.reference_mouth_coords, s, R, t)
                        top = np.array(transformed[0])
                        bottom = np.array(transformed[1])
                        left = np.array(transformed[2])
                        right = np.array(transformed[3])

                        ref_anchors_transformed = self._apply_similarity(self.reference_anchors.tolist(), s, R, t)
                        ref_anchors_transformed = np.array(ref_anchors_transformed)
                        rms = np.sqrt(np.mean((ref_anchors_transformed - cur_anchors)**2))
                        alignment_error = float(rms)
                        if rms < 0.03:
                            used_reference_mapping = True
                except Exception:
                    used_reference_mapping = False

            # If mapping not used, fall back to index-based landmarks
            if not used_reference_mapping:
                if not idx_top or not idx_bottom or not idx_left or not idx_right:
                    return 0.0, {'error': 'Mouth landmarks not available'}
                top = np.array([landmarks[idx_top].x, landmarks[idx_top].y])
                bottom = np.array([landmarks[idx_bottom].x, landmarks[idx_bottom].y])
                left = np.array([landmarks[idx_left].x, landmarks[idx_left].y])
                right = np.array([landmarks[idx_right].x, landmarks[idx_right].y])

            # Ensure numeric numpy arrays
            top = np.array(top, dtype=np.float64)
            bottom = np.array(bottom, dtype=np.float64)
            left = np.array(left, dtype=np.float64)
            right = np.array(right, dtype=np.float64)

            vertical = float(np.linalg.norm(top - bottom))
            horizontal = float(np.linalg.norm(left - right))
            if horizontal == 0:
                return 0.0, {'error': 'Zero mouth width'}

            mar = vertical / horizontal
            debug = {'mar': float(mar), 'vertical': float(vertical), 'horizontal': float(horizontal)}
            debug['used_reference_mapping'] = bool(used_reference_mapping)
            # alignment_error is float when available; use -1.0 sentinel when not
            debug['alignment_error'] = float(alignment_error) if alignment_error is not None else -1.0
            return mar, debug
        except Exception as e:
            return 0.0, {'error': str(e)}
    
    def calculate_shoulder_angle(self, landmarks) -> Optional[float]:
        """Calculate shoulder angle to detect slouching."""
        try:
            # Get shoulder landmarks
            if self.mp_pose and hasattr(self.mp_pose, 'PoseLandmark'):
                left_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            else:
                left_shoulder = None
                right_shoulder = None
            
            # Calculate angle from horizontal
            if left_shoulder is not None and right_shoulder is not None:
                dx = right_shoulder.x - left_shoulder.x
                dy = right_shoulder.y - left_shoulder.y
            else:
                dx = 0.0
                dy = 0.0
            
            if dx == 0:
                return None
            
            angle = np.arctan2(abs(dy), abs(dx)) * 180 / np.pi
            return angle
        except:
            return None
    
    def calculate_head_pose(self, landmarks) -> Optional[Dict]:
        """
        Calculate head pose to detect if user is looking away from screen.
        Uses head rotation angles (yaw, pitch, roll) to determine attention.
        
        Returns:
            Dictionary with head rotation angles and attention indicators, or None
        """
        try:
            # Get key facial landmarks
            nose_tip = landmarks.landmark[self.NOSE_TIP]
            left_eye = landmarks.landmark[self.LEFT_EYE_CENTER]
            right_eye = landmarks.landmark[self.RIGHT_EYE_CENTER]
            chin = landmarks.landmark[self.CHIN]
            forehead = landmarks.landmark[self.FOREHEAD]
            
            # Calculate face center (average of key points)
            face_center_x = (nose_tip.x + left_eye.x + right_eye.x) / 3.0
            face_center_y = (nose_tip.y + left_eye.y + right_eye.y) / 3.0
            
            # Calculate YAW (left/right rotation) - looking left or right
            # When looking straight: eyes are roughly horizontal, nose centered
            # When looking left/right: eyes tilt and nose moves sideways
            eye_center_x = (left_eye.x + right_eye.x) / 2.0
            nose_to_eye_center_x = nose_tip.x - eye_center_x
            # Yaw angle: negative = looking left, positive = looking right
            # Range roughly -45 to +45 degrees
            yaw_angle = np.arctan2(nose_to_eye_center_x, 0.1) * 180 / np.pi
            yaw_angle = np.clip(yaw_angle, -45, 45)
            
            # Calculate PITCH (up/down rotation) - looking up or down
            # When looking straight: nose-chin vector is mostly vertical
            # When looking up: nose above normal, chin down
            # When looking down: nose down, chin closer
            nose_to_chin_y = chin.y - nose_tip.y
            nose_to_forehead_y = forehead.y - nose_tip.y
            # Pitch angle: negative = looking down, positive = looking up
            pitch_angle = np.arctan2(nose_to_forehead_y - nose_to_chin_y, abs(nose_to_chin_y)) * 180 / np.pi if abs(nose_to_chin_y) > 0 else 0
            pitch_angle = np.clip(pitch_angle, -30, 30)
            
            # Calculate ROLL (head tilt) - head tilted to shoulder
            # When upright: eyes are horizontal
            # When tilted: eyes are diagonal
            eye_dy = left_eye.y - right_eye.y
            eye_dx = left_eye.x - right_eye.x
            roll_angle = np.arctan2(eye_dy, eye_dx) * 180 / np.pi if abs(eye_dx) > 0 else 0
            # Normalize to -30 to +30 degrees
            roll_angle = np.clip(roll_angle, -30, 30)
            
            # Calculate ATTENTION SCORE based on head angles
            # When looking directly at screen: all angles near 0
            # When looking away: angles deviate significantly
            
            # Yaw contribution (most important for detecting looking away)
            yaw_deviation = abs(yaw_angle) / 45.0  # Normalize to 0-1
            
            # Pitch contribution (looking up/down)
            pitch_deviation = abs(pitch_angle) / 30.0  # Normalize to 0-1
            
            # Roll contribution (head tilt) - less important for attention
            roll_deviation = abs(roll_angle) / 30.0  # Normalize to 0-1
            
            # Combined attention score: 0 = looking directly at screen, 1 = looking away
            # Weight yaw more heavily (60%), pitch (30%), roll (10%)
            attention_deviation = (yaw_deviation * 0.6 + pitch_deviation * 0.3 + roll_deviation * 0.1)
            attention_deviation = min(1.0, attention_deviation)
            
            # Calculate how far face center is from screen center (0.5, 0.5)
            center_offset_x = abs(face_center_x - 0.5)
            center_offset_y = abs(face_center_y - 0.5)
            total_offset = np.sqrt(center_offset_x**2 + center_offset_y**2)
            
            return {
                'center_x': face_center_x,
                'center_y': face_center_y,
                'center_offset': total_offset,
                'yaw_angle': float(yaw_angle),  # Left/right rotation
                'pitch_angle': float(pitch_angle),  # Up/down rotation
                'roll_angle': float(roll_angle),  # Head tilt
                'attention_deviation': float(attention_deviation),  # 0=focused, 1=looking away
                'yaw_deviation': float(yaw_deviation),
                'pitch_deviation': float(pitch_deviation),
                'roll_deviation': float(roll_deviation)
            }
        except Exception as e:
            return None
    
    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """
        Analyze a frame for drowsiness indicators.
        
        Returns:
            Dictionary with detection results
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = {
            'shoulder_angle': None,
            'eye_aspect_ratio': None,
            'head_pose': None,
            'pose_detected': False,
            'face_detected': False
        }
        
        # Pose detection
        pose_results = self.pose.process(rgb_frame) if self.pose else None
        face_results = self.face_mesh.process(rgb_frame) if self.face_mesh else None
        if pose_results and pose_results.pose_landmarks:
            results['pose_detected'] = True
            angle = self.calculate_shoulder_angle(pose_results.pose_landmarks)
            results['shoulder_angle'] = angle
        
        # Face detection
        if face_results and face_results.multi_face_landmarks:
            results['face_detected'] = True
            landmarks = face_results.multi_face_landmarks[0]
            
            # Provide raw landmarks for callers (useful for reference capture)
            results['landmarks'] = landmarks.landmark

            # Calculate EAR for both eyes (with debug info) using optimized points
            left_ear, left_debug = self.calculate_eye_aspect_ratio(landmarks.landmark, self.LEFT_EYE_EAR_POINTS)
            right_ear, right_debug = self.calculate_eye_aspect_ratio(landmarks.landmark, self.RIGHT_EYE_EAR_POINTS)
            results['eye_aspect_ratio'] = (left_ear + right_ear) / 2.0
            results['ear_debug'] = {
                'left_ear': left_ear,
                'right_ear': right_ear,
                'left_debug': left_debug,
                'right_debug': right_debug
            }
            
            # Calculate head pose for distraction detection
            head_pose = self.calculate_head_pose(landmarks.landmark)
            results['head_pose'] = head_pose

            # Temporal metrics updates
            ts = cv2.getTickCount() / cv2.getTickFrequency()

            # EAR history
            if results['eye_aspect_ratio'] is not None:
                self._ear_history.append((ts, results['eye_aspect_ratio']))
                # keep last 30s
                self._ear_history = [(t, v) for t, v in self._ear_history if ts - t < 30.0]

            # Attention tracking: use eye gaze direction (MediaPipe iris landmarks)
            # Left iris: 468-472, Right iris: 473-477
            try:
                left_iris_indices = [468, 469, 470, 471, 472]
                right_iris_indices = [473, 474, 475, 476, 477]
                left_eye_outer = landmarks.landmark[33]
                left_eye_inner = landmarks.landmark[133]
                left_eye_top = landmarks.landmark[159]
                left_eye_bottom = landmarks.landmark[145]
                right_eye_outer = landmarks.landmark[362]
                right_eye_inner = landmarks.landmark[263]
                right_eye_top = landmarks.landmark[386]
                right_eye_bottom = landmarks.landmark[374]
                
                # Get iris center for each eye
                left_iris_center_x = np.mean([landmarks.landmark[i].x for i in left_iris_indices])
                left_iris_center_y = np.mean([landmarks.landmark[i].y for i in left_iris_indices])
                right_iris_center_x = np.mean([landmarks.landmark[i].x for i in right_iris_indices])
                right_iris_center_y = np.mean([landmarks.landmark[i].y for i in right_iris_indices])
                
                # Horizontal gaze tracking (left/right)
                left_eye_width = left_eye_inner.x - left_eye_outer.x
                left_gaze_pos_h = (left_iris_center_x - left_eye_outer.x) / (left_eye_width + 1e-6)
                right_eye_width = right_eye_inner.x - right_eye_outer.x
                right_gaze_pos_h = (right_iris_center_x - right_eye_outer.x) / (right_eye_width + 1e-6)
                
                # Vertical gaze tracking (up/down)
                left_eye_height = abs(left_eye_bottom.y - left_eye_top.y)
                left_gaze_pos_v = (left_iris_center_y - left_eye_top.y) / (left_eye_height + 1e-6)
                right_eye_height = abs(right_eye_bottom.y - right_eye_top.y)
                right_gaze_pos_v = (right_iris_center_y - right_eye_top.y) / (right_eye_height + 1e-6)
                
                # Calculate horizontal deviation (amplified for more sensitivity)
                # Center is at 0.5, so deviation from center should be amplified
                h_deviation = (abs(left_gaze_pos_h - 0.5) + abs(right_gaze_pos_h - 0.5)) * 2.0
                
                # Calculate vertical deviation (amplified)
                v_deviation = (abs(left_gaze_pos_v - 0.5) + abs(right_gaze_pos_v - 0.5)) * 2.0
                
                # Combine horizontal and vertical with more weight on horizontal
                gaze_deviation = (h_deviation * 0.7 + v_deviation * 0.3)
                gaze_deviation = min(1.0, gaze_deviation)  # Clamp to [0,1]
                
                self._attention_history.append((ts, gaze_deviation))
                # Shorter time window (15s instead of 30s) for faster response
                self._attention_history = [(t, v) for t, v in self._attention_history if ts - t < 15.0]
                results['attention_gaze_deviation'] = gaze_deviation
                results['attention_left_gaze'] = left_gaze_pos_h
                results['attention_right_gaze'] = right_gaze_pos_h
            except Exception as e:
                # Fallback to head pose if iris landmarks not available
                results['attention_iris_error'] = str(e)
                if head_pose is not None and 'attention_deviation' in head_pose:
                    self._attention_history.append((ts, head_pose['attention_deviation']))
                    self._attention_history = [(t, v) for t, v in self._attention_history if ts - t < 15.0]

            # MAR (mouth) history for yawn detection
            try:
                mar, mar_debug = self.calculate_mouth_aspect_ratio(landmarks.landmark)
                if mar and mar > 0:
                    self._mar_history.append((ts, mar))
                    self._mar_history = [(t, m) for t, m in self._mar_history if ts - t < 30.0]
                    results['mar'] = mar
                    results['mar_debug'] = mar_debug
            except Exception:
                pass

            # NEW: Track head pitch for head nodding detection
            try:
                if results['head_pose']:
                    pitch = results['head_pose']['pitch']
                    self._head_pitch_history.append((ts, pitch))
                    self._head_pitch_history = [(t, p) for t, p in self._head_pitch_history if ts - t < 10.0]
            except Exception:
                pass

            # NEW: Track gaze position for eye smoothness (use eye center as proxy)
            try:
                # Calculate average eye center position as gaze proxy
                left_eye_indices = [33, 133, 160, 159, 158, 157]  # Left eye landmarks
                right_eye_indices = [362, 263, 387, 386, 385, 384]  # Right eye landmarks
                
                left_center_x = np.mean([landmarks.landmark[i].x for i in left_eye_indices])
                left_center_y = np.mean([landmarks.landmark[i].y for i in left_eye_indices])
                right_center_x = np.mean([landmarks.landmark[i].x for i in right_eye_indices])
                right_center_y = np.mean([landmarks.landmark[i].y for i in right_eye_indices])
                
                gaze_x = (left_center_x + right_center_x) / 2.0
                gaze_y = (left_center_y + right_center_y) / 2.0
                
                self._gaze_position_history.append((ts, (gaze_x, gaze_y)))
                self._gaze_position_history = [(t, p) for t, p in self._gaze_position_history if ts - t < 10.0]
            except Exception:
                pass

            # NEW: Track blink events for blink variance
            # Detect blinks by checking if EAR drops below threshold
            try:
                if hasattr(self, '_last_ear'):
                    current_ear = results.get('ear', 1.0)
                    # Blink detected: transition from open (>0.25) to closed (<0.2)
                    if self._last_ear > 0.25 and current_ear < 0.2:
                        self._blink_times.append(ts)
                        self._blink_times = [t for t in self._blink_times if ts - t < 60.0]
                    self._last_ear = current_ear
                else:
                    self._last_ear = results.get('ear', 1.0)
            except Exception:
                pass

            # NEW: Track facial movement for stillness detection
            try:
                if self._prev_face_landmarks is not None:
                    # Compute average displacement across key facial landmarks
                    disp = 0.0
                    count = min(len(landmarks.landmark), len(self._prev_face_landmarks))
                    for i in range(count):
                        a = np.array([landmarks.landmark[i].x, landmarks.landmark[i].y])
                        b = np.array([self._prev_face_landmarks[i].x, self._prev_face_landmarks[i].y])
                        disp += np.linalg.norm(a - b)
                    avg_disp = disp / max(1, count)
                    
                    # If significant movement detected, update last movement time
                    if avg_disp > 0.001:
                        self._last_movement_time = ts
                    
                self._prev_face_landmarks = landmarks.landmark
            except Exception:
                self._prev_face_landmarks = landmarks.landmark
        
        return results
    
    def set_reference(self, frame: np.ndarray):
        """Set reference values from a diagnostic image."""
        results = self.analyze_frame(frame)
        
        # Calculate reference shoulder ratio (angle-invariant)
        if results['pose_detected']:
            try:
                pose_results = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) if self.pose else None
                if pose_results and pose_results.pose_landmarks:
                    landmarks = pose_results.pose_landmarks.landmark
                    if self.mp_pose and hasattr(self.mp_pose, 'PoseLandmark'):
                        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                        nose = landmarks[self.mp_pose.PoseLandmark.NOSE] if hasattr(self.mp_pose.PoseLandmark, 'NOSE') else None
                        
                        if left_shoulder and right_shoulder and nose:
                            left_shoulder_pos = np.array([left_shoulder.x, left_shoulder.y])
                            right_shoulder_pos = np.array([right_shoulder.x, right_shoulder.y])
                            nose_pos = np.array([nose.x, nose.y])
                            
                            shoulder_midpoint = (left_shoulder_pos + right_shoulder_pos) / 2
                            shoulder_width = np.linalg.norm(right_shoulder_pos - left_shoulder_pos)
                            vertical_distance = abs(nose_pos[1] - shoulder_midpoint[1])
                            
                            if shoulder_width > 0:
                                self.reference_shoulder_ratio = vertical_distance / shoulder_width
                            else:
                                self.reference_shoulder_ratio = None
                        else:
                            self.reference_shoulder_ratio = None
                    else:
                        self.reference_shoulder_ratio = None
            except Exception as e:
                print(f"Error calculating reference shoulder ratio: {e}")
                self.reference_shoulder_ratio = None
        
        if results['eye_aspect_ratio'] is not None:
            self.reference_eye_aspect_ratio = results['eye_aspect_ratio']
        
        if results['head_pose'] is not None:
            self.reference_head_pose = results['head_pose']
        # Store reference landmarks if available for per-subject mapping
        try:
            lm = results.get('landmarks')
            if lm:
                # store list of (x,y)
                self.reference_landmark_coords = [(float(p.x), float(p.y)) for p in lm]
                # anchors for similarity mapping (nose, left eye center, right eye center)
                try:
                    self.reference_anchors = np.array([
                        self.reference_landmark_coords[self.NOSE_TIP],
                        self.reference_landmark_coords[self.LEFT_EYE_CENTER],
                        self.reference_landmark_coords[self.RIGHT_EYE_CENTER]
                    ], dtype=np.float64)
                except Exception:
                    self.reference_anchors = None

                # store the reference EAR point coords for left/right if possible
                try:
                    left_eye_coords = [self.reference_landmark_coords[i] for i in self.LEFT_EYE_EAR_POINTS]
                    right_eye_coords = [self.reference_landmark_coords[i] for i in self.RIGHT_EYE_EAR_POINTS]
                    self.reference_eye_landmarks_coords = {'left': left_eye_coords, 'right': right_eye_coords}
                except Exception:
                    self.reference_eye_landmarks_coords = None

                # build small descriptor for identification
                try:
                    self.reference_descriptor = self._build_descriptor_from_landmarks(self.reference_landmark_coords)
                except Exception:
                    self.reference_descriptor = None
        except Exception:
            pass
    def get_reference_vector(self) -> Dict:
        """Return a compact reference vector/dict summarizing the captured reference values.

        Useful for identifying users and storing per-subject baselines.
        """
        return {
            'shoulder_ratio': self.reference_shoulder_ratio,
            'eye_aspect_ratio': self.reference_eye_aspect_ratio,
            'head_pose': self.reference_head_pose
        }

    def get_reference_fingerprint(self) -> str:
        """Return a short fingerprint string computed from the reference vector.

        This is a coarse identifier for matching similar reference captures.
        """
        import json, hashlib
        vec = self.get_reference_vector()
        # Convert to sorted JSON for stable hashing
        s = json.dumps(vec, sort_keys=True)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]

    def _build_descriptor_from_landmarks(self, landmark_coords, indices=None):
        """Build a normalized landmark descriptor vector from selected indices.

        Normalizes by inter-eye distance to be scale-invariant.
        """
        try:
            if indices is None:
                indices = [self.NOSE_TIP, self.LEFT_EYE_CENTER, self.RIGHT_EYE_CENTER, self.CHIN, 61, 291]
            coords = np.array([landmark_coords[i] for i in indices], dtype=np.float64)
            mean = coords.mean(axis=0)
            coords_centered = coords - mean
            eye_left = np.array(landmark_coords[self.LEFT_EYE_CENTER])
            eye_right = np.array(landmark_coords[self.RIGHT_EYE_CENTER])
            iod = np.linalg.norm(eye_left - eye_right)
            if iod <= 1e-6:
                iod = 1.0
            norm = coords_centered.flatten() / iod
            return norm.tolist()
        except Exception:
            return None

    def _compute_similarity_transform(self, src_pts, dst_pts):
        """Compute 2D similarity transform (scale, rotation, translation) mapping src_pts -> dst_pts.

        Returns (s, R, t) where R is 2x2 matrix and t vector.
        """
        src = np.array(src_pts, dtype=np.float64)
        dst = np.array(dst_pts, dtype=np.float64)
        if src.shape[0] < 2 or dst.shape[0] < 2:
            return None
        src_mean = src.mean(axis=0)
        dst_mean = dst.mean(axis=0)
        src_centered = src - src_mean
        dst_centered = dst - dst_mean
        A = src_centered.T.dot(dst_centered)
        U, S, Vt = np.linalg.svd(A)
        R = Vt.T.dot(U.T)
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T.dot(U.T)
        var_src = (src_centered**2).sum()
        if var_src <= 1e-9:
            s = 1.0
        else:
            s = (S.sum()) / var_src
        t = dst_mean - s * R.dot(src_mean)
        return s, R, t

    def _apply_similarity(self, pts, s, R, t):
        p = np.array(pts, dtype=np.float64)
        transformed = (s * (R.dot(p.T)).T) + t
        return transformed.tolist()

    def _find_nearest_landmark_index(self, landmarks, point):
        best_i = 0
        best_d = float('inf')
        px = np.array(point)
        for i in range(len(landmarks)):
            xy = np.array([landmarks[i].x, landmarks[i].y])
            d = np.linalg.norm(xy - px)
            if d < best_d:
                best_d = d
                best_i = i
        return best_i
    
    def calculate_drowsiness_index(self, frame: np.ndarray) -> Tuple[float, float, float, float, Dict]:
        """
        Calculate core 4 indices: drowsiness, slouching, attention, yawn.

        Removed indices: head_nodding, eye_smoothness, blink_variance (simplification).
        Returns:
            Tuple of (drowsiness_index, slouching_index, attention_index, yawn_score, debug_info)
        """
        if self.reference_shoulder_ratio is None or self.reference_eye_aspect_ratio is None:
            return (0.0, 0.0, 0.0, 0.0, {'error': 'No reference set'})  # No reference set yet
        
        results = self.analyze_frame(frame)
        
        debug_info = {
            'raw_values': {},
            'scores': {},
            'reference': {}
        }
        
        drowsiness_scores = []
        slouching_score = 0.0

        # ---- Additional indices computed from temporal/vision features ----
        
        # Yawn detection: count actual yawn events (discrete mouth openings)
        # 1.0 = definitely tired (frequent yawning)
        yawn_score = 0.0
        current_time = time.time()
        
        if self._mar_history:
            # Get latest MAR value
            latest_mar = self._mar_history[-1][1] if self._mar_history else 0.0
            
            # Detect yawn start (mouth opens wide)
            if not self._is_yawning and latest_mar > 0.6:
                self._is_yawning = True
                self._yawn_start_time = current_time
            
            # Detect yawn end (mouth closes after being open)
            elif self._is_yawning and latest_mar < 0.4:
                # Yawn ended - record it if it lasted long enough (0.5-3 seconds)
                if self._yawn_start_time and 0.5 <= (current_time - self._yawn_start_time) <= 3.0:
                    self._yawn_events.append(current_time)
                    print(f"Yawn detected! Total yawns in last 60s: {len([t for t in self._yawn_events if current_time - t < 60])}")
                self._is_yawning = False
                self._yawn_start_time = None
            
            # Clean old yawn events (keep last 60 seconds)
            self._yawn_events = [t for t in self._yawn_events if current_time - t < 60]
            
            # Calculate yawn score based on yawn frequency
            # Recalibrated: 0 yawns = 0.0, 1 yawn = 0.35, 2 yawns = 0.65, 3+ yawns = 1.0 (definitely tired)
            yawn_count = len(self._yawn_events)
            yawn_score = min(1.0, yawn_count / 3.0)

        # Attention score: based on gaze direction (iris tracking)
        # 1.0 = definitely distracted (consistently looking away)
        # Recalibrated to be more sensitive with faster response
        attention_score = 0.0
        if self._attention_history:
            # Use recent values with more weight on latest readings for faster response
            vals = [v for t, v in self._attention_history]
            
            # Weight recent values more heavily (exponential moving average approach)
            # This makes the index more responsive to current attention state
            if len(vals) > 5:
                # Recent 5 values get 70% weight, older values get 30% weight
                recent_vals = vals[-5:]
                older_vals = vals[:-5]
                attention_score = float(0.7 * np.mean(recent_vals) + 0.3 * np.mean(older_vals))
            else:
                attention_score = float(np.mean(vals))
            
            # Apply slight amplification to make changes more noticeable
            attention_score = min(1.0, attention_score * 1.2)
            
            debug_info['raw_values']['attention_history_count'] = len(self._attention_history)
            debug_info['raw_values']['attention_recent_vals'] = vals[-5:] if len(vals) >= 5 else vals
        else:
            debug_info['raw_values']['attention_no_history'] = True

        # ===== NEW INDEX 1: Eye Closure Duration =====
        # Dynamic measure combining CURRENT eye closure + recent closure history
        # 1.0 = definitely tired (eyes barely open OR frequent prolonged closures)
        eye_closure_score = 0.0
        if self._ear_history:
            latest_ear = self._ear_history[-1][1] if self._ear_history else 1.0
            
            # PART 1: Current eye openness (dynamic, updates every frame)
            # Normal awake EAR ~0.25-0.35, sleepy ~0.15-0.20, closed <0.15
            # Map current EAR to tiredness: fully open (0.40+) = 0.0, barely open (0.25) ~ 1.0, closed (<0.15) = 1.0
            if latest_ear < 0.40:
                current_closure_score = max(0.0, (0.40 - latest_ear) / 0.15)  # 0.40->0.25 maps to 0.0->1.0
                current_closure_score = min(1.0, current_closure_score)
            else:
                current_closure_score = 0.0
            
            # PART 2: Track prolonged closure events (microsleeps)
            # Detect eye closure (EAR < 0.18 = eyes mostly/fully closed)
            if not self._eyes_closed and latest_ear < 0.18:
                self._eyes_closed = True
                self._eye_close_start = current_time
            
            # Detect eyes opening after being closed
            elif self._eyes_closed and latest_ear >= 0.22:
                if self._eye_close_start:
                    closure_duration = current_time - self._eye_close_start
                    # Record prolonged closures (>0.4s = not a normal blink)
                    if closure_duration >= 0.4:
                        self._eye_closure_events.append((current_time, closure_duration))
                        print(f"Prolonged eye closure: {closure_duration:.2f}s")
                self._eyes_closed = False
                self._eye_close_start = None
            
            # Clean old events (keep last 60 seconds)
            self._eye_closure_events = [(t, d) for t, d in self._eye_closure_events if current_time - t < 60]
            
            # PART 3: Calculate event-based score (recent closure history)
            # 1 closure (0.4-1s) = +0.3, 1 microsleep (1-2s) = +0.6, 2+ events = 1.0
            event_score = 0.0
            if self._eye_closure_events:
                # Weight recent events more heavily
                for event_time, duration in self._eye_closure_events:
                    age = current_time - event_time
                    recency_weight = max(0.3, 1.0 - (age / 60.0))  # Newer events weighted more
                    severity = min(1.0, duration / 1.5)  # 1.5s closure = full severity
                    event_score += severity * recency_weight * 0.4  # Each event adds up to 0.4
                event_score = min(1.0, event_score)
            
            # Combine current state (70%) + event history (30%)
            # This makes it dynamic while still tracking recent problematic closures
            eye_closure_score = min(1.0, current_closure_score * 0.7 + event_score * 0.3)
        
        # Add retained scores to debug_info
        debug_info['scores']['yawn_score'] = yawn_score
        debug_info['scores']['attention'] = attention_score
        
        # Slouching score - angle-invariant ratio method
        # 1.0 = definitely poor posture (severe slouching)
        slouching_score = 0.0
        if results.get('pose_detected'):
            try:
                # Re-process frame to get pose landmarks
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pose_results = self.pose.process(rgb_frame) if self.pose else None
                
                if pose_results and pose_results.pose_landmarks and self.mp_pose and hasattr(self.mp_pose, 'PoseLandmark'):
                    landmarks = pose_results.pose_landmarks.landmark
                    left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                    right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    nose = landmarks[self.mp_pose.PoseLandmark.NOSE] if hasattr(self.mp_pose.PoseLandmark, 'NOSE') else None
                    
                    if left_shoulder and right_shoulder and nose:
                        # Get positions as numpy arrays
                        left_shoulder_pos = np.array([left_shoulder.x, left_shoulder.y])
                        right_shoulder_pos = np.array([right_shoulder.x, right_shoulder.y])
                        nose_pos = np.array([nose.x, nose.y])
                        
                        # Calculate shoulder midpoint
                        shoulder_midpoint = (left_shoulder_pos + right_shoulder_pos) / 2
                        
                        # Calculate shoulder width (horizontal distance)
                        shoulder_width = np.linalg.norm(right_shoulder_pos - left_shoulder_pos)
                        
                        # Calculate vertical distance from shoulders to nose
                        vertical_distance = abs(nose_pos[1] - shoulder_midpoint[1])
                        
                        # Calculate current ratio (angle-invariant)
                        if shoulder_width > 0:
                            current_ratio = vertical_distance / shoulder_width
                        else:
                            current_ratio = 0.0
                        
                        # Compare to reference ratio
                        if self.reference_shoulder_ratio is not None and self.reference_shoulder_ratio > 0:
                            # Slouching means the ratio decreases (chin gets closer to shoulders)
                            ratio_change = (self.reference_shoulder_ratio - current_ratio) / self.reference_shoulder_ratio
                            
                            # Map to 0-1 score: 0% change = 0.0, 30% decrease = 1.0
                            slouching_score = max(0.0, min(1.0, ratio_change / 0.30))
                        else:
                            slouching_score = 0.0
                        
                        debug_info['raw_values']['shoulder_width'] = float(shoulder_width)
                        debug_info['raw_values']['vertical_distance'] = float(vertical_distance)
                        debug_info['raw_values']['current_ratio'] = float(current_ratio)
                        debug_info['raw_values']['reference_ratio'] = float(self.reference_shoulder_ratio) if self.reference_shoulder_ratio else None
                        debug_info['scores']['slouch_score'] = float(slouching_score)
            except Exception as e:
                slouching_score = 0.0
                debug_info['raw_values']['slouch_error'] = str(e)
        
        # Eye closure score (EAR reduction) - for drowsiness index
        # 1.0 = definitely drowsy (eyes barely open)
        # Recalibrated to be more realistic
        if results['eye_aspect_ratio'] is not None:
            if self.reference_eye_aspect_ratio > 0:
                ear_ratio = results['eye_aspect_ratio'] / self.reference_eye_aspect_ratio
                # Recalibrated thresholds:
                # 100% of reference = 0.0 (wide awake)
                # 80% of reference = 0.3 (getting tired)
                # 60% of reference = 0.7 (very drowsy)
                # 50% of reference = 1.0 (definitely drowsy / microsleeping)
                if ear_ratio < 1.0:
                    eye_score = max(0.0, min(1.0, (1.0 - ear_ratio) / 0.5))
                else:
                    eye_score = 0.0
                drowsiness_scores.append(eye_score)
                debug_info['raw_values']['ear_current'] = results['eye_aspect_ratio']
                debug_info['raw_values']['ear_ratio'] = ear_ratio
                debug_info['scores']['eye_score'] = eye_score
                debug_info['reference']['ear'] = self.reference_eye_aspect_ratio
                if 'ear_debug' in results:
                    debug_info['raw_values']['ear_debug'] = results['ear_debug']
        
        # Calculate drowsiness index (now excludes slouching)
        if not drowsiness_scores:
            drowsiness_index = 0.0
        else:
            drowsiness_index = sum(drowsiness_scores) / len(drowsiness_scores)
            drowsiness_index = min(1.0, max(0.0, drowsiness_index))
        
        debug_info['scores']['drowsiness_index'] = drowsiness_index
        debug_info['scores']['slouching_index'] = slouching_score
        debug_info['scores']['attention_index'] = attention_score
        debug_info['scores']['yawn_index'] = yawn_score
    # Removed head_nodding_index, eye_smoothness_index, blink_variance_index from simplified system
        
        # Copy attention tracking data from results to debug_info
        if 'attention_gaze_deviation' in results:
            debug_info['raw_values']['attention_gaze_deviation'] = results['attention_gaze_deviation']
        if 'attention_left_gaze' in results:
            debug_info['raw_values']['attention_left_gaze'] = results['attention_left_gaze']
        if 'attention_right_gaze' in results:
            debug_info['raw_values']['attention_right_gaze'] = results['attention_right_gaze']
        if 'attention_iris_error' in results:
            debug_info['raw_values']['attention_iris_error'] = results['attention_iris_error']
        
        # Return only the 4 core indices now
        return (drowsiness_index, slouching_score, attention_score, yawn_score, debug_info)

    def cleanup(self):
        """Clean up MediaPipe resources."""
        if self.pose:
            self.pose.close()
        if self.face_mesh:
            self.face_mesh.close()

