# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Norwegian transcription service that uses MLX Whisper from the National Library of Norway (NbAiLab/nb-whisper-medium-mlx) to transcribe audio and video files. The system integrates with Azure Blob Storage for file management, SharePoint for secure file sharing, and Microsoft Graph API for email notifications. Additionally, it provides AI-powered meeting summaries using Ollama for generating structured meeting abstracts. Files are converted to DOCX format for delivery.

## Architecture

### Core Components

- **HuginLokalTranskripsjon.py**: Main orchestrator script that processes files from Azure Blob Storage
- **lib/hugintranskriptlib.py**: Core library containing all transcription, AI summarization, file handling, SharePoint integration, and communication functions
- **lib/transkripsjon_sp_lib.py**: SharePoint library for Microsoft Graph API operations
- **lib/ai_tools.py**: AI summarization library with Ollama integration for generating meeting abstracts

### Data Flow

1. Files are uploaded to Azure Blob Storage with user metadata (UPN)
2. Main script periodically checks for new files (every 30 minutes via launchctl)
3. Files are downloaded, transcribed using MLX Whisper, and processed
4. Video files (MP4, MOV, AVI) and M4A audio files are converted to WAV format using ffmpeg
5. AI-powered meeting summaries are generated using Ollama (if available)
6. Transcriptions and summaries are converted to DOCX format using python-docx
7. Both transcription and summary DOCX files are uploaded to SharePoint with unique names and user-specific permissions
8. Secure SharePoint download links are generated for both files
9. Email notifications sent with both SharePoint download links via Microsoft Graph API
10. All temporary files are cleaned up

### Key Dependencies

- **MLX Whisper**: For speech-to-text transcription using NbAiLab/nb-whisper-medium-mlx with Apple Silicon GPU acceleration
- **Ollama**: For AI-powered meeting summarization using local language models (default: gpt-oss:20b)
- **Azure SDK**: For blob storage operations
- **Microsoft Graph API**: For SharePoint file operations and email sending
- **ffmpeg**: For audio/video conversion
- **python-docx**: For creating Word documents

## Environment Setup

### Required Environment Variables

Create a `.env` file with:
```
# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER_NAME=your_container_name

# Microsoft Graph API (for SharePoint and notifications)
TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SHAREPOINT_SITE_URL=your_sharepoint_site_url
DEFAULT_LIBRARY=Documents


# Ollama Configuration (optional - for AI summarization)
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_ENDPOINT=http://localhost:11434

```

### Python Environment

- Python 3.10.x required
- Uses UV virtual environment: `.venv`
- Managed via UV package manager

### System Dependencies

- ffmpeg installed via Homebrew: `/opt/homebrew/bin`
- MLX Whisper from https://github.com/ml-explore/mlx-examples/tree/main/whisper
- Ollama service running locally with the required model (default: gpt-oss:20b)

## Running the Application

### Manual Execution
```bash
python HuginLokalTranskripsjon.py
```

### Scheduled Execution
The system runs every 30 minutes via launchctl using the plist file:
```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.tfk.hugin-transcription.plist

# Check status
launchctl list | grep com.tfk.hugin-transcription

# View logs
tail -f logs/transcription.stdout
tail -f logs/transcription.stderr
```

### Testing
```bash
# Manual run for testing
python HuginLokalTranskripsjon.py
```

## File Structure

```
├── HuginLokalTranskripsjon.py    # Main application
├── lib/
│   ├── hugintranskriptlib.py     # Core functions library
│   ├── transkripsjon_sp_lib.py   # SharePoint/Graph API library
│   └── ai_tools.py               # AI summarization library (Ollama integration)
├── testfiles/                    # Test files directory (see README for samples)
├── com.tfk.hugin-transcription.plist.example  # LaunchAgent configuration
├── blobber/                      # Temporary download directory
├── ferdig_tekst/                 # Transcribed text and DOCX output
├── oppsummeringer/              # AI-generated summaries
├── dokumenter/                   # Temporary SharePoint upload directory
└── logs/                         # Application logs
```

