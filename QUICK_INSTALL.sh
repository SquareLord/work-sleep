#!/bin/bash
# Quick installation script for Study Sleep

echo "=========================================="
echo "Study Sleep - Quick Installation"
echo "=========================================="
echo ""

# Step 1: Install pip3 and tkinter
echo "Step 1: Installing pip3 and tkinter..."
echo "You will need to enter your password for sudo commands."
echo ""
sudo apt-get update
sudo apt-get install -y python3-pip python3-tk

if [ $? -ne 0 ]; then
    echo "❌ Failed to install pip3 and tkinter"
    exit 1
fi

echo ""
echo "✓ pip3 and tkinter installed!"
echo ""

# Step 2: Install Python packages
echo "Step 2: Installing Python packages..."
echo "This may take a few minutes..."
echo ""

cd "$(dirname "$0")"

# Try with --user flag first (handles externally-managed-environment error)
echo "Installing packages to user directory..."
if command -v pip3 &> /dev/null; then
    pip3 install --user -r requirements.txt
elif python3 -m pip --version &> /dev/null; then
    python3 -m pip install --user -r requirements.txt
else
    echo "❌ pip3 is still not available after installation"
    echo "Please try: python3 -m ensurepip --upgrade"
    exit 1
fi

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  Installation with --user failed. Trying with --break-system-packages..."
    pip3 install --break-system-packages -r requirements.txt 2>/dev/null || \
    python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || \
    {
        echo "❌ Installation failed. Please try creating a virtual environment:"
        echo "   python3 -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        exit 1
    }
fi

echo ""
echo "Step 3: Verifying installation..."
python3 test_imports.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Installation complete!"
    echo "=========================================="
    echo ""
    echo "You can now run the application with:"
    echo "  python3 main.py"
else
    echo ""
    echo "⚠️  Some packages may not be installed correctly."
    echo "Please check the errors above."
fi

