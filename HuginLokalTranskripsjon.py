import os
import sys
import time
import base64
import logging
import re
import warnings
import dotenv
from docx import Document

# Ignorer advarsler
warnings.filterwarnings("ignore")

from lib import hugintranskriptlib as htl

# Sørg for at logs-mappen eksisterer
os.makedirs("./logs", exist_ok=True)

# Konfigurer logging med riktig format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/hugintranskripsjonslog.txt', encoding='utf-8'),
        logging.FileHandler('hugin_transcription.log', encoding='utf-8'),  # Backward compatibility
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
        "AZURE_STORAGE_CONTAINER_NAME"
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


# Hent validerte miljøvariabler
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

try:
    logger.info("=" * 80)
    logger.info("🚀 STARTER HUGIN TRANSKRIPSJONSTJENESTE")
    logger.info(f"Tjeneste startet på: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Sørg for at påkrevde mapper eksisterer
    os.makedirs("./blobber", exist_ok=True)
    os.makedirs("./ferdig_tekst", exist_ok=True)
    os.makedirs("./oppsummeringer", exist_ok=True)
    logger.info("✅ Påkrevde mapper opprettet/verifisert (blobber, ferdig_tekst, oppsummeringer)")
    
    # Hent blob-liste
    try:
        logger.info("🔍 Sjekker Azure Blob Storage for nye filer...")
        filnavn = htl.list_blobs(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME)
        logger.info(f"📁 Fant {len(filnavn)} filer å behandle")
        if filnavn:
            logger.info(f"📋 Filer funnet: {', '.join(filnavn)}")
    except Exception as e:
        logger.error(f"❌ Kunne ikke liste filer fra Azure Storage: {e}")
        raise
    
    if not filnavn:
        logger.info("ℹ️  Ingen filer funnet for behandling - avslutter")
        logger.info("=" * 80)
        sys.exit(0)
    
    metadata = []

    # Nedlastingsfase - med individuell feilhåndtering
    logger.info("⬇️  STARTER NEDLASTINGSFASE")
    logger.info("-" * 50)
    
    for i, filename in enumerate(filnavn, 1):
        try:
            # Rens filnavn
            safe_filename = sanitize_filename(filename)
            logger.info(f"📥 [{i}/{len(filnavn)}] Behandler fil: {safe_filename}")
            
            # Hent metadata
            logger.info(f"📋 Henter metadata for {safe_filename}")
            file_metadata = htl.get_blob_metadata(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filename)
            metadata.append(file_metadata)
            
            if 'upn' in file_metadata:
                logger.info(f"👤 Bruker: {file_metadata['upn']}")
            
            # Last ned blob
            download_path = f"./blobber/{safe_filename}"
            logger.info(f"⬇️  Laster ned til: {download_path}")
            htl.download_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filename, download_path)
            logger.info(f"✅ Nedlasting fullført: {safe_filename}")
            
            # Slett fra blob-lagring
            htl.delete_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filename)
            logger.info(f"🗑️  Slettet fra Azure Storage: {safe_filename}")
            
        except Exception as e:
            logger.error(f"❌ Kunne ikke behandle fil {filename}: {e}")
            continue

    # Behandlingsfase - med individuell feilhåndtering
    logger.info("")
    logger.info("🔄 STARTER BEHANDLINGSFASE")
    logger.info("-" * 50)
    
    successful_files = []
    for i, filename in enumerate(filnavn, 1):
        try:
            safe_filename = sanitize_filename(filename)
            file_extension = get_file_extension(safe_filename)
            
            logger.info(f"🔄 [{i}/{len(filnavn)}] Behandler fil: {safe_filename}")
            
            if not file_extension:
                logger.warning(f"⚠️  Hopper over fil uten filtype: {safe_filename}")
                continue
            
            logger.info(f"📄 Filtype: {file_extension}")
            
            # Sjekk om filen eksisterer lokalt
            local_file_path = f"./blobber/{safe_filename}"
            if not os.path.exists(local_file_path):
                logger.error(f"❌ Nedlastet fil ikke funnet: {local_file_path}")
                continue
            
            file_size = os.path.getsize(local_file_path)
            logger.info(f"📊 Filstørrelse: {file_size/1024/1024:.1f} MB")
            
            # Konverter video til lyd hvis nødvendig
            transcription_filename = safe_filename
            if file_extension in ["mp4", "mov", "avi", "m4a"]:
                logger.info(f"🎬 Media-fil oppdaget - konverterer til lyd...")
                base_name = safe_filename.rsplit('.', 1)[0]
                audio_path = f"./blobber/{base_name}.wav"
                htl.konverter_til_lyd(local_file_path, audio_path)
                transcription_filename = f"{base_name}.wav"
                logger.info(f"✅ Media konvertert til lyd: {transcription_filename}")
            
            # Transkriber
            logger.info(f"🎤 Starter transkripsjon med MLX...")
            start_time = time.time()
            htl.transkriber("./blobber/", transcription_filename)
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"✅ Transkripsjon fullført på {duration:.1f} sekunder")

            # Generer AI-sammendrag
            logger.info(f"🤖 Starter AI-sammendrag generering...")
            ai_summary_start = time.time()
            base_name = safe_filename.rsplit('.', 1)[0]
            summary_files = htl.create_ai_summary(base_name)
            ai_summary_duration = time.time() - ai_summary_start

            if summary_files:
                logger.info(f"✅ AI-sammendrag generert på {ai_summary_duration:.1f} sekunder")
                logger.info(f"📄 AI-sammendrag filer: {list(summary_files.keys())}")
            else:
                logger.warning(f"⚠️  AI-sammendrag ikke generert (Ollama ikke tilgjengelig eller feil)")

            # Konverter SRT til tekst kun hvis SRT-fil eksisterer
            base_name = safe_filename.rsplit('.', 1)[0]
            srt_file_path = f"./ferdig_tekst/{base_name}.srt"
            if os.path.exists(srt_file_path):
                logger.info(f"📝 Genererer ren tekst fra SRT-fil...")
                htl.srt_til_tekst(f"{base_name}.srt")
                logger.info(f"✅ Ren tekst generert: {base_name}.txt")
            else:
                logger.info(f"ℹ️  Hopper over SRT-til-tekst konvertering (ingen SRT-fil opprettet)")
            
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
            
            # Opprett docx-fil fra transkripsjonen
            transcribed_docx_path = f"./ferdig_tekst/{base_name}.docx"
            
            try:
                with open(txt_file_path, "r", encoding='utf-8') as file:
                    text = file.read()
                    doc = Document()
                    doc.add_paragraph(text)
                    doc.save(transcribed_docx_path)
                logger.info(f"✅ Opprettet DOCX-fil for transkripsjon: {base_name}.docx")
            except Exception as e:
                logger.error(f"❌ Kunne ikke opprette DOCX for transkripsjon {safe_filename}: {e}")
                continue
            
            # Send varsler med SharePoint nedlastingslenker
            logger.info("📧 Varsler med SharePoint-lenker...")
            try:
                if i-1 < len(metadata) and 'upn' in metadata[i-1]:
                    recipient = metadata[i-1]["upn"]
                    logger.info(f"📧 Varsler til: {recipient}")

                    # Opprett transcribed_files dict for sendNotification
                    transcribed_files = {
                        'docx': transcribed_docx_path
                    }

                    # Send varsler med SharePoint-lenker (inkludert AI-sammendrag hvis tilgjengelig)
                    success = htl.sendNotificationWithSummary(recipient, transcribed_files, summary_files, safe_filename)

                    if success:
                        summary_msg = " (med AI-sammendrag)" if summary_files else ""
                        logger.info(f"✅ Varsel med SharePoint-lenker sendt til {recipient}{summary_msg}")
                    else:
                        logger.error(f"❌ Kunne ikke sende varsel til {recipient}")
                else:
                    logger.warning(f"⚠️  Ingen bruker (UPN) funnet i metadata for {safe_filename}")
            except Exception as e:
                logger.error(f"❌ Kunne ikke sende varsel for {safe_filename}: {e}")
            
            # Rydd opp filer
            logger.info("🧹 Starter opprydding av midlertidige filer...")
            cleanup_files = [
                local_file_path,
                txt_file_path,
                transcribed_docx_path
            ]

            # Legg til AI-sammendrag filer for opprydding hvis de eksisterer
            if summary_files:
                if summary_files.get('txt'):
                    cleanup_files.append(summary_files['txt'])
                if summary_files.get('docx'):
                    cleanup_files.append(summary_files['docx'])
            
            # Rydd også opp SRT-filer hvis de eksisterer
            srt_file_path = f"./ferdig_tekst/{base_name}.srt"
            if os.path.exists(srt_file_path):
                cleanup_files.append(srt_file_path)
            
            # Rydd opp lydfiler hvis de ble opprettet
            if file_extension in ["mp4", "mov", "avi", "m4a"]:
                audio_file_path = f"./blobber/{base_name}.wav"
                if os.path.exists(audio_file_path):
                    cleanup_files.append(audio_file_path)
            
            cleaned_count = 0
            for file_path in cleanup_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.debug(f"🗑️  Fjernet: {file_path}")
                except Exception as e:
                    logger.error(f"❌ Kunne ikke fjerne fil {file_path}: {e}")
            
            logger.info(f"🧹 Opprydding fullført - fjernet {cleaned_count} filer")
            
            successful_files.append(safe_filename)
            logger.info(f"✅ FIL FULLFØRT: {safe_filename}")
            logger.info("-" * 30)
            
        except Exception as e:
            logger.error(f"❌ FEIL ved behandling av {filename}: {e}")
            continue
    
    # Avslutning og sammendrag
    logger.info("")
    logger.info("🏁 TRANSKRIPSJONSTJENESTE FULLFØRT")
    logger.info("=" * 80)
    logger.info(f"📊 SAMMENDRAG:")
    logger.info(f"   • Totalt filer funnet: {len(filnavn)}")
    logger.info(f"   • Filer behandlet vellykket: {len(successful_files)}")
    logger.info(f"   • Filer med feil: {len(filnavn) - len(successful_files)}")
    
    if successful_files:
        logger.info(f"✅ Vellykkede filer: {', '.join(successful_files)}")
    
    failed_files = [f for f in filnavn if sanitize_filename(f) not in successful_files]
    if failed_files:
        logger.info(f"❌ Feilede filer: {', '.join(failed_files)}")
    
    logger.info(f"⏰ Tjeneste avsluttet: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

except Exception as e:
    logger.error("💥 KRITISK FEIL I HUGIN TRANSKRIPSJONSTJENESTE")
    logger.error("=" * 80)
    logging.exception(f"Kritisk feil oppstod: {e}")
    logger.error("=" * 80)
