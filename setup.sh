#!/bin/bash
# Setup script for Study Sleep application

echo "Setting up Study Sleep application..."

# Check Python version
python3 --version || { echo "Python 3 is required but not found"; exit 1; }

# Try to install pip if not available
if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found. Attempting to install..."
    # Try different methods based on system
    if command -v apt-get &> /dev/null; then
        echo "Please run: sudo apt-get install python3-pip python3-tk"
    elif command -v yum &> /dev/null; then
        echo "Please run: sudo yum install python3-pip python3-tkinter"
    elif command -v pacman &> /dev/null; then
        echo "Please run: sudo pacman -S python-pip tk"
    else
        echo "Please install pip3 and tkinter for your system"
    fi
    exit 1
fi

# Install required packages
echo "Installing required Python packages..."
pip3 install -r requirements.txt

# Check if installation was successful
python3 test_imports.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Setup complete! You can now run the application with:"
    echo "  python3 main.py"
else
    echo ""
    echo "✗ Some packages failed to install. Please check the errors above."
    exit 1
fi

