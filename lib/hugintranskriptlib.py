import os
import logging
import time
import json
import warnings
import dotenv
import requests
import ffmpeg
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from transformers import pipeline
from docx import Document
import mlx.core as mx
import mlx_whisper
try:
    from .transkripsjon_sp_lib import hentToken
    from .ai_tools import generate_meeting_summary, is_ollama_available
except ImportError:
    from transkripsjon_sp_lib import hentToken
    from ai_tools import generate_meeting_summary, is_ollama_available

# Ensure ffmpeg is in PATH
os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')

dotenv.load_dotenv()
warnings.filterwarnings("ignore")

# Konfigurer logging
logger = logging.getLogger(__name__)


# Funksjoner
def download_blob(AZURE_STORAGE_CONNECTION_STRING, container_name, blob_name, download_file_path):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    print("Downloading blob to: " + download_file_path)

    with open(download_file_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())
    print(f"Blob {blob_name} successfully downloaded to {download_file_path}")

# Functioon to list all blobs in a container
def list_blobs(AZURE_STORAGE_CONNECTION_STRING, container_name) -> list:
    filnavn = []
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(container_name)
    print("Listing blobs...")
    for blob in container_client.list_blobs():
        print(blob.name)
        filnavn.append(blob.name)
    return filnavn

# Get metadata of a blob
def get_blob_metadata(AZURE_STORAGE_CONNECTION_STRING, container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    print("Blob metadata: " + str(blob_client.get_blob_properties().metadata))
    # metadata.append(blob_client.get_blob_properties().metadata)
    return blob_client.get_blob_properties().metadata

# Delete downloaded blob
def delete_blob(AZURE_STORAGE_CONNECTION_STRING, container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    print("Deleting blob: " + blob_name)
    blob_client.delete_blob()
    print("Blob deleted")

# Konverterer video til lyd
def konverter_til_lyd(filnavn, nytt_filnavn):
    # Konverterer video til lyd
    print(f'Konverterer {filnavn} til lyd.')
    ffmpeg.input(filnavn).output(nytt_filnavn, acodec='pcm_s16le', format='wav').run(overwrite_output=True)
    print(f'Konvertering ferdig. Lydfilen er lagret som {nytt_filnavn}')

# Transkriber blob og lagrer i SRT-fil
def transkriber(sti, filnavn, word_timestamps=False):
        print(f'Transkriberer lyd fra {filnavn} til tekst. Obs: Dette er en tidkrevende prosess.')
        print(f"🇳🇴 MLX Norwegian (Apple Silicon GPU)")
        print("=" * 50)

        device = mx.default_device()
        print(f"MLX Device: {device}")

        start_time = time.time()

        # Transkriberer lydfilen med MLX Norwegian model
        audio_path = sti + filnavn

        # Use local nb-whisper-medium-mlx model
        model_path = "./nb-whisper-medium-mlx"
        if not os.path.exists(os.path.join(model_path, "config.json")):
            print(f"❌ Local MLX model not found at {model_path}")
            raise FileNotFoundError(f"Required MLX model not found at {model_path}")

        print(f"✅ Using local Norwegian MLX model: {model_path}")

        transcribe_params = {
            "path_or_hf_repo": model_path,
            "language": "no",
            "verbose": False,
            "temperature": 0.0
        }

        # Only add word_timestamps if True (for performance)
        if word_timestamps:
            transcribe_params["word_timestamps"] = True

        print("Transcribing with Norwegian MLX model...")
        transcribe_start = time.time()
        result = mlx_whisper.transcribe(audio_path, **transcribe_params)
        transcribe_time = time.time() - transcribe_start

        total_time = time.time() - start_time
        print(f"Transcription completed in {transcribe_time:.2f} seconds")

        # Sørg for at utdata-mappe eksisterer
        os.makedirs("./ferdig_tekst", exist_ok=True)

        # Always create text file
        full_text = result.get('text', '')
        tekst_data = [f"{full_text}\n"] if full_text else []

        with open(f"./ferdig_tekst/{filnavn.split('.')[0]}.txt", 'w', encoding='utf-8') as f:
            f.write(''.join(tekst_data))

        # Only create SRT file if word_timestamps is True
        if word_timestamps:
            srt_data = []

            if 'segments' in result and result['segments']:
                # Use segments with timestamps
                for i, segment in enumerate(result['segments'], start=1):
                    start_time_ts = segment.get('start', 0.0)
                    end_time_ts = segment.get('end', start_time_ts + 1.0)
                    text = segment.get('text', '').strip()

                    if text:
                        # Convert timestamps to datetime objects (subtract 1 hour as in original)
                        start_time = datetime.fromtimestamp(start_time_ts) - timedelta(hours=1)
                        end_time = datetime.fromtimestamp(end_time_ts) - timedelta(hours=1)

                        start_time_str = start_time.strftime('%H:%M:%S,%f')[:-3]
                        end_time_str = end_time.strftime('%H:%M:%S,%f')[:-3]

                        # Create SRT string
                        srt_string = f"{i}\n{start_time_str} --> {end_time_str}\n{text}\n"
                        srt_data.append(srt_string)
            else:
                # Fallback: use full text without timestamps if segments are not available
                if full_text:
                    # Create a single segment for the entire text
                    start_time = datetime.fromtimestamp(0) - timedelta(hours=1)
                    end_time = datetime.fromtimestamp(60) - timedelta(hours=1)  # Default 1 minute

                    start_time_str = start_time.strftime('%H:%M:%S,%f')[:-3]
                    end_time_str = end_time.strftime('%H:%M:%S,%f')[:-3]

                    srt_string = f"1\n{start_time_str} --> {end_time_str}\n{full_text}\n"
                    srt_data.append(srt_string)

            # Skriver til SRT-fil
            with open(f"./ferdig_tekst/{filnavn.split('.')[0]}.srt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_data))

            print(f'Transkripsjonen er lagret i ./ferdig_tekst/{filnavn.split(".")[0]}.srt og .txt')
        else:
            print(f'Transkripsjonen er lagret i ./ferdig_tekst/{filnavn.split(".")[0]}.txt')


# Konverterer srt-fil til ren telst med kun tekst uten tidskoder og index
def srt_til_tekst(filnavn):
    with open("./ferdig_tekst/" +  filnavn, 'r', encoding='utf-8') as f:
        srt_data = f.readlines()

    ren_tekst = []
    for i in range(0, len(srt_data)):
        if srt_data[i].startswith(" ") and srt_data[i].endswith("\n"):
            ren_tekst.append(srt_data[i])

    # Sørg for at utdata-mappe eksisterer
    os.makedirs("./oppsummeringer", exist_ok=True)
    
    # Skriv for hvert element i ren_tekst skriv en ny linje i en docx-fil
    with open("./oppsummeringer/" + filnavn.split(".")[0] + ".txt", 'w', encoding='utf-8') as f:
        f.write("".join(ren_tekst))


def create_ai_summary(filnavn: str, model: str = "gpt-oss:20b") -> dict:
    """
    Create AI-generated meeting summary using Ollama from transcribed text

    Args:
        filnavn: Base filename (without extension) of the transcribed file
        model: Ollama model to use for summarization

    Returns:
        dict: Paths to generated summary files {'txt': path, 'docx': path} or empty dict if failed
    """
    logger.info(f"Creating AI summary for {filnavn}")

    # Check if Ollama is available
    if not is_ollama_available(model):
        logger.warning(f"Ollama model '{model}' not available, skipping AI summary")
        return {}

    # Read transcribed text
    text_file_path = f"./ferdig_tekst/{filnavn}.txt"
    if not os.path.exists(text_file_path):
        logger.error(f"Transcribed text file not found: {text_file_path}")
        return {}

    try:
        with open(text_file_path, 'r', encoding='utf-8') as f:
            transcription_text = f.read()

        if not transcription_text.strip():
            logger.warning(f"Transcribed text file is empty: {text_file_path}")
            return {}

        # Generate summary using Ollama
        logger.info(f"Generating summary using model: {model}")
        summary_text = generate_meeting_summary(transcription_text, model)

        if not summary_text:
            logger.error("Failed to generate summary with Ollama")
            return {}

        # Ensure output directory exists
        os.makedirs("./oppsummeringer", exist_ok=True)

        # Save summary as text file
        summary_txt_path = f"./oppsummeringer/{filnavn}_ai_sammendrag.txt"
        with open(summary_txt_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)

        # Save summary as DOCX file
        summary_docx_path = f"./oppsummeringer/{filnavn}_ai_sammendrag.docx"
        doc = Document()

        # Split text into paragraphs for better formatting
        paragraphs = summary_text.split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())

        doc.save(summary_docx_path)

        logger.info(f"AI summary saved to {summary_txt_path} and {summary_docx_path}")

        return {
            'txt': summary_txt_path,
            'docx': summary_docx_path
        }

    except Exception as e:
        logger.error(f"Error creating AI summary: {str(e)}")
        return {}


def sendNotificationWithSummary(upn: str, transcribed_files: dict, summary_files: dict, original_blob_name: str) -> bool:
    """
    Send email notification with SharePoint download links for both transcription and AI summary

    Args:
        upn: User Principal Name (email) of the recipient
        transcribed_files: Dict with transcription file paths {'docx': 'path/to/file.docx'}
        summary_files: Dict with AI summary file paths {'docx': 'path/to/summary.docx'} (can be empty)
        original_blob_name: Original blob filename for unique naming

    Returns:
        bool: True if email notification sent successfully
    """
    if not upn:
        logger.error("UPN er påkrevd for sendNotificationWithSummary")
        raise ValueError("UPN er påkrevd")

    if not transcribed_files.get('docx'):
        logger.error("DOCX-fil er påkrevd for sendNotificationWithSummary")
        raise ValueError("DOCX-fil er påkrevd")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = os.path.splitext(original_blob_name)[0]

        # Upload transcription file
        trans_unique_filename = f"{base_filename}_transkripsjon_{timestamp}.docx"
        logger.info(f"Laster opp transkripsjon til SharePoint med navn: {trans_unique_filename}")

        os.makedirs("./dokumenter", exist_ok=True)
        trans_temp_path = f"./dokumenter/{trans_unique_filename}"

        import shutil
        shutil.copy2(transcribed_files['docx'], trans_temp_path)

        transcription_url = _upload_to_sharepoint_custom(upn, trans_temp_path)

        if os.path.exists(trans_temp_path):
            os.remove(trans_temp_path)

        if not transcription_url:
            logger.error("SharePoint opplasting av transkripsjon feilet")
            return False

        # Upload AI summary file if available
        summary_url = None
        if summary_files.get('docx') and os.path.exists(summary_files['docx']):
            summary_unique_filename = f"{base_filename}_sammendrag_{timestamp}.docx"
            logger.info(f"Laster opp AI-sammendrag til SharePoint med navn: {summary_unique_filename}")

            summary_temp_path = f"./dokumenter/{summary_unique_filename}"
            shutil.copy2(summary_files['docx'], summary_temp_path)

            summary_url = _upload_to_sharepoint_custom(upn, summary_temp_path)

            if os.path.exists(summary_temp_path):
                os.remove(summary_temp_path)

            if summary_url:
                logger.info(f"SharePoint opplasting av sammendrag vellykket: {summary_url}")
            else:
                logger.warning("SharePoint opplasting av sammendrag feilet - fortsetter uten sammendrag")

        # Create email notification message with download links
        email_message = f"""Hei,

Din transkripsjonsjobb er nå ferdig behandlet.

TRANSKRIPSJON:
Du kan laste ned den transkriberte filen ved å klikke på lenken nedenfor:
{transcription_url}"""

        if summary_url:
            email_message += f"""

AI-SAMMENDRAG:
Du kan også laste ned et AI-generert sammendrag av møtet:
{summary_url}"""

        email_message += """

Filene er lagret trygt i SharePoint og kun du har tilgang til dem.

VIKTIG PERSONVERNHENSYN:
Vær forsiktig med hvordan du bruker transkripsjonen videre i andre tjenester. Dersom transkripsjonen inneholder personopplysninger, må du følge gjeldende personvernregler og kun dele informasjonen med personer som har et tjenstlig behov for den.

Takk for at du bruker transkripsjonstjenesten i Hugin.

Med vennlig hilsen
Hugin Transkripsjonstjeneste
Telemark Fylkeskommune"""

        # Send email notification using Graph API
        logger.info(f"Sender e-post via Graph API til {upn} med lenker")
        email_subject = "Transkripsjon ferdig" + (" (med AI-sammendrag)" if summary_url else "") + " - Hugin"
        email_success = _send_email_graph(upn, email_subject, email_message)

        if email_success:
            logger.info(f"E-post med SharePoint-lenker sendt til {upn}")
        else:
            logger.error(f"E-post sending feilet for {upn}")

        return email_success

    except Exception as e:
        logger.error(f"sendNotificationWithSummary feilet for {upn}: {e}")
        # Send error notification as fallback
        error_message = """Hei,

Din transkripsjonsjobb er ferdig behandlet, men det oppstod et teknisk problem med å laste opp filen til SharePoint.

Vennligst kontakt support for assistanse med å hente din transkriberte fil.

Vi beklager uleiligheten.

Med vennlig hilsen
Hugin Transkripsjonstjeneste
Telemark Fylkeskommune"""
        _send_error_notification(upn, error_message)
        return False


def sendNotification(upn: str, transcribed_files: dict, original_blob_name: str) -> bool:
    """
    Send email notification with SharePoint download link
    
    Args:
        upn: User Principal Name (email) of the recipient
        transcribed_files: Dict with file paths {'docx': 'path/to/file.docx'}
        original_blob_name: Original blob filename for unique naming
    
    Returns:
        bool: True if email notification sent successfully
    """
    if not upn:
        logger.error("UPN er påkrevd for sendNotification")
        raise ValueError("UPN er påkrevd")
    
    if not transcribed_files.get('docx'):
        logger.error("DOCX-fil er påkrevd for sendNotification")
        raise ValueError("DOCX-fil er påkrevd")
    
    try:
        # Generate unique filename using original blob name + timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = os.path.splitext(original_blob_name)[0]
        unique_filename = f"{base_filename}_{timestamp}.docx"
        
        logger.info(f"Laster opp transkripsjon til SharePoint med navn: {unique_filename}")
        
        # Temporarily copy the docx file with unique filename for SharePoint upload
        docx_file_path = transcribed_files['docx']
        temp_upload_path = f"./dokumenter/{unique_filename}"  # Use unique filename
        
        # Create dokumenter directory if it doesn't exist
        os.makedirs("./dokumenter", exist_ok=True)
        
        # Copy the docx file to the expected path temporarily with unique name
        import shutil
        shutil.copy2(docx_file_path, temp_upload_path)
        
        # Upload to SharePoint with custom filename
        sharepoint_url = _upload_to_sharepoint_custom(upn, temp_upload_path)
        
        # Clean up temporary file
        if os.path.exists(temp_upload_path):
            os.remove(temp_upload_path)
        
        if not sharepoint_url:
            logger.error("SharePoint opplasting feilet")
            # Send error notification
            error_message = """Hei,

Din transkripsjonsjobb er ferdig behandlet, men det oppstod et teknisk problem med å laste opp filen til SharePoint.

Vennligst kontakt support for assistanse med å hente din transkriberte fil.

Vi beklager uleiligheten.

Med vennlig hilsen
Hugin Transkripsjonstjeneste
Telemark Fylkeskommune"""
            _send_error_notification(upn, error_message)
            return False
        
        logger.info(f"SharePoint opplasting vellykket: {sharepoint_url}")
        logger.info(f"Fil lastet opp med navn: {unique_filename}")
        
        # Create email notification message with download link
        email_message = f"""Hei,

Din transkripsjonsjobb er nå ferdig behandlet.

Du kan laste ned den transkriberte filen ved å klikke på lenken nedenfor:
{sharepoint_url}

Filen er lagret trygt i SharePoint og kun du har tilgang til den.

VIKTIG PERSONVERNHENSYN:
Vær forsiktig med hvordan du bruker transkripsjonen videre i andre tjenester. Dersom transkripsjonen inneholder personopplysninger, må du følge gjeldende personvernregler og kun dele informasjonen med personer som har et tjenstlig behov for den.

Takk for at du bruker transkripsjonstjenesten i Hugin.

Med vennlig hilsen
Hugin Transkripsjonstjeneste
Telemark Fylkeskommune"""

        # Send email notification using Graph API
        logger.info(f"Sender e-post via Graph API til {upn} med SharePoint URL: {sharepoint_url}")
        email_subject = "Transkripsjon ferdig - Hugin"
        email_success = _send_email_graph(upn, email_subject, email_message)
        
        if email_success:
            logger.info(f"E-post med SharePoint-lenke sendt til {upn}")
        else:
            logger.error(f"E-post sending feilet for {upn}")
        
        return email_success
        
    except Exception as e:
        logger.error(f"sendNotification feilet for {upn}: {e}")
        # Send error notification as fallback
        error_message = """Hei,

Din transkripsjonsjobb er ferdig behandlet, men det oppstod et teknisk problem med å laste opp filen til SharePoint.

Vennligst kontakt support for assistanse med å hente din transkriberte fil.

Vi beklager uleiligheten.

Med vennlig hilsen
Hugin Transkripsjonstjeneste
Telemark Fylkeskommune"""
        _send_error_notification(upn, error_message)
        return False

def _send_error_notification(upn: str, error_message: str):
    """Send a simple error notification via email using Graph API"""
    try:
        error_subject = "Transkripsjonsfeil - Hugin"
        success = _send_email_graph(upn, error_subject, error_message)
        if success:
            logger.info(f"Feilmelding sendt via e-post til {upn}")
        else:
            logger.error(f"Kunne ikke sende feilmelding via e-post til {upn}")
        
    except Exception as e:
        logger.error(f"Kunne ikke sende feilmelding til {upn}: {e}")

def _upload_to_sharepoint_custom(upn: str, file_path: str) -> str:
    """
    Custom SharePoint upload function that uses the provided file path and filename
    Upload files to SharePoint with custom file path support
    """
    SHAREPOINT_SITE_URL = os.getenv('SHAREPOINT_SITE_URL')
    DEFAULT_LIBRARY = os.getenv('DEFAULT_LIBRARY', 'Documents')
    GRAPH_URL = "https://graph.microsoft.com/v1.0"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    try:
        # Get authentication token
        token = hentToken()
        if not token:
            return None
        
        # Get site ID
        parts = SHAREPOINT_SITE_URL.replace('https://', '').split('/')
        hostname = parts[0]
        site_path = '/'.join(parts[1:])
        
        headers = {'Authorization': f'Bearer {token}'}
        url = f"{GRAPH_URL}/sites/{hostname}:/{site_path}"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        site_id = response.json()['id']
        
        if not site_id:
            logger.error("Could not get SharePoint site ID")
            return None
        
        # Get document library
        drives_url = f"{GRAPH_URL}/sites/{site_id}/drives"
        drives_response = requests.get(drives_url, headers=headers)
        drives_response.raise_for_status()
        
        # Find the specified document library
        drives = drives_response.json()['value']
        drive_id = None
        for drive in drives:
            if drive['name'] == DEFAULT_LIBRARY:
                drive_id = drive['id']
                break
        
        if not drive_id:
            logger.error(f"Could not find '{DEFAULT_LIBRARY}' document library")
            return None
        
        # Upload file with the exact filename from file_path
        file_name = os.path.basename(file_path)
        upload_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/octet-stream'
        }
        
        upload_url = f"{GRAPH_URL}/sites/{site_id}/drives/{drive_id}/root:/{file_name}:/content"
        
        with open(file_path, 'rb') as f:
            response = requests.put(upload_url, headers=upload_headers, data=f)
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"Successfully uploaded to SharePoint: {file_name}")
        
        # Set exclusive permissions for the specified UPN
        file_id = result['id']
        permission_data = {
            'recipients': [{'email': upn}],
            'roles': ['read'],
            'requireSignIn': True,
            'sendInvitation': False
        }
        
        invite_url = f"{GRAPH_URL}/sites/{site_id}/drives/{drive_id}/items/{file_id}/invite"
        permission_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        invite_response = requests.post(invite_url, headers=permission_headers, json=permission_data)
        
        if invite_response.status_code in [200, 201]:
            logger.info(f"Granted exclusive access to: {upn}")
        else:
            logger.warning(f"Permission grant may have failed: {invite_response.status_code}")
        
        # Generate a secure sharing link
        sharing_data = {
            'type': 'view',
            'scope': 'users'  # Only users with permissions can access
        }
        
        link_url = f"{GRAPH_URL}/sites/{site_id}/drives/{drive_id}/items/{file_id}/createLink"
        response = requests.post(link_url, headers=permission_headers, json=sharing_data)
        
        if response.status_code in [200, 201]:
            sharing_link = response.json()['link']['webUrl']
            logger.info("Secure sharing link created successfully")
            return sharing_link
        else:
            logger.warning(f"Sharing link creation failed: {response.status_code}, using direct URL")
            return result['webUrl']
        
    except Exception as e:
        logger.error(f"SharePoint upload failed: {e}")
        return None


def _send_email_graph(upn: str, subject: str, message: str) -> bool:
    """
    Send email using Microsoft Graph API directly
    """
    try:
        # Get authentication token
        token = hentToken()
        if not token:
            logger.error("Could not get Graph API token for email")
            return False
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Send email
        email_payload = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': 'Text',
                    'content': message
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': upn
                        }
                    }
                ]
            }
        }
        
        # Use application permissions to send mail
        email_url = f"https://graph.microsoft.com/v1.0/users/{upn}/sendMail"
        email_response = requests.post(email_url, headers=headers, json=email_payload)
        
        if email_response.status_code == 202:
            logger.info(f"Email sent via Graph API to {upn}")
            return True
        else:
            logger.error(f"Failed to send email via Graph API: {email_response.status_code} - {email_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send email via Graph API to {upn}: {e}")
        return False