# 🎤 Hugin Transcription Service

An automated Norwegian transcription service using the National Library of Norway's MLX Whisper model optimized for Apple Silicon. This service monitors Azure Blob Storage for audio/video files, transcribes them using AI, uploads results to SharePoint, and delivers secure download links via email notifications using Microsoft Graph API.

## 🚀 Features

- **Norwegian-optimized transcription** using NbAiLab/nb-whisper-medium-mlx with Apple Silicon GPU acceleration
- **Automated file processing** from Azure Blob Storage
- **Multi-format support** (MP3, MP4, MOV, AVI, WAV, M4A)
- **SharePoint integration** with secure file uploads and user-specific permissions
- **Email delivery** with SharePoint download links via Microsoft Graph API
- **Secure file handling** with automatic cleanup and unique filenames
- **Apple Silicon optimization** for M1/M2/M3/M4 Macs

## 📋 Prerequisites

- **macOS** (tested on Apple Silicon Macs)
- **Homebrew** package manager
- **Azure Blob Storage** account
- **SharePoint** site for file storage
- **Microsoft Graph API** application registration
- **OpenAI API** key

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
   - Download and cache the MLX Whisper model
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

   > **Note**: The install script automatically creates the plist file. You can also manually copy and customize `com.tfk.hugin-transcription.plist.example` if needed.

## 🔧 Configuration

Create a `.env` file in the project root with:

```env
# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your_azure_connection_string
AZURE_STORAGE_CONTAINER_NAME=your_container_name

# Microsoft Graph API (for SharePoint and notifications)
TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SHAREPOINT_SITE_URL=your_sharepoint_site_url
DEFAULT_LIBRARY=Documents

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
```

### Microsoft Graph API Permissions

Configure your Azure App Registration with these **Application permissions**:

#### Currently Working:
- `Sites.ReadWrite.All` - Read/write SharePoint sites and libraries
- `Files.ReadWrite.All` - Read/write files in SharePoint

#### Required for Email (Add these permissions):
- `Mail.Send` - Send emails on behalf of users

## 🔄 How It Works

1. **File Upload**: Users upload audio/video files to Azure Blob Storage with metadata
2. **Detection**: Service checks for new files every 30 minutes
3. **Download**: Files are securely downloaded to temporary storage
4. **Processing**: 
   - Video files and M4A audio converted to WAV format (ffmpeg)
   - Audio transcribed using Norwegian MLX Whisper model with Apple Silicon GPU acceleration
   - Text cleaned and formatted
   - Transcription converted to DOCX format
5. **SharePoint Upload**:
   - Transcribed files uploaded to SharePoint as DOCX documents with unique names (filename_timestamp.docx)
   - User-specific permissions applied (only requesting user can access)
   - Secure sharing links generated
6. **Delivery**: 
   - Email sent with SharePoint download link (via Microsoft Graph API)
7. **Cleanup**: All temporary files automatically deleted

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
- `logs/hugintranskripsjonslog.txt` - Main application log with detailed flow information
- `logs/transcription.stdout` - Standard output from scheduled runs
- `logs/transcription.stderr` - Error messages from scheduled runs
- `hugin_transcription.log` - Backup application log (for compatibility)

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
│   ├── hugintranskriptlib.py     # Core functions library
│   └── transkripsjon_sp_lib.py   # SharePoint/Graph API library
├── test_notification.py          # Test email notification system
├── test_graph_api.py             # Test Graph API email function
├── .venv/                        # UV virtual environment
├── blobber/                      # Temporary downloads
├── ferdig_tekst/                 # Processed transcriptions
├── oppsummeringer/               # AI summaries
├── dokumenter/                   # Temporary SharePoint uploads
└── logs/                         # Service logs
```

## 🔒 Security

- Input sanitization prevents path traversal attacks
- Environment variables for sensitive data
- Automatic cleanup of temporary files
- SharePoint files have exclusive user permissions (only requesting UPN can access)
- Secure sharing links with user-specific access
- Microsoft Graph API authentication using application credentials
- Unique filenames prevent collisions and enhance security

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
- MLX Whisper (Apple Silicon GPU accelerated)
- Azure Blob Storage SDK
- Microsoft Graph API SDK (requests)
- OpenAI API client
- ffmpeg for audio conversion

**Full list in `pyproject.toml`**

## 🤝 Support

- **Documentation**: See CLAUDE.md for detailed technical information
- **Issues**: Report bugs via GitHub Issues
- **Architecture**: Norwegian-optimized transcription pipeline

---

*Developed by Telemark Fylkeskommune for automated transcription services.*