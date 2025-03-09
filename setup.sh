#!/bin/bash
# Setup script for Superwhisper

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Superwhisper Setup ===${NC}"

# Check for Xcode Command Line Tools
if ! xcode-select -p &> /dev/null; then
    echo -e "${BLUE}Installing Xcode Command Line Tools...${NC}"
    xcode-select --install
    echo "Please wait for Xcode Command Line Tools to finish installing, then run this script again."
    exit 0
fi

# Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    echo -e "${BLUE}Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# Install system dependencies
echo -e "${BLUE}Installing system dependencies...${NC}"
for pkg in "python@3.11" "ffmpeg" "portaudio"; do
    if ! brew list $pkg &>/dev/null; then
        echo "Installing $pkg..."
        brew install $pkg
    else
        echo "$pkg is already installed"
    fi
done

# Find Python 3.11
echo -e "${BLUE}Locating Python 3.11...${NC}"
PYTHON_PATHS=(
    "/opt/homebrew/bin/python3.11"
    "$(brew --prefix)/opt/python@3.11/bin/python3.11"
    "$(brew --prefix)/bin/python3.11"
)

PYTHON_PATH=""
for path in "${PYTHON_PATHS[@]}"; do
    if [ -f "$path" ]; then
        PYTHON_PATH="$path"
        echo -e "${GREEN}Found Python 3.11 at: $PYTHON_PATH${NC}"
        break
    fi
done

if [ -z "$PYTHON_PATH" ]; then
    echo -e "${RED}Failed to find Python 3.11. Please ensure it's installed correctly.${NC}"
    exit 1
fi

# Clean up any existing virtual environment
if [ -d "venv" ]; then
    echo -e "${BLUE}Removing existing virtual environment...${NC}"
    rm -rf venv
fi

# Clean up any existing builds
if [ -d "dist" ] || [ -d "build" ]; then
    echo -e "${BLUE}Cleaning up previous builds...${NC}"
    rm -rf dist build
fi

# Set up Python environment
echo -e "${BLUE}Setting up Python environment...${NC}"
$PYTHON_PATH -m venv venv
source venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ "$PYTHON_VERSION" != "3.11" ]]; then
    echo -e "${RED}Wrong Python version in virtual environment: $PYTHON_VERSION (expected 3.11)${NC}"
    exit 1
fi

# Install dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
python3 -m pip install --upgrade pip wheel setuptools
python3 -m pip install -r requirements.txt

# Ensure PyInstaller is up to date
echo -e "${BLUE}Updating PyInstaller...${NC}"
python3 -m pip install --upgrade pyinstaller

# Make scripts executable
chmod +x superwhisper.py
chmod +x run.sh

# Create PyInstaller spec file
echo -e "${BLUE}Creating PyInstaller spec file...${NC}"
cat > superwhisper.spec << 'EOL'
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all whisper model files and data
whisper_datas = collect_data_files('whisper')
numpy_datas = collect_data_files('numpy')

# Collect all required hidden imports
hidden_imports = [
    'numpy',
    'pyaudio',
    'pynput',
    'pyperclip',
    'whisper',
    'torch',
    'tqdm',
    'regex',
    'requests',
    'tiktoken',
] + collect_submodules('whisper')

a = Analysis(
    ['superwhisper.py'],
    pathex=[],
    binaries=[],
    datas=whisper_datas + numpy_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add torch and its dependencies
torch_path = os.path.dirname(os.__file__) + '/site-packages/torch'
if os.path.exists(torch_path):
    a.datas += [(os.path.join('torch', f), os.path.join(torch_path, f), 'DATA') 
                for f in os.listdir(torch_path) if f.endswith('.dylib')]

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Superwhisper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Superwhisper',
)

app = BUNDLE(
    coll,
    name='Superwhisper.app',
    bundle_identifier='com.superwhisper.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
        'NSMicrophoneUsageDescription': 'Superwhisper needs access to your microphone to record audio for transcription.',
        'NSHighResolutionCapable': True,
        'LSEnvironment': {
            'DYLD_LIBRARY_PATH': '@executable_path/../Resources/lib',
            'PYTHONPATH': '@executable_path/../Resources/lib/python3.11/site-packages',
        },
    },
)
EOL

# Build the app
echo -e "${BLUE}Building macOS application...${NC}"
python3 -m PyInstaller superwhisper.spec

# Verify the build
if [ ! -d "dist/Superwhisper.app" ]; then
    echo -e "${RED}Build failed! The application bundle was not created.${NC}"
    exit 1
fi

echo -e "${GREEN}Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}You can now:${NC}"
echo "1. Run from terminal: ${GREEN}./run.sh${NC}"
echo "2. Use the app: ${GREEN}open dist/Superwhisper.app${NC}"

# Check for microphone permissions
echo ""
echo -e "${BLUE}Important:${NC}"
echo "1. Make sure to grant microphone permissions when prompted"
echo "2. If no prompt appears, grant permissions manually in System Settings > Privacy & Security > Microphone"

# Move app to Applications folder
echo ""
echo -e "${BLUE}Would you like to install Superwhisper.app to your Applications folder? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Installing to Applications folder..."
    cp -r "dist/Superwhisper.app" "/Applications/"
    echo -e "${GREEN}Installed! You can now find Superwhisper in your Applications folder.${NC}"
fi 