#!/bin/bash

# Hugin Transcription Service Installation Script for M4 Mac
# This script sets up the complete environment for running the transcription service

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${BLUE}🚀 Starting Hugin Transcription Service Installation${NC}"
echo "Project directory: $PROJECT_ROOT"

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS only"
    exit 1
fi

# Check if running on Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    print_warning "This script is optimized for Apple Silicon (M1/M2/M3/M4) Macs"
    print_warning "It may work on Intel Macs but hasn't been tested"
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    print_error "Homebrew is required but not installed"
    echo "Please install Homebrew first: https://brew.sh/"
    exit 1
fi

print_status "Homebrew found"

# Install system dependencies
echo -e "${BLUE}📦 Installing system dependencies...${NC}"

# Install ffmpeg if not present
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing ffmpeg..."
    brew install ffmpeg
    print_status "ffmpeg installed"
else
    print_status "ffmpeg already installed"
fi

# Install Ollama if not present
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    print_status "Ollama installed"
    print_warning "Please start Ollama service and install the model manually:"
    print_warning "  ollama serve"
    print_warning "  ollama pull gpt-oss:20b"
else
    print_status "Ollama already installed"
fi

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the shell configuration to make uv available
    source "$HOME/.cargo/env" 2>/dev/null || true
    print_status "UV installed"
else
    print_status "UV already installed"
fi

# Ensure UV is in PATH
if ! command -v uv &> /dev/null; then
    print_error "UV installation failed or not in PATH"
    echo "Please ensure UV is installed and available in your PATH"
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_ROOT"

# Create UV virtual environment
echo -e "${BLUE}🐍 Setting up Python virtual environment...${NC}"

if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists, removing old one..."
    rm -rf .venv
fi

# Create virtual environment with Python 3.11 (optimized for M4)
uv venv .venv --python 3.11
print_status "Virtual environment created"

# Activate virtual environment and install dependencies
echo -e "${BLUE}📚 Installing Python dependencies...${NC}"
uv sync
print_status "Python dependencies installed"

# Create required directories
echo -e "${BLUE}📁 Creating required directories...${NC}"
mkdir -p blobber ferdig_tekst oppsummeringer logs
print_status "Directory structure created"

# Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    echo "Please create a .env file with the following variables:"
    echo "  AZURE_STORAGE_CONNECTION_STRING=your_connection_string"
    echo "  AZURE_STORAGE_CONTAINER_NAME=your_container_name"
    echo "  OLLAMA_MODEL=gpt-oss:20b (for AI summarization)"
    echo "  OLLAMA_ENDPOINT=http://localhost:11434"
    echo ""
    echo "You can copy .env.example to .env and fill in your values"
else
    print_status ".env file found"
fi

# Download and cache the MLX Whisper model
echo -e "${BLUE}🤖 Downloading MLX Whisper model (this may take a while)...${NC}"
.venv/bin/python -c "
import os
import mlx_whisper
print('Loading NbAiLab/nb-whisper-medium-mlx model...')
# This will download and cache the model if not present
result = mlx_whisper.load_model('nb-whisper-medium-mlx')
print('MLX model downloaded and cached successfully!')
" || print_warning "MLX model download failed, will be downloaded on first run"

# Validate installation
echo -e "${BLUE}🔍 Validating installation...${NC}"

# Run comprehensive health check
if .venv/bin/python health_check.py; then
    print_status "All health checks passed"
else
    print_error "Health check failed - see output above for details"
    exit 1
fi

# Create or update LaunchAgent plist
echo -e "${BLUE}⏰ Setting up scheduled task...${NC}"

PLIST_FILE="$HOME/Library/LaunchAgents/com.tfk.hugin-transcription.plist"
PYTHON_PATH="$PROJECT_ROOT/.venv/bin/python"
SCRIPT_PATH="$PROJECT_ROOT/run_transcription.sh"

# Create the runner script
cat > "$PROJECT_ROOT/run_transcription.sh" << EOF
#!/bin/bash

# Set up environment
export PATH="/opt/homebrew/bin:\$PATH"
cd "$PROJECT_ROOT"

# Activate virtual environment and run
source .venv/bin/activate
python HuginLokalTranskripsjon.py
EOF

chmod +x "$PROJECT_ROOT/run_transcription.sh"

# Create the plist file
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tfk.hugin-transcription</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_PATH</string>
    </array>
    <key>StartInterval</key>
    <integer>600</integer>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/logs/transcription.stdout</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/logs/transcription.stderr</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

print_status "LaunchAgent plist created at $PLIST_FILE"

echo -e "${GREEN}✅ Installation completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Configure your .env file with Azure credentials and Ollama settings"
echo "2. Set up Ollama (if not done automatically):"
echo "   ${YELLOW}ollama serve${NC} (start service)"
echo "   ${YELLOW}ollama pull gpt-oss:20b${NC} (download AI model)"
echo "3. Test the installation:"
echo "   ${YELLOW}./run_transcription.sh${NC}"
echo "4. Load the scheduled task:"
echo "   ${YELLOW}launchctl load ~/Library/LaunchAgents/com.tfk.hugin-transcription.plist${NC}"
echo "5. Check if the service is loaded:"
echo "   ${YELLOW}launchctl list | grep com.tfk.hugin-transcription${NC}"
echo "6. Monitor logs:"
echo "   ${YELLOW}tail -f logs/transcription.stdout${NC}"
echo "   ${YELLOW}tail -f logs/transcription.stderr${NC}"
echo ""
echo "The service will run every 10 minutes once loaded."
echo "For manual testing, you can also run: ${YELLOW}python HuginLokalTranskripsjon.py${NC}"
echo ""
echo -e "${YELLOW}Note: AI summarization will be skipped if Ollama is not running or the model is unavailable${NC}"