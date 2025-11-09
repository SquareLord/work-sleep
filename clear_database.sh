#!/bin/bash

# Clear Database Script
# This script clears all data from the database while keeping the structure intact

DB_PATH="$(dirname "$0")/tasks.db"

echo "🗑️  Clearing database contents..."
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Error: Database file not found at $DB_PATH"
    exit 1
fi

# Run Python script to clear the database
python3 << 'EOF'
import sqlite3
import sys

try:
    # Connect to the database
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if not tables:
        print("⚠️  No tables found in database.")
        sys.exit(0)
    
    print("Clearing data from tables:")
    total_rows = 0
    for table in tables:
        table_name = table[0]
        if table_name != 'sqlite_sequence':  # Skip internal SQLite table
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            cursor.execute(f"DELETE FROM {table_name}")
            print(f"  ✓ Cleared {table_name} ({row_count} rows deleted)")
            total_rows += row_count
    
    # Reset auto-increment counters (if the table exists)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';")
    if cursor.fetchone():
        cursor.execute("DELETE FROM sqlite_sequence")
        print("  ✓ Reset auto-increment counters")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("")
    print(f"✅ Database cleared successfully! ({total_rows} total rows deleted)")
    print("   Database structure remains intact and ready for new data.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✨ You can now restart the application with fresh data!"
else
    echo ""
    echo "❌ Failed to clear database. Please check the error above."
    exit 1
fi
