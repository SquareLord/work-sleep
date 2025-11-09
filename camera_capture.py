"""Camera capture module for taking periodic images."""
import cv2
import time
from typing import Optional, Callable

class CameraCapture:
    def __init__(self, capture_interval: float = 3.0):
        """
        Initialize camera capture.
        
        Args:
            capture_interval: Time in seconds between captures
        """
        self.capture_interval = capture_interval
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_capture_time = 0
        self.is_running = False
        
    def start(self) -> bool:
        """Start the camera."""
        # If camera is already open, release it first
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            return False
        self.is_running = True
        self.last_capture_time = time.time()
        return True
    
    def stop(self):
        """Stop the camera."""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def capture_frame(self) -> Optional[tuple]:
        """
        Capture a frame if enough time has passed.
        
        Returns:
            (frame, timestamp) if captured, None otherwise
        """
        if not self.is_running or not self.cap:
            return None
        
        current_time = time.time()
        if current_time - self.last_capture_time >= self.capture_interval:
            ret, frame = self.cap.read()
            if ret:
                self.last_capture_time = current_time
                return (frame, current_time)
        return None
    
    def get_current_frame(self) -> Optional[tuple]:
        """Get current frame without waiting for interval."""
        if not self.is_running or not self.cap:
            return None
        ret, frame = self.cap.read()
        if ret:
            return (frame, time.time())
        return None

