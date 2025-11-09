#!/usr/bin/env python3
"""Script to clear all data from the tasks database while preserving schema."""

import sqlite3
import os

DB_FILE = 'tasks.db'

def clear_database():
    """Clear all data from the database tables."""
    if not os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' not found.")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} tables in database.")
    
    # Clear all tables
    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f"DELETE FROM {table_name}")
            count = cursor.rowcount
            print(f"✓ Cleared {count} rows from table '{table_name}'")
        except Exception as e:
            print(f"✗ Error clearing table '{table_name}': {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Database cleared successfully!")
    print("Note: Schema and structure preserved. All data removed.")

if __name__ == "__main__":
    response = input("⚠️  This will DELETE ALL DATA from the database. Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        clear_database()
    else:
        print("Operation cancelled.")
