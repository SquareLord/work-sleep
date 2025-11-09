#!/usr/bin/env python3
"""Installation checker and guide script for Study Sleep application."""
import subprocess
import sys
import os

def run_command(cmd, check=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def check_pip3():
    """Check if pip3 is installed."""
    success, stdout, stderr = run_command("pip3 --version")
    if success:
        return True, stdout
    # Try python3 -m pip
    success, stdout, stderr = run_command("python3 -m pip --version")
    if success:
        return True, stdout
    return False, None

def check_tkinter():
    """Check if tkinter is available."""
    try:
        import tkinter
        return True, "tkinter is available"
    except ImportError:
        return False, "tkinter is not installed"

def check_python_packages():
    """Check which Python packages are installed."""
    packages = {
        'cv2': 'opencv-python',
        'mediapipe': 'mediapipe',
        'numpy': 'numpy',
        'pynput': 'pynput',
        'tkinter': 'tkinter (system package)'
    }
    
    results = {}
    for module, package_name in packages.items():
        try:
            if module == 'cv2':
                import cv2
                results[package_name] = True
            elif module == 'mediapipe':
                import mediapipe
                results[package_name] = True
            elif module == 'numpy':
                import numpy
                results[package_name] = True
            elif module == 'pynput':
                import pynput
                results[package_name] = True
            elif module == 'tkinter':
                import tkinter
                results[package_name] = True
        except ImportError:
            results[package_name] = False
    
    return results

def print_status(title, status, details=None):
    """Print a status line with formatting."""
    symbol = "✓" if status else "✗"
    color_start = "\033[92m" if status else "\033[91m"
    color_end = "\033[0m"
    print(f"{color_start}{symbol}{color_end} {title}")
    if details:
        print(f"   {details}")

def main():
    print("=" * 60)
    print("Study Sleep - Installation Checker")
    print("=" * 60)
    print()
    
    # Check Python
    print("Checking Python installation...")
    success, version, _ = run_command("python3 --version")
    if success:
        print_status("Python 3", True, version)
    else:
        print_status("Python 3", False, "Python 3 is required but not found!")
        sys.exit(1)
    print()
    
    # Check pip3
    print("Checking pip3 installation...")
    pip_available, pip_info = check_pip3()
    if pip_available:
        print_status("pip3", True, pip_info)
        pip_command = "pip3" if run_command("pip3 --version")[0] else "python3 -m pip"
    else:
        print_status("pip3", False, "pip3 is not installed")
        print()
        print("To install pip3, run:")
        print("  sudo apt-get update")
        print("  sudo apt-get install -y python3-pip")
        print()
        pip_command = None
    print()
    
    # Check tkinter
    print("Checking tkinter...")
    tk_available, tk_info = check_tkinter()
    print_status("tkinter", tk_available, tk_info)
    if not tk_available:
        print()
        print("To install tkinter, run:")
        print("  sudo apt-get install -y python3-tk")
        print()
    print()
    
    # Check Python packages
    print("Checking Python packages...")
    package_results = check_python_packages()
    all_installed = True
    for package, installed in package_results.items():
        print_status(package, installed)
        if not installed:
            all_installed = False
    print()
    
    # Summary and recommendations
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    if not pip_available:
        print("\n❌ pip3 is not installed. Please install it first:")
        print("   sudo apt-get update")
        print("   sudo apt-get install -y python3-pip python3-tk")
        sys.exit(1)
    
    if not tk_available:
        print("\n❌ tkinter is not installed. Please install it:")
        print("   sudo apt-get install -y python3-tk")
        sys.exit(1)
    
    if all_installed:
        print("\n✅ All packages are installed! You can run the application:")
        print("   python3 main.py")
        sys.exit(0)
    else:
        print("\n⚠️  Some packages are missing. Installing now...")
        print()
        
        # Try to install packages
        requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
        if os.path.exists(requirements_file):
            print(f"Installing packages from {requirements_file}...")
            install_cmd = f"{pip_command} install -r {requirements_file}"
            print(f"Running: {install_cmd}")
            print()
            
            success, stdout, stderr = run_command(install_cmd)
            if success:
                print("✅ Installation successful!")
                print()
                print("Verifying installation...")
                package_results = check_python_packages()
                all_installed = True
                for package, installed in package_results.items():
                    if not installed:
                        all_installed = False
                        print(f"   ✗ {package} still missing")
                
                if all_installed:
                    print("\n✅ All packages are now installed! You can run:")
                    print("   python3 main.py")
                else:
                    print("\n⚠️  Some packages failed to install. Please check the errors above.")
                    print("You may need to install them manually:")
                    print(f"   {pip_command} install -r requirements.txt")
            else:
                print("❌ Installation failed!")
                print(f"Error: {stderr}")
                print()
                print("Try installing manually:")
                print(f"   {pip_command} install -r requirements.txt")
                print()
                print("Or with user flag if you get permission errors:")
                print(f"   {pip_command} install --user -r requirements.txt")
        else:
            print(f"❌ requirements.txt not found at {requirements_file}")
            sys.exit(1)

if __name__ == "__main__":
    main()

