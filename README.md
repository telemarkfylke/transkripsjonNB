# 🎤 Hugin Transcription Service

An automated Norwegian transcription service using the National Library of Norway's WhisperX model. This service monitors Azure Blob Storage for audio/video files, transcribes them using AI, and delivers results via email and Teams notifications.

## 🚀 Features

- **Norwegian-optimized transcription** using NbAiLab/nb-whisper-medium
- **Automated file processing** from Azure Blob Storage
- **Multi-format support** (MP3, MP4, MOV, AVI, WAV)
- **Email delivery** with full transcription attachments
- **Teams notifications** for job completion
- **Secure file handling** with automatic cleanup
- **Apple Silicon optimization** for M1/M2/M3/M4 Macs

## 📋 Prerequisites

- **macOS** (tested on Apple Silicon Macs)
- **Homebrew** package manager
- **Azure Blob Storage** account
- **OpenAI API** key
- **Microsoft Teams/Logic App** integration

## ⚡ Quick Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/telemarkfylke/transkripsjonNB.git
   cd transkripsjonNB
   ```

2. **Run the automated installer:**
   ```bash
   ./install.sh
   ```

   This script will:
   - Install UV (Python package manager)
   - Install system dependencies (ffmpeg)
   - Create Python virtual environment
   - Install all Python dependencies
   - Download and cache the WhisperX model
   - Set up directory structure
   - Create scheduled task configuration

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Start the scheduled service:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.tfk.hugin-transcription.plist
   ```

## 🔧 Configuration

Create a `.env` file in the project root with:

```env
# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your_azure_connection_string
AZURE_STORAGE_CONTAINER_NAME=your_container_name

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Teams/Email Integration
LOGIC_APP_CHAT_URL=your_logic_app_webhook_url
```

## 🔄 How It Works

1. **File Upload**: Users upload audio/video files to Azure Blob Storage with metadata
2. **Detection**: Service checks for new files every 10 minutes
3. **Download**: Files are securely downloaded to temporary storage
4. **Processing**: 
   - Video files converted to audio (ffmpeg)
   - Audio transcribed using Norwegian WhisperX model
   - Text cleaned and formatted
5. **Delivery**: 
   - Full transcription sent via email
   - Teams notification sent to user
6. **Cleanup**: All temporary files automatically deleted

## 🧪 Testing

**Health check:**
```bash
# Run comprehensive system validation
./health_check.py
```

**Manual run:**
```bash
# Activate environment and run once
source .venv/bin/activate
python HuginLokalTranskripsjon.py
```

**Test Teams integration:**
```bash
python test.py
```

**Check scheduled service:**
```bash
# Verify service is loaded
launchctl list | grep com.tfk.hugin-transcription

# View logs
tail -f logs/transcription.stdout
tail -f logs/transcription.stderr
```

## 📊 Monitoring

**Log files:**
- `logs/transcription.stdout` - Standard output
- `logs/transcription.stderr` - Error messages
- `hugin_transcription.log` - Application logs

**Service management:**
```bash
# Stop scheduled service
launchctl unload ~/Library/LaunchAgents/com.tfk.hugin-transcription.plist

# Start scheduled service
launchctl load ~/Library/LaunchAgents/com.tfk.hugin-transcription.plist

# Check service status
launchctl list | grep hugin-transcription
```

## 🏗️ Architecture

```
├── HuginLokalTranskripsjon.py    # Main orchestrator
├── lib/
│   └── hugintranskriptlib.py     # Core functions library
├── .venv/                        # UV virtual environment
├── blobber/                      # Temporary downloads
├── ferdig_tekst/                 # Processed transcriptions
├── oppsummeringer/               # AI summaries
└── logs/                         # Service logs
```

## 🔒 Security

- Input sanitization prevents path traversal attacks
- Environment variables for sensitive data
- Automatic cleanup of temporary files
- File size limits for attachments
- Secure Azure SDK integration

## 🛠️ Development

**Install development dependencies:**
```bash
uv sync --group dev
```

**Code formatting:**
```bash
black .
isort .
flake8 .
```

**Dependencies managed via:**
- `pyproject.toml` - Project configuration
- UV for virtual environment and dependency resolution

## 📚 Dependencies

**Core:**
- WhisperX (transformers, torch)
- Azure Blob Storage SDK
- OpenAI API client
- ffmpeg for audio conversion

**Full list in `pyproject.toml`**

## 🤝 Support

- **Documentation**: See CLAUDE.md for detailed technical information
- **Issues**: Report bugs via GitHub Issues
- **Architecture**: Norwegian-optimized transcription pipeline

---

*Developed by Telemark Fylkeskommune for automated transcription services.*