# Download file from azure blob storage
import os, dotenv
#from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import ffmpeg, os
from transformers import pipeline
#import json
#from datetime import datetime, timedelta
from openai import OpenAI
import pprint as pp
#from docx import Document
#import os, requests
#import base64

import warnings
warnings.filterwarnings("ignore")

from lib import hugintranskriptlib as htl

dotenv.load_dotenv()
client = OpenAI()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 

filnavn = htl.list_blobs(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME)
metadata = []
print("\n-----------------------------")

for i in range(len(filnavn)):
    print("\n-----------------------------")
    print(f"Blob {i}: {filnavn[i]}")
    metadata.append(htl.get_blob_metadata(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i]))
    print("Sendes: ", metadata[i]['format'], metadata[i]['spraak'])
    htl.download_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i], "./blobber/" + filnavn[i])
    htl.delete_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i])

for i in range(len(filnavn)):
    if filnavn[i].split(".")[1] == "mp4" or filnavn[i].split(".")[1] == "mov" or filnavn[i].split(".")[1] == "avi":
        htl.konverter_til_lyd(f"./blobber/{filnavn[i]}", f"./blobber/{filnavn[i].split('.')[0]}.wav")
    htl.transkriber("./blobber/", filnavn[i])
    # htl.oppsummering("./ferdig_tekst/", filnavn[i], metadata[i]['spraak'] ,metadata[i]['format'])
    htl.srt_til_tekst(filnavn[i].split(".")[0] + ".srt")

    # Encode the file to base64
    # with open(f"./oppsummeringer/{filnavn[i].split(".")[0]}.docx" , "rb") as file:
    #    base64file = base64.b64encode(file.read()).decode('utf-8')

    # Send mail
    # htl.send_email(metadata[i]["upn"], base64file)

    # Delete file from local storage
    os.remove(f"./blobber/{filnavn[i]}")
    # os.remove(f"./ferdig_tekst/{filnavn[i].split(".")[0]}.srt")
    # os.remove(f"./oppsummeringer/{filnavn[i]}.md")
    #os.remove(f"./oppsummeringer/{filnavn[i]}.docx")