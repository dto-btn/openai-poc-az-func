import os 
import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

kv_name = os.environ["KEY_VAULT_NAME"]
kv_uri = f"https://{kv_name}.vault.azure.net"
credential  = DefaultAzureCredential()
client      = SecretClient(vault_url=kv_uri, credential=credential)

storage_connection  = client.get_secret("openai-storage-connection").value
blob_service_client = BlobServiceClient.from_connection_string(storage_connection)

urls = [
    "https://plus.ssc-spc.gc.ca/en/topic/who-we-are"
]

def main():
    # use beautiful soup to get more urls from the base urls (SSC Plus, Sharepoint, etc.) .. and build a list of stuff to fetch..
    # todo

    # request text content from each urls ...
    for url in urls:
        r = requests.get(url, verify=False)
        d = r.text
        print(d)



if __name__ == "__main__":
    main()