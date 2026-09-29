[Skip to content](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#_top)
# Enterprise Rollout
## **Overview**
[Section titled “Overview”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#overview)
Rolling out LlamaCloud in a large enterprise requires planning to ensure a seamless onboarding experience for users. This guide provides step-by-step instructions for configuring LlamaCloud for an enterprise environment, defining user roles, setting up integrations, and best practices for operationalizing LlamaCloud in production.
Note that we will be expanding our RBAC offerings, and this cookbook will evolve with additional features
## **Step 1: Setting Up Your Organization**
[Section titled “Step 1: Setting Up Your Organization”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#step-1-setting-up-your-organization)
LlamaCloud structures access and resources using **Organizations** and **Projects**.
### **1.1 Create a Central Organization**
[Section titled “1.1 Create a Central Organization”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#11-create-a-central-organization)
  * Navigate to **Settings**
  * Define a single **organization** for your enterprise (e.g., ACME instead of each user having their own organization).
  * As you scale, you can consider additional organizations. We have seen large enterprises create an organization per business unit.


### **1.2 Configure Projects for Departments/ Teams**
[Section titled “1.2 Configure Projects for Departments/ Teams”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#12-configure-projects-for-departments-teams)
Each **Project** serves as a logical unit within the organization. Recommended structure:
  * **Experiments** : For initial testing and onboarding
  * **Teams** : Create dedicated projects per Team (e.g., Research, Engineering).


Note that integrations are scoped to a project (see below).
## **Step 2: Setting Up Integrations**
[Section titled “Step 2: Setting Up Integrations”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#step-2-setting-up-integrations)
You can pre-configure integrations to streamline workflows for your users. There are 3 kinds of integrations
  * Embedding Model (e.g. OpenAI keys)
  * Data Sink (e.g. vectorDB like MongoDB)
  * Data Source (e.g. Sharepoint or Box)


### **2.1 Configuring Embedding Models**
[Section titled “2.1 Configuring Embedding Models”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#21-configuring-embedding-models)
  * **Embedding model API Key Management** : Configure Embedding Model connection as a shared project resource. When creating an Index, a user can select from a dropdown the already configured API key instead of entering credentials manually.


### **2.2 Data Sources and Data Sinks**
[Section titled “2.2 Data Sources and Data Sinks”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#22-data-sources-and-data-sinks)
  * **Pre-configure Data Source Connectors** : Use a service credential to provide controlled access to shared folders.
  * Pre-Configure Data Sink Connection
  * When creating an index, users can select Data Source and Data Sink from a dropdown list


## **Step 3: Defining Users and Roles**
[Section titled “Step 3: Defining Users and Roles”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#step-3-defining-users-and-roles)
In Settings → Members you can add team members to your organization. By default, LlamaCloud has two roles: **Admin** and **Viewer**. We plan to add additional roles for granular control.
## **Step 4: Enterprise Rollout Strategy**
[Section titled “Step 4: Enterprise Rollout Strategy”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#step-4-enterprise-rollout-strategy)
### **4.1 Phase 1: Pilot Group Deployment**
[Section titled “4.1 Phase 1: Pilot Group Deployment”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#41-phase-1-pilot-group-deployment)
  * Start with a small team of **10-25 pilot users** in the `Experiments` project.
  * Gather feedback on usability, security, and role assignments.


### **4.2 Phase 2: Teams Expansion**
[Section titled “4.2 Phase 2: Teams Expansion”](https://developers.llamaindex.ai/python/cloud/cookbooks/enterprise_onboarding/#42-phase-2-teams-expansion)
  * Roll out LlamaCloud to various teams (or use cases) by creating projects for each.
  * Configure resources for each project so that the Index creation process is seamless


