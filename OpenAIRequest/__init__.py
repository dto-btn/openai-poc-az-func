import json
import logging
import os
import io

import azure.functions as func
import openai
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

from pathlib import Path
from llama_index import GPTSimpleVectorIndex, download_loader

#storage_account_name = os.environ["STORAGE_ACCNT_NAME"]
key_vault_name          = os.environ["KEY_VAULT_NAME"]
openai_endpoint_name    = os.environ["OPENAI_ENDPOINT_NAME"]
deployment_name         = os.environ["OPENAI_DEPLOYMENT_NAME"]

kv_uri              = f"https://{key_vault_name}.vault.azure.net"
azure_openai_uri    = f"https://{openai_endpoint_name}.openai.azure.com"

credential  = DefaultAzureCredential()
client      = SecretClient(vault_url=kv_uri, credential=credential)

storage_connection  = client.get_secret("openai-storage-connection").value

blob_service_client = BlobServiceClient.from_connection_string(storage_connection)

openai.api_key      = client.get_secret("AzureOpenAIKey").value
openai.api_base     = azure_openai_uri
openai.api_type     = 'azure'
openai.api_version  = '2022-12-01' # this may change in the future

PDFReader = download_loader("PDFReader")
loader = PDFReader()

def main(req: func.HttpRequest) -> func.HttpResponse:

    
    logging.info('Python HTTP trigger function processed a request.')

    container_client = blob_service_client.get_container_client(container="unstructureddocs")

    documents = []
    
    logging.debug("Downloading blobs to create index...")
    for blob in container_client.list_blobs():

        current_file = open(blob.name.split("sscplus/")[1],mode='w')
        stream = io.BytesIO()
        download_blob_to_stream(blob_service_client, container_name="unstructureddocs", blob_name=blob.name, stream=current_file)
        documents = loader.load_data(current_file)
    
    logging.debug("Creating index...")
    index = GPTSimpleVectorIndex(documents)
    #downloader = blob.download_blob(encoding='UTF-8')
    #blob_text = downloader.readall()
    #print(f"Blob contents: {blob_text}")

    # Send a completion call to generate an answer
    #print('Sending a test completion job')
    #start_phrase = 'Write a tagline for an ice cream shop. '
    #response = openai.Completion.create(engine=deployment_name, prompt=start_phrase, max_tokens=10)
    #text = response['choices'][0]['text'].replace('\n', '').replace(' .', '.').strip()
    #print(start_phrase+text)

    enable_llm = bool(req.params.get('llm'))
    msg = req.params.get('msg')
    if not msg:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            msg = req_body.get('msg')

    if msg:
        return func.HttpResponse(f"{msg}\nAnwnser:")
    else:
        # ideally return json..
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

def list_blobs_hierarchical(self, container_client, prefix):
    for blob in container_client.walk_blobs(name_starts_with=prefix, delimiter='/'):
        if isinstance(blob, prefix):
            # Indentation is only added to show nesting in the output
            print(f"{self.indent * self.depth}{blob.name}")
            self.depth += 1
            self.list_blobs_hierarchical(container_client, prefix=blob.name)
            self.depth -= 1
        else:
            print(f"{self.indent * self.depth}{blob.name}")

def download_blob_to_string(blob_service_client: BlobServiceClient, container_name, blob_name):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    # encoding param is necessary for readall() to return str, otherwise it returns bytes
    downloader = blob_client.download_blob(max_concurrency=1, encoding='UTF-8')
    return downloader.readall()

def download_blob_to_stream(blob_service_client: BlobServiceClient, container_name, blob_name, stream):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.download_blob().readinto(stream)