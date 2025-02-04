# Download file from azure blob storage
import os, dotenv
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import ffmpeg, os
from transformers import pipeline
import json
from datetime import datetime, timedelta
from openai import OpenAI
import pprint as pp
from docx import Document
import os, requests
import base64

from lib import hugintranskriptlib as htl

dotenv.load_dotenv()
client = OpenAI()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
GRAPH_JWT_TOKEN = os.getenv("GRAPH_JWT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
filnavn = []
metadata = []

# Transkriber blob og lagrer i SRT-fil
def transkriber(sti, filnavn):
     # Laster inn KI-modellen fra Huggingface
        asr = pipeline("automatic-speech-recognition", "NbAiLab/nb-whisper-medium") # Sett device='cuda' eller device='cpu' om ønskelig

        # Transkriberer lydfilen til tekst i JSON-format
        print(f'Transkriberer lyd fra {filnavn} til tekst. Obs: Dette er en tidkrevende prosess.')
        json_tekst = asr(sti + filnavn, chunk_length_s=28, return_timestamps=True, generate_kwargs={'num_beams': 5, 'task': 'transcribe', 'language': 'no'})

        # Laster inn JSON-dataen
        data = json_tekst
        srt_data = []
        srt_data_vasket = []
        hallusinasjonSjekk = False
 
        # Looper over JSON-rådataen og formaterer den til SRT-format
        for i, item in enumerate(data["chunks"], start=1):
            start_time = datetime.fromtimestamp(item['timestamp'][0]) - timedelta(hours=1)
            end_time = datetime.fromtimestamp(item['timestamp'][1]) - timedelta(hours=1) if item['timestamp'][1] is not None else start_time

            start_time_str = start_time.strftime('%H:%M:%S,%f')[:-3]
            end_time_str = end_time.strftime('%H:%M:%S,%f')[:-3]

            # Lager SRT-strengen og legger den til i listen
            srt_string = f"{i}\n{start_time_str} --> {end_time_str}\n{item['text']}\n"
            srt_data.append(srt_string)

        # Enkel Sjekk om det er hallusinasjoner i teksten og fjerner disse (Sånn passe bra)
        for i in range(1, len(srt_data)):
            if srt_data[i].split('\n')[2] == srt_data[i-1].split('\n')[2]:
                hallusinasjonSjekk = True
                # srt_data_vasket.append("x")
            elif hallusinasjonSjekk:
                hallusinasjonSjekk = False
                # srt_data_vasket.append("x")
            else:
                srt_data_vasket.append(srt_data[i-1])
            
        print(srt_data[0].split('\n')[2])
        # Skriver til SRT-fil
        with open(f"./ferdig_tekst/{filnavn}.srt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_data_vasket))
        with open('raw.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        print(f'Transkripsjonen er lagret i ./ferdig_tekst/{filnavn}.srt')

# Lag oppsummeringer
def oppsummering(sti, filnavn, metadata):
    # Importer srt-fil og legg innholdet i en variabel som heter tekst
    undertekstfil = sti + filnavn + ".srt"
    tekst = ""
    språk = metadata["spraak"]
    oppsummering = filnavn

    with open(undertekstfil, "r") as file:
        tekst = file.read()

    # Systeminstruksjon
    systeminstruksjon = "Brukeren legger inn en tekst som er en transkripsjon av et møte eller foredrag. Teksten er formater som en srt-undertekstfil. Din oppgave er å lage et korrekt og nøyaktig referat av innholdet. Følg disse instruksene: 1. Det er viktig at oppsummeringen er helt riktig. 2. Skriv overskrifter når det er nytt tema. 3. Oppsummeringen skal være fyldig og beskrive hva det ble snakket om. 4. Oversett eller forklar forkortelser og fagbegreper når disse er vanskelige. 5. Bruk et klart og tydelig språk som er lett å forstå. 6. Oppsummeringen skal være på ca 1500 ord. 7. Oppsummeringen skal være på markdown-format. 8. Oppsummeringen skal være på " + språk + "."

    completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": systeminstruksjon},
        {"role": "user", "content": tekst}
    ]
    )

    pp.pprint(completion.choices[0].message.content)

    # Write to markdown file
    with open("./oppsummeringer/" + oppsummering + ".md", "w") as file:
        file.write(completion.choices[0].message.content)

    # Skriv til docx-fil
    doc = Document()
    doc.add_paragraph(completion.choices[0].message.content)
    doc.save("./oppsummeringer/" + oppsummering + ".docx")

filnavn = htl.list_blobs(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME)
print("\n-----------------------------")
for i in range(len(filnavn)):
    print("\n-----------------------------")
    print(f"Blob {i}: {filnavn[i]}")
    metadata.append(htl.get_blob_metadata(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i]))
    htl.download_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i], "./blobber/" + filnavn[i])
    htl.delete_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i])
    transkriber("./blobber/", filnavn[i])
    oppsummering("./ferdig_tekst/", filnavn[i], metadata[i])

    # Ecode the file to base64
    with open(f"./oppsummeringer/{filnavn[i]}.md" , "rb") as file:
        base64file = base64.b64encode(file.read()).decode('utf-8')
    
    htl.send_email(GRAPH_JWT_TOKEN, "fuzzbin@gmail.com", "Oppsummering", "Hei og hadet", base64file)

        # Delete file from local storage
    os.remove(f"./blobber/{filnavn[i]}")
    os.remove(f"./ferdig_tekst/{filnavn[i]}.srt")
    os.remove(f"./oppsummeringer/{filnavn[i]}.md")
    os.remove(f"./oppsummeringer/{filnavn[i]}.docx")