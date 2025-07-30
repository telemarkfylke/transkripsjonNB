# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Norwegian transcription service that uses WhisperX from the National Library of Norway (NbAiLab/nb-whisper-medium) to transcribe audio and video files. The system integrates with Azure Blob Storage for file management and sends results via email and Teams notifications.

## Architecture

### Core Components

- **HuginLokalTranskripsjon.py**: Main orchestrator script that processes files from Azure Blob Storage
- **lib/hugintranskriptlib.py**: Core library containing all transcription, file handling, and communication functions
- **test.py**: Simple test script for Teams chat functionality

### Data Flow

1. Files are uploaded to Azure Blob Storage with user metadata (UPN)
2. Main script periodically checks for new files (every 30 minutes via launchctl)
3. Files are downloaded, transcribed using WhisperX, and processed
4. Results are sent via email with full transcription as attachment
5. Teams notification sent to inform user of completion
6. All temporary files are cleaned up

### Key Dependencies

- **WhisperX/Transformers**: For speech-to-text transcription using NbAiLab/nb-whisper-medium
- **Azure SDK**: For blob storage operations
- **OpenAI API**: For generating summaries and meeting notes
- **ffmpeg**: For audio/video conversion
- **python-docx**: For creating Word documents

## Environment Setup

### Required Environment Variables

Create a `.env` file with:
```
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER_NAME=your_container_name
OPENAI_API_KEY=your_openai_key
LOGIC_APP_CHAT_URL=your_logic_app_url
```

### Python Environment

- Python 3.10.x required
- Uses conda environment: `lokaltranskripsjon`
- Location: `/opt/homebrew/Caskroom/miniconda/base/envs/lokaltranskripsjon/bin/python`

### System Dependencies

- ffmpeg installed via Homebrew: `/opt/homebrew/bin`
- WhisperX from https://github.com/m-bain/whisperX

## Running the Application

### Manual Execution
```bash
python HuginLokalTranskripsjon.py
```

### Scheduled Execution
The system runs every 30 minutes via launchctl using the plist file:
```bash
# Load the service
launchctl load local.example.hello.plist

# Check status
launchctl list | grep local.example.hello

# View logs
tail -f hello.stdout
tail -f hello.stderr
```

### Testing
```bash
python test.py  # Test Teams chat functionality
```

## File Structure

```
├── HuginLokalTranskripsjon.py    # Main application
├── lib/
│   └── hugintranskriptlib.py     # Core functions library
├── test.py                       # Test script
├── testfiles/                    # Sample audio files
├── local.example.hello.plist     # LaunchAgent configuration
├── blobber/                      # Temporary download directory
├── ferdig_tekst/                 # Transcribed text output
└── oppsummeringer/              # AI-generated summaries
```

## Security Considerations

- Input sanitization implemented for filenames to prevent path traversal
- File size limits enforced for email/Teams attachments
- Temporary files are automatically cleaned up after processing
- Environment variables used for sensitive configuration

## Key Functions (lib/hugintranskriptlib.py)

- `transkriber()`: Main transcription using NbAiLab WhisperX model
- `oppsummering()`: AI-powered meeting summaries using OpenAI GPT-4
- `send_email()`: Send transcription via Logic App email service
- `sendTeamsChat()`: Send Teams notifications
- `konverter_til_lyd()`: Convert video to audio using ffmpeg
- Azure blob operations: `list_blobs()`, `download_blob()`, `delete_blob()`

## Logging

- Logs written to `hugin_transcription.log`
- Also outputs to stdout for launchctl monitoring
- Separate stdout/stderr files: `hello.stdout`, `hello.stderr`