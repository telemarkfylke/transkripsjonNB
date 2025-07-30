import os
import sys
import time
import base64
import logging
import re
from openai import OpenAI
from docx import Document
import dotenv

# Ignorer advarsler
import warnings
warnings.filterwarnings("ignore")

from lib import hugintranskriptlib as htl

# Konfigurer logging med riktig format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hugin_transcription.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Reduser Azure logging støy
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def validate_environment():
    """Validerer at alle påkrevde miljøvariabler er satt"""
    required_vars = [
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER_NAME", 
        "OPENAI_API_KEY",
        "LOGIC_APP_CHAT_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Mangler påkrevde miljøvariabler: {', '.join(missing_vars)}")
        sys.exit(1)
    
    logger.info("Alle påkrevde miljøvariabler validert")

def sanitize_filename(filename):
    """Renser filnavn for å forhindre path traversal-angrep"""
    if not filename:
        raise ValueError("Filnavn kan ikke være tomt")
    
    # Fjern alle path-separatorer og farlige tegn
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized = os.path.basename(sanitized)
    
    # Forhindre directory traversal
    if '..' in sanitized or sanitized.startswith('.'):
        raise ValueError(f"Ugyldig filnavn: {filename}")
    
    return sanitized

def get_file_extension(filename):
    """Henter filtype med sikker grensesjekking"""
    if not filename or '.' not in filename:
        return None
    
    parts = filename.split('.')
    if len(parts) < 2:
        return None
    
    return parts[-1].lower()

# Last miljøvariabler
dotenv.load_dotenv()
validate_environment()

# Initialiser OpenAI klient
try:
    client = OpenAI()
    logger.info("OpenAI klient initialisert")
except Exception as e:
    logger.error(f"Kunne ikke initialisere OpenAI klient: {e}")
    sys.exit(1)

