# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Norwegian transcription service that uses MLX Whisper from the National Library of Norway (NbAiLab/nb-whisper-medium-mlx) to transcribe audio and video files. The system integrates with Azure Blob Storage for file management, SharePoint for secure file sharing, and Microsoft Graph API for email notifications. Files are converted to DOCX format for delivery.

## Architecture

### Core Components

- **HuginLokalTranskripsjon.py**: Main orchestrator script that processes files from Azure Blob Storage
- **lib/hugintranskriptlib.py**: Core library containing all transcription, file handling, SharePoint integration, and communication functions
- **lib/transkripsjon_sp_lib.py**: SharePoint library for Microsoft Graph API operations

### Data Flow

1. Files are uploaded to Azure Blob Storage with user metadata (UPN)
2. Main script periodically checks for new files (every 30 minutes via launchctl)
3. Files are downloaded, transcribed using MLX Whisper, and processed
4. Video files (MP4, MOV, AVI) and M4A audio files are converted to WAV format using ffmpeg
5. Transcriptions are converted to DOCX format using python-docx
6. DOCX files are uploaded to SharePoint with unique names and user-specific permissions
7. Secure SharePoint download links are generated
8. Email notifications sent with SharePoint download links via Microsoft Graph API
9. All temporary files are cleaned up

### Key Dependencies

- **MLX Whisper**: For speech-to-text transcription using NbAiLab/nb-whisper-medium-mlx with Apple Silicon GPU acceleration
- **Azure SDK**: For blob storage operations
- **Microsoft Graph API**: For SharePoint file operations and email sending
- **OpenAI API**: For generating summaries and meeting notes
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

# OpenAI API
OPENAI_API_KEY=your_openai_key

```

### Python Environment

- Python 3.10.x required
- Uses UV virtual environment: `.venv`
- Managed via UV package manager

### System Dependencies

- ffmpeg installed via Homebrew: `/opt/homebrew/bin`
- MLX Whisper from https://github.com/ml-explore/mlx-examples/tree/main/whisper

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
│   └── transkripsjon_sp_lib.py   # SharePoint/Graph API library
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
- `oppsummering()`: AI-powered meeting summaries using OpenAI GPT-4
- `konverter_til_lyd()`: Convert video files and M4A audio to WAV format using ffmpeg

### Azure Blob Storage Operations
- `list_blobs()`: List files in Azure container
- `download_blob()`: Download file from Azure storage
- `delete_blob()`: Remove processed files from Azure storage
- `get_blob_metadata()`: Extract user metadata from blobs

### SharePoint and Notifications (New)
- `sendNotification()`: Main email notification function using SharePoint links and Graph API (handles DOCX files)
- `_upload_to_sharepoint_custom()`: Upload transcribed DOCX files to SharePoint with unique names
- `_send_email_graph()`: Send emails via Microsoft Graph API


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
- **Output**: DOCX format for all transcribed files

Video files and M4A audio are automatically converted to WAV format before transcription.