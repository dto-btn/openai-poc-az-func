from typing import List
import json
import logging
import os
import io

import azure.functions as func
import openai

from langchain.llms import AzureOpenAI
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

from pathlib import Path
from llama_index import (
    GPTSimpleVectorIndex, 
    download_loader, 
    LLMPredictor, 
    PromptHelper,
    ServiceContext
)
from langchain.embeddings import OpenAIEmbeddings
from llama_index import LangchainEmbedding

class NewAzureOpenAI(AzureOpenAI):
    stop: List[str] = None
    @property
    def _invocation_params(self):
        params = super()._invocation_params
        # fix InvalidRequestError: logprobs, best_of and echo parameters are not available on gpt-35-turbo model.
        params.pop('logprobs', None)
        params.pop('best_of', None)
        params.pop('echo', None)
        #params['stop'] = self.stop
        return params

#storage_account_name = os.environ["STORAGE_ACCNT_NAME"]
key_vault_name          = os.environ["KEY_VAULT_NAME"]
openai_endpoint_name    = os.environ["OPENAI_ENDPOINT_NAME"]
deployment_name         = os.environ["OPENAI_DEPLOYMENT_NAME"]

kv_uri              = f"https://{key_vault_name}.vault.azure.net"
azure_openai_uri    = f"https://{openai_endpoint_name}.openai.azure.com"

credential  = DefaultAzureCredential()
client      = SecretClient(vault_url=kv_uri, credential=credential)

blob_service_client = BlobServiceClient.from_connection_string(client.get_secret("openai-storage-connection").value)

openai.api_type     = 'azure'
openai.api_base     = azure_openai_uri
openai.api_key      = client.get_secret("AzureOpenAIKey").value
openai.api_version  = '2022-12-01' # this may change in the future

os.environ["OPENAI_API_TYPE"]   = "azure"
os.environ["OPENAI_API_BASE"]   = azure_openai_uri
os.environ["OPENAI_API_KEY"]    = client.get_secret("AzureOpenAIKey").value
os.environ["OPENAI_API_VERSION"] = '2022-12-01' # this may change in the future

SimpleDirectoryReader  = download_loader("SimpleDirectoryReader")

##############################################################################
##########################-UTIL FUNCTIONS-####################################
##############################################################################
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

def download_blob_to_file(blob_service_client: BlobServiceClient, container_name, blob_name):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    basepath = os.path.dirname(blob_name)
    isExist = os.path.exists(os.path.dirname(blob_name))
    if not isExist:
        os.makedirs(os.path.dirname(blob_name))

    with open(file=blob_name, mode="wb") as sample_blob:
        download_stream = blob_client.download_blob()
        sample_blob.write(download_stream.readall())

##############################################################################
##########################       MAIN      ###################################
##############################################################################
def main(req: func.HttpRequest) -> func.HttpResponse:

    container_client = blob_service_client.get_container_client(container="unstructureddocs")

    # TODO: terrible way to do things, index should be generated elsewhere and simply loaded here.
    for blob in container_client.list_blobs():
    #uncomment for live download ... test only atm
        download_blob_to_file(blob_service_client, container_name="unstructureddocs", blob_name=blob.name)
        #print(blob.name)
    

    documents = SimpleDirectoryReader(input_dir='./sscplus').load_data()
    logging.info("The documents are:" + ''.join(str(x.doc_id) for x in documents))

    logging.info("Creating index...")
    # Define prompt helper
    max_input_size = 3000
    num_output = 256
    chunk_size_limit = 1000 # token window size per document
    max_chunk_overlap = 20 # overlap for each token fragment
    prompt_helper = PromptHelper(max_input_size=max_input_size, num_output=num_output, max_chunk_overlap=max_chunk_overlap, chunk_size_limit=chunk_size_limit)

    # using same dep as model name because of an older bug in langchains lib (now fixed I believe)
    llm = NewAzureOpenAI(deployment_name=deployment_name, model_name=deployment_name, temperature=0.5)
    print(llm)
    llm_predictor = LLMPredictor(llm=llm)
    embedding_llm = LangchainEmbedding(OpenAIEmbeddings(model="text-embedding-ada-002", chunk_size=1))
    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=prompt_helper, embed_model=embedding_llm)
    #service_context = ServiceContext(llm_predictor=llm_predictor, prompt_helper=prompt_helper, embed_model=embedding_llm, node_parser=None, llama_logger=None)
    index = GPTSimpleVectorIndex.from_documents(documents, service_context=service_context)

    msg = req.params.get('msg')
    if not msg:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            msg = req_body.get('msg')

    answer = index.query(msg)

    if msg:
        return func.HttpResponse(f"{msg}\nAnwnser:{answer}")
    else:
        # ideally return json..
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )