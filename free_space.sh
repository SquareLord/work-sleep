#!/bin/bash
# Script to help free up disk space

echo "Checking disk space..."
df -h /home

echo ""
echo "Cleaning up pip cache..."
rm -rf ~/.cache/pip/* 2>/dev/null
echo "✓ Pip cache cleaned"

echo ""
echo "Checking for other large files/directories..."
echo "Top 10 largest directories in home:"
du -h ~ 2>/dev/null | sort -rh | head -10

echo ""
echo "You may want to:"
echo "1. Remove old Python virtual environments"
echo "2. Clean package manager cache: sudo apt-get clean"
echo "3. Remove old logs: sudo journalctl --vacuum-time=7d"
echo "4. Check for large files: find ~ -type f -size +100M"



