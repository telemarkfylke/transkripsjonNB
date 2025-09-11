# Test Files

This directory contains test audio files for development and testing.

## Test File

- **audio_king.mp3** - Norwegian audio sample for testing transcription functionality

## Testing Process

1. Upload test files to Azure Blob Storage with proper UPN metadata
2. Monitor logs in `logs/hugintranskripsjonslog.txt`
3. Check SharePoint for processed DOCX files
4. Verify email notifications are sent

## Supported Formats

- Audio: MP3, WAV, M4A
- Video: MP4, MOV, AVI

All files are automatically converted to WAV format before transcription.