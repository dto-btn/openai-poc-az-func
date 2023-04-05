import os 
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

kv_name = os.environ["KEY_VAULT_NAME"]
kv_uri = f"https://{kv_name}.vault.azure.net"
credential  = DefaultAzureCredential()
client      = SecretClient(vault_url=kv_uri, credential=credential)

storage_connection  = client.get_secret("openai-storage-connection").value
blob_service_client = BlobServiceClient.from_connection_string(storage_connection)