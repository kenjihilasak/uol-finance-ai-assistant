import os

from azure.identity import InteractiveBrowserCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


load_dotenv()

account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")

if not account_url:
    raise RuntimeError(
        "Falta AZURE_STORAGE_ACCOUNT_URL en el archivo .env"
    )

expected_containers = {
    "source-documents",
    "processed-documents",
    "evaluation-data",
}

tenant_id = os.getenv("AZURE_TENANT_ID")

if not tenant_id:
    raise RuntimeError("Falta AZURE_TENANT_ID en el archivo .env")

credential = InteractiveBrowserCredential(tenant_id=tenant_id)

blob_service = BlobServiceClient(
    account_url=account_url,
    credential=credential,
)

try:
    print(f"Conectando con: {account_url}")

    available_containers = {
        container["name"]
        for container in blob_service.list_containers()
    }

    print("\nContenedores esperados:")

    for name in sorted(expected_containers):
        status = "OK" if name in available_containers else "NO ENCONTRADO"
        print(f"- {name}: {status}")

finally:
    blob_service.close()
    credential.close()