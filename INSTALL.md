# Installation Instructions

## Step 1: Install System Dependencies

Run these commands in your terminal (you'll need to enter your password):

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-tk
```

## Step 2: Verify pip Installation

After installation, verify pip is working:

```bash
pip3 --version
```

## Step 3: Install Python Packages

Navigate to the project directory and install the required packages:

```bash
cd /home/abhiramk/Documents/hack-princeton/work-sleep
pip3 install -r requirements.txt
```

## Step 4: Verify Installation

Run the test script to verify all packages are installed:

```bash
python3 test_imports.py
```

If all packages show as installed, you're ready to run the application!

## Step 5: Run the Application

```bash
python3 main.py
```

## Troubleshooting

### If pip3 command is not found after installation:
Try using `python3 -m pip` instead:
```bash
python3 -m pip install -r requirements.txt
```

### If you get permission errors:
You may need to use `--user` flag:
```bash
pip3 install --user -r requirements.txt
```

### If MediaPipe installation fails:
MediaPipe requires specific system libraries. On Ubuntu/Debian:
```bash
sudo apt-get install -y libopencv-dev python3-opencv
```