# Hent validerte miljøvariabler
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    logger.info("Starter transkripsjonstjeneste for HuginLokalTranskripsjon")
    
    # Sørg for at påkrevde mapper eksisterer
    os.makedirs("./blobber", exist_ok=True)
    os.makedirs("./ferdig_tekst", exist_ok=True)
    os.makedirs("./oppsummeringer", exist_ok=True)
    logger.info("Påkrevde mapper opprettet/verifisert")
    
    # Hent blob-liste
    try:
        filnavn = htl.list_blobs(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME)
        logger.info(f"Fant {len(filnavn)} filer å behandle")
    except Exception as e:
        logger.error(f"Kunne ikke liste filer: {e}")
        raise
    
    if not filnavn:
        logger.info("Ingen filer funnet for behandling")
        sys.exit(0)
    
    metadata = []

    # Nedlastingsfase - med individuell feilhåndtering
    for i, filename in enumerate(filnavn):
        try:
            # Rens filnavn
            safe_filename = sanitize_filename(filename)
            logger.info(f"Behandler fil {i}: {safe_filename}")
            
            # Hent metadata
            file_metadata = htl.get_blob_metadata(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filename)
            metadata.append(file_metadata)
            
            # Last ned blob
            download_path = f"./blobber/{safe_filename}"
            htl.download_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filename, download_path)
            logger.info(f"Lastet ned fil {safe_filename}")
            
            # Slett fra blob-lagring
            htl.delete_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filename)
            logger.info(f"Slettet fil {safe_filename} fra lagring")
            
        except Exception as e:
            logger.error(f"Kunne ikke behandle fil {filename}: {e}")
            continue

    # Behandlingsfase - med individuell feilhåndtering
    successful_files = []
    for i, filename in enumerate(filnavn):
        try:
            safe_filename = sanitize_filename(filename)
            file_extension = get_file_extension(safe_filename)
            
            if not file_extension:
                logger.warning(f"Hopper over fil uten filtype: {safe_filename}")
                continue
            
            # Sjekk om filen eksisterer lokalt
            local_file_path = f"./blobber/{safe_filename}"
            if not os.path.exists(local_file_path):
                logger.error(f"Nedlastet fil ikke funnet: {local_file_path}")
                continue
            
            logger.info(f"Behandler fil: {safe_filename}")
            
            # Konverter video til lyd hvis nødvendig
            if file_extension in ["mp4", "mov", "avi"]:
                base_name = safe_filename.rsplit('.', 1)[0]
                audio_path = f"./blobber/{base_name}.wav"
                htl.konverter_til_lyd(local_file_path, audio_path)
                logger.info(f"Konverterte {safe_filename} til lyd")
            
            # Transkriber
            htl.transkriber("./blobber/", safe_filename)
            logger.info(f"Transkriberte {safe_filename}")
            
            # Konverter SRT til tekst
            base_name = safe_filename.rsplit('.', 1)[0]
            htl.srt_til_tekst(f"{base_name}.srt")
            logger.info(f"Genererte ren tekst for {safe_filename}")
            
            # Kod fil til base64
            txt_file_path = f"./ferdig_tekst/{base_name}.txt"
            if not os.path.exists(txt_file_path):
                logger.error(f"Transkribert tekstfil ikke funnet: {txt_file_path}")
                continue
            
            # Sjekk filstørrelse før base64-koding
            try:
                file_size = os.path.getsize(txt_file_path)
                max_size = 20 * 1024 * 1024  # 20MB grense før base64-koding
                
                if file_size > max_size:
                    logger.warning(f"Tekstfil for stor ({file_size/1024/1024:.1f}MB). Sender uten vedlegg for {safe_filename}")
                    base64file = None
                else:
                    with open(txt_file_path, "rb") as file:
                        base64file = base64.b64encode(file.read()).decode('utf-8')
                        logger.info(f"Kodet {safe_filename} til base64 ({file_size/1024:.1f}KB)")
            except Exception as e:
                logger.error(f"Kunne ikke kode {safe_filename} til base64: {e}")
                base64file = None
            
            # Opprett docx-fil
            oppsummering_txt_path = f"./oppsummeringer/{base_name}.txt"
            oppsummering_docx_path = f"./oppsummeringer/{base_name}.docx"
            
            if os.path.exists(oppsummering_txt_path):
                try:
                    with open(oppsummering_txt_path, "r", encoding='utf-8') as file:
                        text = file.read()
                        doc = Document()
                        doc.add_paragraph(text)
                        doc.save(oppsummering_docx_path)
                    logger.info(f"Opprettet DOCX-fil for {safe_filename}")
                except Exception as e:
                    logger.error(f"Kunne ikke opprette DOCX for {safe_filename}: {e}")
            
            # Send e-post med fullstendig transkripsjon som vedlegg
            try:
                if i < len(metadata) and 'upn' in metadata[i]:
                    # Opprett e-post vedlegg fra tekstfil
                    email_attachment = None
                    if os.path.exists(txt_file_path):
                        with open(txt_file_path, "rb") as file:
                            email_attachment = base64.b64encode(file.read()).decode('utf-8')
                            logger.info(f"Opprettet e-post vedlegg for {safe_filename}")
                    
                    htl.send_email(metadata[i]["upn"], email_attachment)
                    logger.info(f"Sendte e-post med transkripsjon for {safe_filename} til {metadata[i]['upn']}")
                else:
                    logger.warning(f"Ingen UPN funnet i metadata for {safe_filename}")
            except Exception as e:
                logger.error(f"Kunne ikke sende e-post for {safe_filename}: {e}")
            
            # Send enkel statusmelding i Teams (kun varsel om ferdig jobb)
            #try:
            #    if i < len(metadata) and 'upn' in metadata[i]:
            #        response = htl.sendTeamsChat(metadata[i]["upn"], None)  # Alltid uten vedlegg eller transkripsjon
            #        logger.info(f"Sendte Teams-varsel om ferdig jobb for {safe_filename} til {metadata[i]['upn']}")
            #    else:
            #        logger.warning(f"Ingen UPN funnet i metadata for {safe_filename}")
            #except Exception as e:
            #    logger.error(f"Kunne ikke sende Teams-varsel for {safe_filename}: {e}")
            
            # Rydd opp filer
            cleanup_files = [
                local_file_path,
                txt_file_path,
                oppsummering_txt_path,
                oppsummering_docx_path
            ]
            
            # Rydd også opp SRT-filer
            srt_file_path = f"./ferdig_tekst/{base_name}.srt"
            if os.path.exists(srt_file_path):
                cleanup_files.append(srt_file_path)
            
            # Rydd opp lydfiler hvis de ble opprettet
            if file_extension in ["mp4", "mov", "avi"]:
                audio_file_path = f"./blobber/{base_name}.wav"
                if os.path.exists(audio_file_path):
                    cleanup_files.append(audio_file_path)
            
            for file_path in cleanup_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.debug(f"Fjernet fil: {file_path}")
                except Exception as e:
                    logger.error(f"Kunne ikke fjerne fil {file_path}: {e}")
            
            successful_files.append(safe_filename)
            logger.info(f"Behandlet {safe_filename} vellykket")
            
        except Exception as e:
            logger.error(f"Kunne ikke behandle fil {filename}: {e}")
            continue
    
    logger.info(f"Transkripsjonsjeneneste fullført. Behandlet {len(successful_files)} filer vellykket")

except Exception as e:
    logging.exception(f"En feil oppstod i HuginLokalTranskripsjon: {e}")
