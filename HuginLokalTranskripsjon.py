
import os, dotenv
import time
from openai import OpenAI
import pprint as pp
import base64
from docx import Document

import warnings
warnings.filterwarnings("ignore")

from lib import hugintranskriptlib as htl

dotenv.load_dotenv()
client = OpenAI()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 

print("Logging startet: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
filnavn = htl.list_blobs(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME)
metadata = []

for i in range(len(filnavn)):
    print(f"Blob {i}: {filnavn[i]}")
    metadata.append(htl.get_blob_metadata(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i]))
    htl.download_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i], "./blobber/" + filnavn[i])
    htl.delete_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i])

for i in range(len(filnavn)):
    if filnavn[i].split(".")[1] == "mp4" or filnavn[i].split(".")[1] == "mov" or filnavn[i].split(".")[1] == "avi":
        htl.konverter_til_lyd(f"./blobber/{filnavn[i]}", f"./blobber/{filnavn[i].split('.')[0]}.wav")
    htl.transkriber("./blobber/", filnavn[i])
    # htl.oppsummering("./ferdig_tekst/", filnavn[i], metadata[i]['spraak'] ,metadata[i]['format'])
    htl.srt_til_tekst(filnavn[i].split(".")[0] + ".srt")

    # Encode the file to base64
    with open(f"./ferdig_tekst/{filnavn[i].split('.')[0]}.txt" , "rb") as file:
       base64file = base64.b64encode(file.read()).decode('utf-8')

    # Convert and write to docx
    with open(f"./oppsummeringer/{filnavn[i].split('.')[0]}.txt", "r") as file:
       text = file.read()
       doc = Document()
       doc.add_paragraph(text)
       doc.save(f"./oppsummeringer/{filnavn[i].split('.')[0]}.docx")
       

    # Send mail
    htl.send_email(metadata[i]["upn"], base64file)

    # Delete file from local storage
    # os.remove(f"./blobber/{filnavn[i]}")
    os.remove(f"./ferdig_tekst/{filnavn[i].split('.')[0]}.srt")
    os.remove(f"./ferdig_tekst/{filnavn[i].split('.')[0]}.txt")
    os.remove(f"./oppsummeringer/{filnavn[i].split('.')[0]}.txt")
    os.remove(f"./oppsummeringer/{filnavn[i].split('.')[0]}.docx")
print("Logging slutt: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))