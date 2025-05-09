import os, dotenv
import ffmpeg
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from transformers import pipeline
import json
from datetime import datetime, timedelta
from openai import OpenAI
import pprint as pp
from docx import Document
import requests

dotenv.load_dotenv()
MAIL_API_URL = os.getenv("MAIL_API_URL")
MAIL_API_KEY = os.getenv("MAIL_API_KEY")
LOGIC_APP_CHAT_URL = os.getenv("LOGIC_APP_CHAT_URL")

import warnings
warnings.filterwarnings("ignore")

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
        json_tekst = asr(sti + filnavn, chunk_length_s=28, return_timestamps=True, generate_kwargs={'num_beams': 5, 'language': 'no'})

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

        # Skriver til SRT-fil
        with open(f"./ferdig_tekst/{filnavn.split('.')[0]}.srt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_data))
        
        # Skriver til tekstfil
        with open(f"./ferdig_tekst/{filnavn.split('.')[0]}.txt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(tekst_data))
        

        print(f'Transkripsjonen er lagret i ./ferdig_tekst/{filnavn}')

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

    # Write to markdown file
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

    # Skriv for hvert element i ren_tekst skriv en ny linje i en docx-fil
    with open("./oppsummeringer/" + filnavn.split(".")[0] + ".txt", 'w', encoding='utf-8') as f:
        f.write("".join(ren_tekst))

# Sender oppsummering på epost
def send_email(recipient, attachment=None):
    payload = {
        "to": [recipient],
        "from": "Hugin - Transkripsjonsbotten <ikke-svar@huginbotten.no>",
        "subject": "Transkribering",
        "text": "Hei! Her er en oppsummering av transkriberingen.",
        "html": "<b>Hei!</b><p>Her er en oppsummering av transkriberingen.</p>",
        "attachments": [
            {
                "content": attachment,
                "filename": "transkripsjon.txt",
                "type": "application/json"
            }
        ]
    }

    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0',
        'x-functions-key': MAIL_API_KEY
    }

    response = requests.post(MAIL_API_URL, headers=headers, data=json.dumps(payload))
    print(response)

# ToDo: Send transkribering som chat i teams til innlogget bruker
def sendTeamsChat(recipient, base64file=None):

    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    payload = {
        "UPN": recipient,
        "base64": base64file
    }

    # Send https request til teams
    req = requests.post(LOGIC_APP_CHAT_URL, headers=headers, data=json.dumps(payload))
    print(req)    