import os
import logging
import time

# Ensure ffmpeg is in PATH
os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')

import ffmpeg
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from transformers import pipeline
import json
from datetime import datetime, timedelta
from openai import OpenAI
from docx import Document
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import dotenv
from .transkripsjon_sp_lib import hentToken

dotenv.load_dotenv()
LOGIC_APP_CHAT_URL = os.getenv("LOGIC_APP_CHAT_URL")

import warnings
warnings.filterwarnings("ignore")

# Konfigurer logging
logger = logging.getLogger(__name__)

def create_requests_session():
    """Opprett en requests session med retry-strategi og timeout"""
    session = requests.Session()
    
    # Bruk riktig parameter navn for kompatibilitet med nye urllib3 versjoner
    try:
        # Prøv først nye parameter navn (urllib3 >=1.26)
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "DELETE"],
            backoff_factor=1
        )
    except TypeError:
        # Fall tilbake til gamle parameter navn (urllib3 <1.26)
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "POST", "DELETE"],
            backoff_factor=1
        )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

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
    stream = ffmpeg.input(filnavn)
    stream = ffmpeg.output(stream, nytt_filnavn)
    ffmpeg.input(filnavn).output(nytt_filnavn, acodec='libmp3lame', format='mp3').run()
    # ffmpeg.run(stream, overwrite_output=True)
    print(f'Konvertering ferdig. Lydfilen er lagret som {nytt_filnavn}')

# Transkriber blob og lagrer i SRT-fil
def transkriber(sti, filnavn):
     # Laster inn KI-modellen fra Huggingface
        asr = pipeline("automatic-speech-recognition", "NbAiLab/nb-whisper-medium", device="mps") # Sett device='cuda' eller device='cpu' om ønskelig

        # Transkriberer lydfilen til tekst i JSON-format
        print(f'Transkriberer lyd fra {filnavn} til tekst. Obs: Dette er en tidkrevende prosess.')
        json_tekst = asr(sti + filnavn, chunk_length_s=28, return_timestamps=True, generate_kwargs={'language': 'no'})

        # Laster inn JSON-dataen
        data = json_tekst
        srt_data = []
        tekst_data = []
 
        # Looper over JSON-rådataen og formaterer den til SRT- og tekst-format
        for i, item in enumerate(data["chunks"], start=1):
            start_time = datetime.fromtimestamp(item['timestamp'][0]) - timedelta(hours=1)
            end_time = datetime.fromtimestamp(item['timestamp'][1]) - timedelta(hours=1) if item['timestamp'][1] is not None else start_time

            start_time_str = start_time.strftime('%H:%M:%S,%f')[:-3]
            end_time_str = end_time.strftime('%H:%M:%S,%f')[:-3]

            # Lager SRT-strengen og legger den til i listen
            srt_string = f"{i}\n{start_time_str} --> {end_time_str}\n{item['text']}\n"
            srt_data.append(srt_string)

            # Lager tekststrengen og legger den til i listen
            tekst_data.append(f"{item['text']}\n")

        # Sørg for at utdata-mappe eksisterer
        os.makedirs("./ferdig_tekst", exist_ok=True)
        
        # Skriver til SRT-fil
        with open(f"./ferdig_tekst/{filnavn.split('.')[0]}.srt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_data))
        
        # Skriver til tekstfil
        with open(f"./ferdig_tekst/{filnavn.split('.')[0]}.txt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(tekst_data))
        

        print(f'Transkripsjonen er lagret i ./ferdig_tekst/{filnavn.split(".")[0]}.srt og .txt')

# Lag oppsummeringer
def oppsummering(sti, filnavn, språk, format):
    client = OpenAI()
    # Importer srt-fil og legg innholdet i en variabel som heter tekst
    undertekstfil = sti + filnavn + ".srt"
    tekst = ""
    if språk == "":
        språk = "norsk"
    else:
        språk = språk
    if format == "":
        format = "oppsummering"
    else:
        format = format

    oppsummering = filnavn

    with open(undertekstfil, "r") as file:
        tekst = file.read()

    # Systeminstruksjoner
    systeminstruksjon_oppsummering = "Brukeren legger inn en tekst som er en transkripsjon av et møte eller foredrag. Teksten er formatert som en srt-undertekstfil. Din oppgave er å lage et korrekt og nøyaktig referat av innholdet. Følg disse instruksene: 1. Det er viktig at oppsummeringen er helt riktig. 2. Skriv overskrifter når det er nytt tema. 3. Oppsummeringen skal være fyldig og beskrive hva det ble snakket om. 4. Oversett eller forklar forkortelser og fagbegreper når disse er vanskelige. 5. Bruk et klart og tydelig språk som er lett å forstå. 6. Oppsummeringen skal være på ca 1500 ord. 7. Oppsummeringen skal være på markdown-format. 8. Oppsummeringen skal være på " + språk + ". 9. Viktig: Formen på oppsummeringen skal være på formatet:" + format + ". Her er srt-filen:"
    
    systeminstruksjon_moteref = "Du har fått i oppgave å lage et møtereferat fra en SRT-fil som inneholder tekstutskrift med tidsmerker fra et møte. Her er instruksjonene for å lage et effektivt og nøyaktig referat: Tidsmerker: Ignorer de eksakte tidsmerkene, men bruk dem som referanse for å identifisere skift i topics eller start/slutt på ulike diskusjonspunkter. Identifisering: Forsøk å identifisere forskjellige stemmer/talere dersom det er mulig, og tilordne kommentarer til riktig person. Bruk generelle beskrivelser som 'Leder', 'Deltaker 1', med mindre det er spesifikke navn. Konsistens: Oppsummer lange diskusjoner kortfattet, men behold alle viktige detaljer og beslutninger. Utelat fyllstoff som ikke påvirker forståelsen av møtet. Struktur: Organiser referatet i seksjoner basert på møteagendaen, hvis tilgjengelig. Hvis ikke, del inn i logiske seksjoner som diskuterer forskjellige emner. Beslutninger og Oppfølging: Sørg for at alle beslutninger, oppfølgingspunkter, og ansvarlige personer er tydelig notert. Språk: Sikre at språket er klart og profesjonelt, hvor teknisk terminologi er forklart eller utdypet dersom det kan bli misforstått. Du skal aldri skrive noe som ikke er sagt i møtet! Det er veldig viktig at du kune skriver ting som er sagt i møtet. Vennligst les gjennom SRT-filen og lag et møtereferat som følger disse retningslinjene. Møtereferatet skal være på " + språk + ". Her er SRT-filen:"

    systeminstruksjon = ""
    if format == "motereferat":
        systeminstruksjon = systeminstruksjon_moteref
    else:
        systeminstruksjon = systeminstruksjon_oppsummering

    completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": systeminstruksjon},
        {"role": "user", "content": tekst}
    ]
    )

    # Sørg for at utdata-mappe eksisterer
    os.makedirs("./oppsummeringer", exist_ok=True)
    
    # Skriv til markdown-fil
    with open("./oppsummeringer/" + oppsummering + ".md", "w") as file:
        file.write(completion.choices[0].message.content)

    # Skriv til docx-fil
    doc = Document()
    doc.add_paragraph(completion.choices[0].message.content)
    doc.save("./oppsummeringer/" + oppsummering + ".docx")

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

