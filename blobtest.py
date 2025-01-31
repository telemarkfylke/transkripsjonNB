# Download file from azure blob storage
import os, dotenv
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

dotenv.load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
filnavn = []

def download_blob(container_name, blob_name, download_file_path):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    print("\nDownloading blob to \n\t" + download_file_path)

    with open(download_file_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())
    print(f"Blob {blob_name} downloaded to {download_file_path}")

# Functioon to list all blobs in a container
def list_blobs(container_name):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(container_name)
    print("\nListing blobs...")
    for blob in container_client.list_blobs():
        print("\t" + blob.name)
        filnavn.append(blob.name)

# Get metadata of a blob
def get_blob_metadata(container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    print("\nGetting blob metadata...")
    print("\t" + str(blob_client.get_blob_properties().metadata))

# Delete downloaded blob
def delete_blob(container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    print("\nDeleting blob...")
    blob_client.delete_blob()
    print("\tBlob deleted")

list_blobs(AZURE_STORAGE_CONTAINER_NAME)
print("\n-----------------------------")
for i in range(len(filnavn)):
    print("\n-----------------------------")
    print(f"Blob {i}: {filnavn[i]}")
    get_blob_metadata(AZURE_STORAGE_CONTAINER_NAME, filnavn[i])
    download_blob(AZURE_STORAGE_CONTAINER_NAME, filnavn[i], "./" + filnavn[i])
    delete_blob(AZURE_STORAGE_CONTAINER_NAME, filnavn[i])