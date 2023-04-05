# openai-poc-az-func

poc using the Azure OpenAI cognitive service (chatgpg 3.5 turbo)

## dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install openai azure-identity azure-keyvault-secrets llama-index azure-storage-blob
```

Then once you finish the setup for configs bellow you can simply `func start` and use your function service.

### keyvault

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

### LLM index for storing corpo documents to be leveraged

https://betterprogramming.pub/how-to-build-your-own-custom-chatgpt-with-custom-knowledge-base-4e61ad82427e