## Security Considerations

- Input sanitization implemented for filenames to prevent path traversal
- SharePoint files have exclusive user permissions (only the requesting UPN can access)
- Secure sharing links generated for SharePoint downloads
- Temporary files are automatically cleaned up after processing
- Environment variables used for sensitive configuration
- Microsoft Graph API authentication using application credentials

## Key Functions (lib/hugintranskriptlib.py)

### Core Transcription Functions
- `transkriber()`: Main transcription using NbAiLab MLX Whisper model with Apple Silicon GPU acceleration
- `create_ai_summary()`: Generate AI-powered meeting summaries using Ollama
- `konverter_til_lyd()`: Convert video files and M4A audio to WAV format using ffmpeg

### Azure Blob Storage Operations
- `list_blobs()`: List files in Azure container
- `download_blob()`: Download file from Azure storage
- `delete_blob()`: Remove processed files from Azure storage
- `get_blob_metadata()`: Extract user metadata from blobs

### SharePoint and Notifications
- `sendNotificationWithSummary()`: Enhanced email notification function with both transcription and AI summary SharePoint links
- `sendNotification()`: Legacy email notification function for transcription only
- `_upload_to_sharepoint_custom()`: Upload DOCX files to SharePoint with unique names
- `_send_email_graph()`: Send emails via Microsoft Graph API


## Key Functions (lib/ai_tools.py)

### AI Summarization Functions
- `generate_meeting_summary()`: Generate structured meeting summaries using Ollama with Norwegian prompts
- `is_ollama_available()`: Check if Ollama service and specified model are accessible
- `get_available_models()`: List available Ollama models

## Key Functions (lib/transkripsjon_sp_lib.py)

- `hentToken()`: Authenticate to Microsoft Graph and return access token
- `_hentSiteId()`: Get SharePoint site ID from URL
- `_settTilganger()`: Set user permissions on SharePoint files
- `_lagDelingslenke()`: Generate secure sharing links

## Microsoft Graph API Permissions Required

For full functionality, the Azure App Registration needs these **Application permissions**:

### SharePoint Operations (Working)
- `Sites.ReadWrite.All`: Read/write SharePoint sites and document libraries
- `Files.ReadWrite.All`: Read/write files in SharePoint

### Email (Requires Setup)
- `Mail.Send`: Send emails on behalf of users

## Logging

- Main logs written to `logs/hugintranskripsjonslog.txt`
- Backup log at `hugin_transcription.log` (for compatibility)
- Scheduled service logs: `logs/transcription.stdout`, `logs/transcription.stderr`
- Also outputs to stdout for launchctl monitoring
- Detailed SharePoint upload and Graph API operation logging
- Enhanced error handling and troubleshooting information

## Supported File Formats

- **Audio**: MP3, WAV, M4A
- **Video**: MP4, MOV, AVI
- **Output**: DOCX format for all transcribed files and AI-generated summaries

Video files and M4A audio are automatically converted to WAV format before transcription.

## AI Summarization Features

### Ollama Integration
- **Local AI Processing**: Uses Ollama for privacy-preserving AI summarization
- **Norwegian Language Model**: Optimized prompts for Norwegian meeting abstracts
- **Default Model**: gpt-oss:20b (configurable via environment variables)
- **Fallback Behavior**: Gracefully continues without AI summary if Ollama is unavailable
- **Structured Output**: Generates well-formatted meeting abstracts with AI disclaimer

### Summary Content Structure
- **Meeting Overview**: Key topics and decisions discussed
- **Action Items**: Clear listing of follow-up tasks and responsible parties
- **Timeline Information**: Important dates and deadlines mentioned
- **AI Disclaimer**: Clear indication that summary is AI-generated and may contain errors
- **Signature Fields**: Spaces for meeting referent and approver signatures

### Email Notifications
Users receive two separate SharePoint download links:
1. **Full Transcription**: Complete word-for-word transcript in DOCX format
2. **AI Summary**: Structured meeting abstract with key points and action items

Both files are securely stored in SharePoint with user-specific access permissions.