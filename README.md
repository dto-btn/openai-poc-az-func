# openai-poc-az-func

poc using the Azure OpenAI cognitive service (chatgpg 3.5 turbo) and `llama_index` to build and index to use with the LLM

## How-to

Pull this project and create your virtual env, install packages and you can simply run `func start` (see [prerequisites](#pre-requisites))

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install openai azure-identity azure-keyvault-secrets llama-index azure-storage-blob langchain
```

Then once you finish the setup for configs bellow you can simply `func start` and use your function service.

### Pre-requisites

* VSCode with Azure Dev tools such as anything needed to run app dev locally.
* .NET runtime ..
* etc.

Set KeyVault setting to your `local.settings.json` we will be using `DefaultAzureCredential` to conect to Key Vault.

```bash
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "KEY_VAULT_NAME": "ScDC-CIO-DTO-Infra-kv",
    "OPENAI_ENDPOINT_NAME":"scdc-cio-dto-openai-poc-oai",
    "OPENAI_DEPLOYMENT_NAME":"gpt-35-poc-dev"
  }
}
```

## Documentation

*  python langchain [documentation](https://python.langchain.com/en/latest/index.html) 
* [llamahub to get custom loaders](https://llamahub.ai/)
* [llama_index](https://gpt-index.readthedocs.io/en/latest/index.html) documentation on how to build the index and load it

### Other references used as inspiration

* https://betterprogramming.pub/how-to-build-your-own-custom-chatgpt-with-custom-knowledge-base-4e61ad82427e
* https://github.com/jerryjliu/llama_index/blob/main/docs/guides/primer/usage_pattern.md
* https://python.langchain.com/en/harrison-docs-refactor-3-24/modules/models/text_embedding/examples/azureopenai.html
* https://python.langchain.com/en/harrison-docs-refactor-3-24/modules/models/llms/integrations/azure_openai_example.html
* https://clemenssiebler.com/posts/chatting-private-data-langchain-azure-openai-service/