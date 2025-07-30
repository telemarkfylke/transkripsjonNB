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

# Send transkribering som chat i teams til innlogget bruker
def sendTeamsChat(recipient, base64file=None):
    """Send transkripsjon via Teams-chat med retry og timeout"""
    if not LOGIC_APP_CHAT_URL:
        logger.error("LOGIC_APP_CHAT_URL ikke konfigurert")
        raise ValueError("LOGIC_APP_CHAT_URL ikke konfigurert")
    
    if not recipient:
        logger.error("Mottaker UPN er påkrevd")
        raise ValueError("Mottaker UPN er påkrevd")
    
    # Sjekk filstørrelse - Teams har begrensninger på meldingsstørrelse
    if base64file:
        # Base64 dekoding for å sjekke faktisk filstørrelse
        try:
            import base64
            decoded_size = len(base64.b64decode(base64file))
            max_size = 25 * 1024 * 1024  # 25MB grense for Teams
            
            if decoded_size > max_size:
                logger.warning(f"Fil for stor for Teams ({decoded_size/1024/1024:.1f}MB > {max_size/1024/1024}MB). Sender uten vedlegg.")
                base64file = None
        except Exception as e:
            logger.warning(f"Kunne ikke sjekke filstørrelse: {e}")
            base64file = None

    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    # Enkel statusmelding - ingen transkripsjon i Teams
    message = "Din transkripsjonsjobb er ferdig! Sjekk e-posten din for å få den fullstendige transkripsjonen."
    
    payload = {
        "UPN": recipient,
        "message": message,
        "type": "teams"  # Indikerer at dette er en Teams-melding
    }
    
    # Kun inkluder base64 hvis det faktisk finnes innhold
    if base64file:
        payload["base64"] = base64file

    session = create_requests_session()
    try:
        if base64file:
            logger.info(f"Sender Teams-melding med vedlegg til {recipient}")
        else:
            logger.info(f"Sender Teams-melding uten vedlegg til {recipient}")
            
        response = session.post(LOGIC_APP_CHAT_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        logger.info(f"Teams-melding sendt til {recipient} (status: {response.status_code})")
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Kunne ikke sende Teams-melding til {recipient}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}, Response text: {e.response.text[:200]}")
        raise     