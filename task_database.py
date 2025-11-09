"""Database system for storing tasks and learned weightages."""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

class TaskDatabase:
    def __init__(self, db_file: str = "tasks.db"):
        """
        Initialize task database.
        
        Args:
            db_file: Path to SQLite database file
        """
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Task sessions table (tracks each study session)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                subject_id INTEGER,
                session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_end TIMESTAMP,
                breaks_triggered INTEGER DEFAULT 0,
                total_break_time INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        # Break events table (tracks each break)
        # Tracks 4 indices: drowsiness, slouching, attention, yawn_score
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS break_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                break_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                break_duration INTEGER NOT NULL,
                drowsiness_index REAL NOT NULL,
                slouching_index REAL NOT NULL,
                attention_index REAL NOT NULL,
                yawn_score_index REAL NOT NULL,
                user_alert_before_timer BOOLEAN DEFAULT 0,
                user_drowsy_after_timer BOOLEAN DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES task_sessions(id)
            )
        ''')
        
        # Task weightages table (learned weights for each task)
        # Tracks 4 indices: drowsiness, slouching, attention, yawn_score
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_weightages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                subject_id INTEGER,
                drowsiness_weight REAL DEFAULT 0.25,
                slouching_weight REAL DEFAULT 0.25,
                attention_weight REAL DEFAULT 0.25,
                yawn_score_weight REAL DEFAULT 0.25,
                scaler REAL DEFAULT 300.0,
                total_sessions INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id),
                UNIQUE (task_id, subject_id)
            )
        ''')

        # Subjects table to store per-person reference vectors and optional name
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                fingerprint TEXT UNIQUE,
                reference_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
        # Run migrations for existing databases
        self._migrate_database(conn)
        
        conn.close()
    
    def _migrate_database(self, conn):
        """Migrate existing database schema to latest version."""
        cursor = conn.cursor()
        
        # Check if task_weightages has subject_id column
        cursor.execute("PRAGMA table_info(task_weightages)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Migration 1: Add subject_id column if missing
        if 'subject_id' not in columns:
            try:
                cursor.execute('ALTER TABLE task_weightages ADD COLUMN subject_id INTEGER')
                print("Migration: Added subject_id column to task_weightages")
            except sqlite3.OperationalError:
                pass  # Column already exists or other issue
        
        # Migration 2: Add new index columns to task_weightages if missing
        new_columns = [
            ('gaze_fixation_weight', 'REAL DEFAULT 0.15'),
            ('yawn_score_weight', 'REAL DEFAULT 0.15'),
            ('blink_rate_weight', 'REAL DEFAULT 0.10'),
            ('blink_duration_weight', 'REAL DEFAULT 0.10'),
            ('expressiveness_weight', 'REAL DEFAULT 0.10')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f'ALTER TABLE task_weightages ADD COLUMN {col_name} {col_type}')
                    print(f"Migration: Added {col_name} column to task_weightages")
                except sqlite3.OperationalError:
                    pass
        
        # Migration 3: Check if break_events has new index columns
        cursor.execute("PRAGMA table_info(break_events)")
        break_columns = [row[1] for row in cursor.fetchall()]
        
        new_break_columns = [
            ('gaze_fixation_index', 'REAL NOT NULL DEFAULT 0.0'),
            ('yawn_score_index', 'REAL NOT NULL DEFAULT 0.0'),
            ('blink_rate_index', 'REAL NOT NULL DEFAULT 0.0'),
            ('blink_duration_index', 'REAL NOT NULL DEFAULT 0.0'),
            ('expressiveness_index', 'REAL NOT NULL DEFAULT 0.0')
        ]
        
        for col_name, col_type in new_break_columns:
            if col_name not in break_columns:
                try:
                    cursor.execute(f'ALTER TABLE break_events ADD COLUMN {col_name} {col_type}')
                    print(f"Migration: Added {col_name} column to break_events")
                except sqlite3.OperationalError:
                    pass
        
        # Migration 4: Rename distraction to slouching (add slouching columns, copy data if exists)
        # Refresh column lists
        cursor.execute("PRAGMA table_info(task_weightages)")
        columns = [row[1] for row in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(break_events)")
        break_columns = [row[1] for row in cursor.fetchall()]
        
        if 'slouching_weight' not in columns and 'distraction_weight' in columns:
            try:
                # Add slouching_weight column
                cursor.execute('ALTER TABLE task_weightages ADD COLUMN slouching_weight REAL DEFAULT 0.20')
                # Copy distraction data to slouching
                cursor.execute('UPDATE task_weightages SET slouching_weight = distraction_weight')
                print("Migration: Renamed distraction_weight to slouching_weight in task_weightages")
            except sqlite3.OperationalError:
                pass
        
        if 'slouching_index' not in break_columns and 'distraction_index' in break_columns:
            try:
                # Add slouching_index column
                cursor.execute('ALTER TABLE break_events ADD COLUMN slouching_index REAL NOT NULL DEFAULT 0.0')
                # Copy distraction data to slouching
                cursor.execute('UPDATE break_events SET slouching_index = distraction_index')
                print("Migration: Renamed distraction_index to slouching_index in break_events")
            except sqlite3.OperationalError:
                pass
        
        # Migration 5: Remove old attention/distraction columns if they exist
        if 'attention_weight' in columns:
            # SQLite doesn't support DROP COLUMN before 3.35.0
            # For now, we'll just leave it and ignore it
            print("Note: Old attention_weight column exists but will be ignored")
        
        if 'attention_index' in break_columns:
            print("Note: Old attention_index column exists but will be ignored")
        
        if 'distraction_weight' in columns:
            print("Note: Old distraction_weight column exists but will be ignored (use slouching_weight)")
        
        if 'distraction_index' in break_columns:
            print("Note: Old distraction_index column exists but will be ignored (use slouching_index)")
        
        # Migration 6: Remove blink columns and rename gaze_fixation to attention (7 -> 5 indices)
        # Refresh column lists
        cursor.execute("PRAGMA table_info(task_weightages)")
        columns = [row[1] for row in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(break_events)")
        break_columns = [row[1] for row in cursor.fetchall()]
        
        # Add attention_weight if missing, copy from gaze_fixation_weight if available
        if 'attention_weight' not in columns:
            try:
                cursor.execute('ALTER TABLE task_weightages ADD COLUMN attention_weight REAL DEFAULT 0.20')
                if 'gaze_fixation_weight' in columns:
                    cursor.execute('UPDATE task_weightages SET attention_weight = gaze_fixation_weight')
                    print("Migration: Renamed gaze_fixation_weight to attention_weight in task_weightages")
                else:
                    print("Migration: Added attention_weight column to task_weightages")
            except sqlite3.OperationalError:
                pass
        
        # Add attention_index to break_events if missing
        if 'attention_index' not in break_columns:
            try:
                cursor.execute('ALTER TABLE break_events ADD COLUMN attention_index REAL NOT NULL DEFAULT 0.0')
                if 'gaze_fixation_index' in break_columns:
                    cursor.execute('UPDATE break_events SET attention_index = gaze_fixation_index')
                    print("Migration: Renamed gaze_fixation_index to attention_index in break_events")
                else:
                    print("Migration: Added attention_index column to break_events")
            except sqlite3.OperationalError:
                pass
        
        # Note deprecated blink columns
        if 'blink_rate_weight' in columns:
            print("Note: Old blink_rate_weight column exists but will be ignored (removed from system)")
        if 'blink_duration_weight' in columns:
            print("Note: Old blink_duration_weight column exists but will be ignored (removed from system)")
        if 'blink_rate_index' in break_columns:
            print("Note: Old blink_rate_index column exists but will be ignored (removed from system)")
        if 'blink_duration_index' in break_columns:
            print("Note: Old blink_duration_index column exists but will be ignored (removed from system)")
        if 'gaze_fixation_weight' in columns:
            print("Note: Old gaze_fixation_weight column exists but will be ignored (use attention_weight)")
        if 'gaze_fixation_index' in break_columns:
            print("Note: Old gaze_fixation_index column exists but will be ignored (use attention_index)")
        
        # Migration 7 (deprecated): previously added head_nodding, eye_smoothness, blink_variance.
        # No longer applicable in simplified 4-index system.
        
        # Note: expressiveness_weight/index columns remain for backward compatibility but unused
        if 'expressiveness_weight' in columns:
            print("Note: Old expressiveness_weight column exists but will be ignored (replaced by new indices)")
        if 'expressiveness_index' in break_columns:
            print("Note: Old expressiveness_index column exists but will be ignored (replaced by new indices)")
        
        # Migration 8: Add timer_coefficient for adaptive timer duration
        cursor.execute("PRAGMA table_info(task_weightages)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'timer_coefficient' not in columns:
            try:
                cursor.execute('ALTER TABLE task_weightages ADD COLUMN timer_coefficient REAL DEFAULT 300.0')
                print("Migration: Added timer_coefficient column to task_weightages")
            except sqlite3.OperationalError:
                pass

        # Migration 9: Rename timer_coefficient to scaler and update semantics
        # SQLite doesn't support RENAME COLUMN before 3.25, so we check if we need the rename
        if 'timer_coefficient' in columns and 'scaler' not in columns:
            try:
                # Create new scaler column with default 300.0
                cursor.execute('ALTER TABLE task_weightages ADD COLUMN scaler REAL DEFAULT 300.0')
                # Copy values from timer_coefficient (converting multiplier to scaler)
                # Old coefficient was multiplier (0.5-2.0 × base_duration)
                # New scaler is direct (scaler × weighted_score)
                # To preserve behavior: new_scaler = old_coeff × 180 (assuming avg base was 180s)
                cursor.execute('UPDATE task_weightages SET scaler = timer_coefficient * 180.0 WHERE timer_coefficient IS NOT NULL')
                print("Migration: Added scaler column and migrated data from timer_coefficient")
                print("Note: timer_coefficient column will remain for backward compatibility but is deprecated")
            except sqlite3.OperationalError as e:
                print(f"Migration warning: {e}")

        # If only scaler exists, we're on new schema
        if 'scaler' in columns:
            print("Using new scaler-based timer duration formula")
        
        conn.commit()
    
    def get_or_create_task(self, task_name: str) -> int:
        """Get task ID or create new task if it doesn't exist."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Try to get existing task
        cursor.execute('SELECT id FROM tasks WHERE task_name = ?', (task_name,))
        result = cursor.fetchone()
        
        if result:
            task_id = result[0]
        else:
            # Create new task
            cursor.execute('INSERT INTO tasks (task_name) VALUES (?)', (task_name,))
            task_id = cursor.lastrowid
            
            # Initialize with equal weightages for 4 indices (sum to 1.0)
            cursor.execute('''
                INSERT INTO task_weightages (task_id, subject_id, drowsiness_weight, slouching_weight, 
                                            attention_weight, yawn_score_weight)
                VALUES (?, NULL, 0.25, 0.25, 0.25, 0.25)
            ''', (task_id,))
        # commit and return task id
        conn.commit()
        conn.close()
        if task_id is None:
            raise RuntimeError('Failed to create task')
        return int(task_id)
    
    def start_session(self, task_id: int) -> int:
        """Start a new study session for a task."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO task_sessions (task_id, session_start)
            VALUES (?, CURRENT_TIMESTAMP)
        ''', (task_id,))

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        if session_id is None:
            raise RuntimeError('Failed to start session')
        return int(session_id)

    def start_session_with_subject(self, task_id: int, subject_id: int) -> int:
        """Start a session linked to a subject."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO task_sessions (task_id, subject_id, session_start)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (task_id, subject_id))

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        if session_id is None:
            raise RuntimeError('Failed to start session with subject')
        return int(session_id)

    def get_or_create_subject(self, fingerprint: str, reference_json: Optional[str] = None, name: Optional[str] = None) -> int:
        """Get subject id by fingerprint or create a new subject entry."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM subjects WHERE fingerprint = ?', (fingerprint,))
        row = cursor.fetchone()
        if row:
            sid = row[0]
            # Optionally update reference_json if provided
            if reference_json:
                cursor.execute('UPDATE subjects SET reference_json = ? WHERE id = ?', (reference_json, sid))
        else:
            cursor.execute('INSERT INTO subjects (name, fingerprint, reference_json) VALUES (?, ?, ?)',
                           (name, fingerprint, reference_json))
            sid = cursor.lastrowid

        conn.commit()
        conn.close()
        if sid is None:
            raise RuntimeError('Failed to create/get subject')
        return int(sid)
    
    def end_session(self, session_id: int, breaks_triggered: int, total_break_time: int):
        """End a study session."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE task_sessions
            SET session_end = CURRENT_TIMESTAMP,
                breaks_triggered = ?,
                total_break_time = ?
            WHERE id = ?
        ''', (breaks_triggered, total_break_time, session_id))
        
        conn.commit()
        conn.close()
    
    def record_break(self, session_id: int, break_duration: int, 
                     drowsiness_index: float, slouching_index: float,
                     attention_index: float, yawn_score_index: float,
                     user_alert_before: bool = False,
                     user_drowsy_after: bool = False):
        """Record a break event with core 4 indices."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO break_events 
            (session_id, break_duration, drowsiness_index, slouching_index,
             attention_index, yawn_score_index,
             user_alert_before_timer, user_drowsy_after_timer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, break_duration, drowsiness_index, slouching_index,
              attention_index, yawn_score_index,
              1 if user_alert_before else 0, 1 if user_drowsy_after else 0))
        
        conn.commit()
        conn.close()
    
    def get_task_weightages(self, task_id: int) -> Optional[Dict]:
        """Get current weightages for a task (4 indices).

        If a subject-specific weightage exists, return that when subject_id provided.
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT drowsiness_weight, slouching_weight, attention_weight, 
                   yawn_score_weight, total_sessions
            FROM task_weightages
            WHERE task_id = ? AND subject_id IS NULL
        ''', (task_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'drowsiness_weight': result[0],
                'slouching_weight': result[1],
                'attention_weight': result[2],
                'yawn_score_weight': result[3],
                'total_sessions': result[4]
            }
        return None

    def get_task_weightages_for_subject(self, task_id: int, subject_id: Optional[int]) -> Optional[Dict]:
        """Get weightages specifically for a task+subject (4 indices + scaler). Falls back to generic task weightages if none."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if subject_id is not None:
            cursor.execute('''
                SELECT drowsiness_weight, slouching_weight, attention_weight,
                       yawn_score_weight, scaler, total_sessions
                FROM task_weightages
                WHERE task_id = ? AND subject_id = ?
            ''', (task_id, subject_id))
        else:
            cursor.execute('''
                SELECT drowsiness_weight, slouching_weight, attention_weight,
                       yawn_score_weight, scaler, total_sessions
                FROM task_weightages
                WHERE task_id = ? AND subject_id IS NULL
            ''', (task_id,))
        
        row = cursor.fetchone()
        if row:
            conn.close()
            return {
                'drowsiness_weight': row[0],
                'slouching_weight': row[1],
                'attention_weight': row[2],
                'yawn_score_weight': row[3],
                'scaler': row[4] if len(row) > 4 and row[4] is not None else 300.0,
                'total_sessions': row[5] if len(row) > 5 else 0
            }
        conn.close()
        # Fallback to generic
        return self.get_task_weightages(task_id)
    
    def update_task_weightages(self, task_id: int, drowsiness_weight: float,
                               slouching_weight: float, attention_weight: float,
                               yawn_score_weight: float,
                               subject_id: Optional[int] = None, scaler: Optional[float] = None):
        """Update weightages for a task with 4 indices and optional scaler."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Normalize weights to sum to 1.0
        total = (drowsiness_weight + slouching_weight + attention_weight + yawn_score_weight)
        if total > 0:
            drowsiness_weight /= total
            slouching_weight /= total
            attention_weight /= total
            yawn_score_weight /= total
        
        # Upsert for (task_id, subject_id)
        cursor.execute('''
            SELECT id FROM task_weightages WHERE task_id = ? AND (
                (subject_id IS NULL AND ? IS NULL) OR (subject_id = ?)
            )
        ''', (task_id, subject_id, subject_id))
        row = cursor.fetchone()
        if row:
            if scaler is not None:
                cursor.execute('''
                    UPDATE task_weightages
                    SET drowsiness_weight = ?,
                        slouching_weight = ?,
                        attention_weight = ?,
                        yawn_score_weight = ?,
                        scaler = ?,
                        total_sessions = total_sessions + 1,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (drowsiness_weight, slouching_weight, attention_weight,
                      yawn_score_weight, scaler, row[0]))
            else:
                cursor.execute('''
                    UPDATE task_weightages
                    SET drowsiness_weight = ?,
                        slouching_weight = ?,
                        attention_weight = ?,
                        yawn_score_weight = ?,
                        total_sessions = total_sessions + 1,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (drowsiness_weight, slouching_weight, attention_weight,
                      yawn_score_weight, row[0]))
        else:
            cursor.execute('''
                INSERT INTO task_weightages (task_id, subject_id, drowsiness_weight, slouching_weight,
                                            attention_weight, yawn_score_weight, total_sessions)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (task_id, subject_id, drowsiness_weight, slouching_weight,
                  attention_weight, yawn_score_weight))
        
        conn.commit()
        conn.close()

    def get_similar_tasks(self, task_name: str, limit: int = 5) -> List[Tuple[int, str, float]]:
        """
        Find similar tasks using AI-powered semantic similarity.
        
        This uses sentence transformers to understand semantic meaning, so it can
        match tasks like "math homework" with "calculus assignment" or "reading book"
        with "studying textbook" even without exact word matches.
        
        Falls back to keyword matching if AI model is unavailable.
        """
        from semantic_matcher import get_semantic_matcher
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Get all other tasks with their weightages
        cursor.execute('''
            SELECT t.id, t.task_name, tw.total_sessions
            FROM tasks t
            LEFT JOIN task_weightages tw ON t.id = tw.task_id AND tw.subject_id IS NULL
            WHERE t.task_name != ?
        ''', (task_name,))
        all_tasks = cursor.fetchall()
        conn.close()
        
        if not all_tasks:
            return []
        
        # Filter to only tasks with training history (at least 1 session)
        tasks_with_history = [(task_id, name) for task_id, name, sessions in all_tasks 
                              if sessions and sessions > 0]
        
        if not tasks_with_history:
            return []
        
        # Use semantic matcher to find similar tasks
        matcher = get_semantic_matcher()
        similar_tasks = matcher.find_most_similar(
            query=task_name,
            candidates=tasks_with_history,
            threshold=0.3,  # 30% similarity threshold (lower than keyword-only)
            limit=limit
        )
        
        return similar_tasks

    def get_subject_by_name(self, name: str) -> Optional[Dict]:
        """Return subject row by name or None."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, fingerprint, reference_json FROM subjects WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'name': row[1], 'fingerprint': row[2], 'reference_json': row[3]}
        return None

    def get_subject_reference(self, subject_id: int) -> Optional[str]:
        """Return stored reference_json for a subject_id."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT reference_json FROM subjects WHERE id = ?', (subject_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return None
    
    def get_task_break_history(self, task_id: int, limit: int = 20) -> List[Dict]:
        """Get break history for a task to analyze patterns with 4 indices."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT be.drowsiness_index, be.slouching_index, be.attention_index,
                   be.yawn_score_index,
                   be.user_alert_before_timer, be.user_drowsy_after_timer,
                   be.break_duration
            FROM break_events be
            JOIN task_sessions ts ON be.session_id = ts.id
            WHERE ts.task_id = ?
            ORDER BY be.break_start DESC
            LIMIT ?
        ''', (task_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'drowsiness_index': r[0],
                'slouching_index': r[1],
                'attention_index': r[2],
                'yawn_score_index': r[3],
                'alert_before': bool(r[4]),
                'drowsy_after': bool(r[5]),
                'break_duration': r[6]
            }
            for r in results
        ]


