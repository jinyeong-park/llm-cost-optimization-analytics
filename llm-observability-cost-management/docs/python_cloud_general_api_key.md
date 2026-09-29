[Skip to content](https://developers.llamaindex.ai/python/cloud/general/api_key/#_top)
# API Key
You need an API key to use LlamaCloud services including Parse, Extract, and Index.
## Generate a New API Key
[Section titled “Generate a New API Key”](https://developers.llamaindex.ai/python/cloud/general/api_key/#generate-a-new-api-key)
  1. Go to [LlamaCloud](https://cloud.llamaindex.ai) and sign in with your preferred method.
  2. Click on “API Key” in the left sidebar navigation.
  3. Click the “Generate New Key” button.
Access the API Key page
  4. Enter a descriptive name for your key and click “Create new key”.
  5. **Important** : Copy your API key immediately. For security reasons, you won’t be able to view the full key after you leave this page.
Generate your key


## Managing Your API Keys
[Section titled “Managing Your API Keys”](https://developers.llamaindex.ai/python/cloud/general/api_key/#managing-your-api-keys)
You can manage all your API keys from the API Key page:
  * **View active keys** : See all currently active keys and when they were created
  * **Revoke keys** : If a key is compromised or no longer needed, you can instantly revoke it
  * **Create new keys** : Generate additional keys for different projects or environments

The UI lets you manage your keys
## Using Your API Key
[Section titled “Using Your API Key”](https://developers.llamaindex.ai/python/cloud/general/api_key/#using-your-api-key)
Each LlamaCloud product has specific instructions for using your API key:
  * [Parse usage instructions](https://developers.llamaindex.ai/python/cloud/llamaparse/getting_started/)
  * [Extract usage instructions](https://developers.llamaindex.ai/python/cloud/llamaextract/getting_started/)
  * [Index usage instructions](https://developers.llamaindex.ai/python/cloud/llamacloud/getting_started/)


## API Key Scope
[Section titled “API Key Scope”](https://developers.llamaindex.ai/python/cloud/general/api_key/#api-key-scope)
API keys in LlamaCloud are scoped to both the individual user and the project:
  * **User Scope** : Each API key is associated with the user who created it
  * **Project Scope** : Keys are tied to the specific project they were created in and cannot be used across different projects


This scoping ensures proper access control and usage tracking within your organization.
## Security Best Practices
[Section titled “Security Best Practices”](https://developers.llamaindex.ai/python/cloud/general/api_key/#security-best-practices)
  * **Never hardcode your API key** directly in your application code
  * Store API keys as environment variables or in a secure key management service
  * Rotate your keys periodically for enhanced security
  * Use different keys for development and production environments


