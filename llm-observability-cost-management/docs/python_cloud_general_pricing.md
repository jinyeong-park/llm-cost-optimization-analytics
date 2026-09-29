[Skip to content](https://developers.llamaindex.ai/python/cloud/general/pricing/#_top)
# Pricing
All features are priced using **credits** , which are billed per page (or minute for audio). Credits vary by parsing mode, model, and whether files are cached.
## Credit Rates
[Section titled “Credit Rates”](https://developers.llamaindex.ai/python/cloud/general/pricing/#credit-rates)
Region | Price per 1,000 Credits  
---|---  
North America | $1.00  
Europe | $1.50  
## Parsing
[Section titled “Parsing”](https://developers.llamaindex.ai/python/cloud/general/pricing/#parsing)
Our recommended settings are simply mapping to a set of options (parse mode, model, and parameters).
Presets are created for specific use-cases.
Category | Mode | Model | Credits per Page  
---|---|---|---  
**Recommended Settings** | Cost-effective | - | 3  
Agentic | - | 10  
Agentic Plus | - | 45  
**Presets** | Invoice | - | 90  
Scientific papers | - | 90  
Technical documentation | - | 90  
Forms | - | 90  
**Modes** | Parse without AI | - | 1  
Parse page with LLM | - | 3  
Parse page with LVM | anthropic-sonnet-3.5 (deprecated) | 60  
anthropic-sonnet-3.7 | 60  
anthropic-sonnet-4.0 | 60  
anthropic-sonnet-4.5 | 60  
anthropic-haiku-4.5 (preview) | 30  
openai-gpt-4o-mini | 15  
openai-gpt-4o | 30  
openai-gpt-4-1-nano | 15  
openai-gpt-4-1-mini | 20  
openai-gpt-4-1 | 30  
openai-gpt-5-nano | 10  
openai-gpt-5-mini | 30  
openai-gpt-5 | 150  
gemini-1.5-flash (discountinued) | 15  
gemini-1.5-pro (discountinued) | 30  
gemini-2.0-flash | 6  
gemini-2.5-flash | 25  
gemini-2.5-pro | 60  
gemini-3.0-pro | 90  
Custom Azure Model | 1  
Use your own API key | 1  
Parse page with Layout Agent | - | 45  
Parse page with Agent | anthropic-sonnet-3.5 (deprecated) | 45  
anthropic-sonnet-3.7 | 90  
anthropic-sonnet-4.0 | 90  
anthropic-sonnet-4.5 | 90  
anthropic-haiku-4.5 (preview) | 45  
openai-gpt-4-1-mini | 10  
openai-gpt-4-1 | 45  
openai-gpt-5-nano | 10  
openai-gpt-5-mini | 45  
openai-gpt-5 | 90  
gemini-2.0-flash | 10  
gemini-2.5-flash | 10  
gemini-2.5-pro | 45  
Auto Mode | - | 3–45  
Parse document with LLM | - | 30  
Parse document with Agent | anthropic-sonnet-3.7 | 90  
anthropic-sonnet-4.0 | 90  
anthropic-sonnet-4.5 | 90  
**Other Options** | Structure Output | - | 3  
**File Type Modes** | Spreadsheet | - | 1 per sheet  
Audio | - | 3 per minute  
**Legacy Modes** | Continuous Mode | - | 30  
**Additional Configs:**
  * **Layout extraction:** +3 credits per page (can be added to any mode)


## Indexing
[Section titled “Indexing”](https://developers.llamaindex.ai/python/cloud/general/pricing/#indexing)
Mode | Credits per Page (or Sheet)  
---|---  
Standard | 1  
Spreadsheet | 2  
Multi-modal | 2  
## Extraction
[Section titled “Extraction”](https://developers.llamaindex.ai/python/cloud/general/pricing/#extraction)
Mode | Credits per Page | Credits per Page (extract only)*  
---|---|---  
Fast | 5 | 4  
Balanced | 10 | 7  
Multimodal | 20 | 14  
Premium | 60 | 15  
_*For text files or pre-cached parsed files._
  * For text files (md, txt, csv, html), a page is defined as the equivalent of 600 tokens.
  * For text files or if the file has previously been parsed by LlamaParse, only extraction costs apply.
  * For Multimodal mode, 6 additional credits will be charged for docx/pptx format.


## Split
[Section titled “Split”](https://developers.llamaindex.ai/python/cloud/general/pricing/#split)
Mode | Credits per Page  
---|---  
Default | 4 (3 for cached files)  
> If the file is already present in the LlamaParse cache, only split costs apply.
## Classification
[Section titled “Classification”](https://developers.llamaindex.ai/python/cloud/general/pricing/#classification)
Mode | Credits per Page  
---|---  
Fast | 1  
Multimodal | 2  
## Agents
[Section titled “Agents”](https://developers.llamaindex.ai/python/cloud/general/pricing/#agents)
Agents is currently in beta and **free to use**. When agents make use of Parse, Extract, or Index, the pricing of the underlying module applies.
