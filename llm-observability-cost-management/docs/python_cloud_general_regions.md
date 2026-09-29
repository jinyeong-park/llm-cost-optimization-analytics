[Skip to content](https://developers.llamaindex.ai/python/cloud/general/regions/#_top)
# Regions
LlamaCloud provides cloud services across multiple regions, with availability in North America and Europe currently. You can [sign up](https://cloud.llamaindex.ai/) for a free account to get started in either region.
## Regional Endpoints
[Section titled “Regional Endpoints”](https://developers.llamaindex.ai/python/cloud/general/regions/#regional-endpoints)
North America (NA) | Europe (EU)  
---|---  
**Cloud** | cloud.llamaindex.ai | cloud.eu.llamaindex.ai  
**API** | api.cloud.llamaindex.ai | api.cloud.eu.llamaindex.ai  
**AWS Region** | us-east-1 | eu-central-1  
## Features
[Section titled “Features”](https://developers.llamaindex.ai/python/cloud/general/regions/#features)
### How do I use the EU region with the client?
[Section titled “How do I use the EU region with the client?”](https://developers.llamaindex.ai/python/cloud/general/regions/#how-do-i-use-the-eu-region-with-the-client)
When setting up the LlamaCloud client pass the attribute `base_url = 'api.cloud.eu.llamaindex.ai'`:
```


from llama_cloud.client import LlamaCloud





client =LlamaCloud(




token='<llama-cloud-api-key>',




base_url='api.cloud.eu.llamaindex.ai'



```

### Are there any differences between NA and EU LlamaCloud?
[Section titled “Are there any differences between NA and EU LlamaCloud?”](https://developers.llamaindex.ai/python/cloud/general/regions/#are-there-any-differences-between-na-and-eu-llamacloud)
All features are supported in both regions!
### Can I connect NA organizations and EU organizations for LlamaCloud, LlamaParse, Billing, etc…?
[Section titled “Can I connect NA organizations and EU organizations for LlamaCloud, LlamaParse, Billing, etc…?”](https://developers.llamaindex.ai/python/cloud/general/regions/#can-i-connect-na-organizations-and-eu-organizations-for-llamacloud-llamaparse-billing-etc)
LlamaIndex does not support this at the moment, Please let us know if you’re interested in this feature.
### Where is my data stored and processed?
[Section titled “Where is my data stored and processed?”](https://developers.llamaindex.ai/python/cloud/general/regions/#where-is-my-data-stored-and-processed)
Data will be stored within the region it is uploaded to. If interacting with LlamaCloud EU for example, all data provided will remain within the EU region for storage and processing.
### How can I see my organization’s region?
[Section titled “How can I see my organization’s region?”](https://developers.llamaindex.ai/python/cloud/general/regions/#how-can-i-see-my-organizations-region)
Check your URL. If your url is `https://cloud.llamaindex.ai` that is LlamaCloud NA, if your url is `https://cloud.eu.llamaindex.ai` that is LlamaCloud EU.
### Can I switch my organization between regions?
[Section titled “Can I switch my organization between regions?”](https://developers.llamaindex.ai/python/cloud/general/regions/#can-i-switch-my-organization-between-regions)
LlamaCloud does not support migrating between regions at this time. Please let us know if you’re interested in this feature.
## Legal & Compliance
[Section titled “Legal & Compliance”](https://developers.llamaindex.ai/python/cloud/general/regions/#legal--compliance)
### What privacy and data protection frameworks does LlamaCloud comply with?
[Section titled “What privacy and data protection frameworks does LlamaCloud comply with?”](https://developers.llamaindex.ai/python/cloud/general/regions/#what-privacy-and-data-protection-frameworks-does-llamacloud-comply-with)
LlamaCloud adheres to the General Data Protection Regulation (GDPR) and all other applicable laws and regulations governing our services. We are also SOC 2 Type 2 certified and HIPAA compliant. For more details on our security policies and practices, visit our [Trust Center](https://app.vanta.com/runllama.ai/trust/pkcgbjf8b3ihxjpqdx17nu).
## Can I sign a Data Processing Addendum (DPA) with LlamaIndex?
[Section titled “Can I sign a Data Processing Addendum (DPA) with LlamaIndex?”](https://developers.llamaindex.ai/python/cloud/general/regions/#can-i-sign-a-data-processing-addendum-dpa-with-llamaindex)
Yes, if you’d like to sign a Data Processing Addendum (DPA), please contact us. Please note that Business Associate Agreements (BAAs) are only available for customers on our Enterprise plan.
### My company is not based in the EU, can I still have my data hosted there?
[Section titled “My company is not based in the EU, can I still have my data hosted there?”](https://developers.llamaindex.ai/python/cloud/general/regions/#my-company-is-not-based-in-the-eu-can-i-still-have-my-data-hosted-there)
Yes, you can use LlamaCloud EU independent of your location.
### Do you have a legal entity in the EU that we can contract with?
[Section titled “Do you have a legal entity in the EU that we can contract with?”](https://developers.llamaindex.ai/python/cloud/general/regions/#do-you-have-a-legal-entity-in-the-eu-that-we-can-contract-with)
No, we do not have a legal entity in the EU for customer contracting today.
### Do different legal terms apply if I choose the EU region?
[Section titled “Do different legal terms apply if I choose the EU region?”](https://developers.llamaindex.ai/python/cloud/general/regions/#do-different-legal-terms-apply-if-i-choose-the-eu-region)
No, the terms are the same for the EU and NA regions.
