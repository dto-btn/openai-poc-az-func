import logging
import os
from typing import List

import azure.functions as func
import openai
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import AzureOpenAI
from llama_index import (GPTSimpleVectorIndex, LangchainEmbedding,
                         LLMPredictor, PromptHelper, ServiceContext,
                         download_loader)


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

def main(req: func.HttpRequest) -> func.HttpResponse:

    prompt = req.params.get('prompt')
    if not prompt:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            prompt = req_body.get('prompt')
    
    temp = req_body.get('temp')
    temperature = float(temp) if temp else 0.7

    # Define prompt helper
    max_input_size = 3000
    num_output = 256
    chunk_size_limit = 1000 # token window size per document
    max_chunk_overlap = 20 # overlap for each token fragment
    prompt_helper = PromptHelper(max_input_size=max_input_size, num_output=num_output, max_chunk_overlap=max_chunk_overlap, chunk_size_limit=chunk_size_limit)

    index = get_index(prompt_helper, temperature)
    answer = index.query(prompt)

    if prompt:
        return func.HttpResponse(f"{prompt}\nAnwnser:{answer}")
    else:
        # ideally return json..
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

def get_index(helper: PromptHelper, temperature: float) -> "GPTSimpleVectorIndex":
    logging.info("Creating index...")
    container_client = blob_service_client.get_container_client(container="unstructureddocs")

    #TODO: terrible way to do things, index should be generated elsewhere and simply loaded here.
    for blob in container_client.list_blobs():
        download_blob_to_file(blob_service_client, container_name="unstructureddocs", blob_name=blob.name)
    

    documents = SimpleDirectoryReader(input_dir='./sscplus').load_data()
    #logging.info("The documents are:" + ''.join(str(x.doc_id) for x in documents))

    # using same dep as model name because of an older bug in langchains lib (now fixed I believe)
    llm = NewAzureOpenAI(deployment_name=deployment_name, model_name=deployment_name, temperature=temperature)
    print(llm)
    llm_predictor = LLMPredictor(llm=llm)
    #current limitation with Azure OpenAI, has to be chunk size of 1
    embedding_llm = LangchainEmbedding(OpenAIEmbeddings(model="text-embedding-ada-002", chunk_size=1))
    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=helper, embed_model=embedding_llm)

    return GPTSimpleVectorIndex.from_documents(documents, service_context=service_context)
    
def download_blob_to_file(blob_service_client: BlobServiceClient, container_name, blob_name):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    basepath = os.path.dirname(blob_name)
    isExist = os.path.exists(os.path.dirname(blob_name))
    if not isExist:
        os.makedirs(os.path.dirname(blob_name))

    with open(file=blob_name, mode="wb") as sample_blob:
        download_stream = blob_client.download_blob()
        sample_blob.write(download_stream.readall())