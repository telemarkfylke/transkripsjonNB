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

# Empty dictionayr for metadat
metadata = {}

filnavn = htl.list_blobs(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME)
print("\n-----------------------------")
for i in range(len(filnavn)):
    print("\n-----------------------------")
    print(f"Blob {i}: {filnavn[i]}")
    metadata = htl.get_blob_metadata(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i])
    htl.download_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i], "./blobber/" + filnavn[i])
    htl.delete_blob(AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME, filnavn[i])
    htl.transkriber("./blobber/", filnavn[i])
    htl.oppsummering("./ferdig_tekst/", filnavn[i], metadata["format"])

    # Ecode the file to base64
    with open(f"./oppsummeringer/{filnavn[i]}.docx" , "rb") as file:
        base64file = base64.b64encode(file.read()).decode('utf-8')

    # Send mail
    htl.send_email(metadata["upn"], base64file)

    # Delete file from local storage
    os.remove(f"./blobber/{filnavn[i]}")
    os.remove(f"./ferdig_tekst/{filnavn[i]}.srt")
    os.remove(f"./oppsummeringer/{filnavn[i]}.md")
    os.remove(f"./oppsummeringer/{filnavn[i]}.docx")