# Sender e-post via Logic App
def send_email(recipient, attachment=None):
    """Send e-post med transkripsjon via Logic App"""
    if not LOGIC_APP_CHAT_URL:
        logger.error("LOGIC_APP_CHAT_URL ikke konfigurert")
        raise ValueError("LOGIC_APP_CHAT_URL ikke konfigurert")
    
    if not recipient:
        logger.error("Mottaker UPN er påkrevd")
        raise ValueError("Mottaker UPN er påkrevd")

    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    # E-post melding med vedlegg
    email_message = "Takk for at du har brukt transkripsjonstjenesten i Hugin. Vedlagt finner du den fullstendige transkripsjonen av din fil."
    
    payload = {
        "UPN": recipient,
        "message": email_message,
        "type": "email"  # Indikerer at dette er en e-post forespørsel
    }
    
    # Kun inkluder base64 hvis det faktisk finnes innhold
    if attachment:
        payload["base64"] = attachment

    session = create_requests_session()
    try:
        logger.info(f"Sender e-post via Logic App til {recipient}")
        response = session.post(LOGIC_APP_CHAT_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        logger.info(f"E-post sendt til {recipient} (status: {response.status_code})")
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Kunne ikke sende e-post til {recipient}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}, Response text: {e.response.text[:200]}")
        raise

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
            error_message = "Din transkripsjonsjobb er ferdig, men det oppstod et problem med å laste opp filen til SharePoint. Kontakt support for assistanse."
            _send_error_notification(upn, error_message)
            return False
        
        logger.info(f"SharePoint opplasting vellykket: {sharepoint_url}")
        logger.info(f"Fil lastet opp med navn: {unique_filename}")
        
        # Create email notification message with download link
        email_message = f"Takk for at du har brukt transkripsjonstjenesten i Hugin. Din transkripsjon er ferdig og kan lastes ned fra SharePoint: {sharepoint_url}"

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
        error_message = "Din transkripsjonsjobb er ferdig, men det oppstod et teknisk problem med å laste opp til SharePoint. Kontakt support for assistanse."
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
    Based on the original lastOppTilSP function but with custom file path support
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