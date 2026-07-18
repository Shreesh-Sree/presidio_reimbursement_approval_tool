# GitHub to Azure/Supabase Auto-Deployment Setup

This guide configures automatic deployments from GitHub to Azure and Supabase.

## Prerequisites

- Azure subscription with Owner/Contributor access
- Supabase project (free tier works)
- GitHub repository with admin access

## 1. Azure Service Principal (OIDC)

Create a service principal for GitHub Actions to authenticate via OIDC (no secrets needed):

```bash
# Set variables
SUBSCRIPTION_ID="your-subscription-id"
RESOURCE_GROUP="presidio-reimbursement-rg"
LOCATION="eastus"
GITHUB_ORG="Shreesh-Sree"
GITHUB_REPO="presidio_reimbursement_approval_tool"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create service principal with OIDC federation
APP_NAME="presidio-github-actions"
az ad app create --display-name $APP_NAME

# Get app ID
APP_ID=$(az ad app list --display-name $APP_NAME --query "[0].appId" -o tsv)

# Create service principal
az ad sp create --id $APP_ID

# Get service principal object ID
SP_OBJECT_ID=$(az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv)

# Assign Contributor role to subscription
az role assignment create \
  --role Contributor \
  --subscription $SUBSCRIPTION_ID \
  --assignee-object-id $SP_OBJECT_ID \
  --assignee-principal-type ServicePrincipal

# Add federated credential for azure-production environment
az ad app federated-credential create \
  --id $APP_ID \
  --parameters "{
    \"name\": \"github-azure-production\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GITHUB_ORG}/${GITHUB_REPO}:environment:azure-production\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"

# Get tenant ID
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "AZURE_CLIENT_ID: $APP_ID"
echo "AZURE_TENANT_ID: $TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID: $SUBSCRIPTION_ID"
```

## 2. Azure Container Registry

Create ACR for Docker images:

```bash
ACR_NAME="presidioregistry"  # Must be globally unique

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled false

# Grant service principal ACR push/pull access
ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)
az role assignment create \
  --role AcrPush \
  --assignee $APP_ID \
  --scope $ACR_ID

echo "ACR_LOGIN_SERVER: ${ACR_NAME}.azurecr.io"
```

## 3. Azure Static Web Apps

Create SWA for frontend hosting:

```bash
SWA_NAME="presidio-frontend"

az staticwebapp create \
  --name $SWA_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Free

# Get deployment token
SWA_TOKEN=$(az staticwebapp secrets list \
  --name $SWA_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.apiKey" -o tsv)

echo "AZURE_STATIC_WEB_APPS_API_TOKEN: $SWA_TOKEN"
```

## 4. Supabase Configuration

Get credentials from Supabase dashboard (https://supabase.com/dashboard):

1. **Project Settings → API**:
   - `VITE_SUPABASE_URL`: Project URL (e.g., `https://xxxxx.supabase.co`)
   - `VITE_SUPABASE_ANON_KEY`: Anon/public key

2. **Project Settings → Database → Connection string**:
   - Copy "URI" connection string
   - Format: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
   - This becomes `DATABASE_URL`

## 5. GitHub Secrets Configuration

Go to: `https://github.com/Shreesh-Sree/presidio_reimbursement_approval_tool/settings/secrets/actions`

### Add Repository Secrets:

```
AZURE_CLIENT_ID                  = <from step 1>
AZURE_TENANT_ID                  = <from step 1>
AZURE_SUBSCRIPTION_ID            = <from step 1>
ACR_LOGIN_SERVER                 = presidioregistry.azurecr.io
AZURE_STATIC_WEB_APPS_API_TOKEN  = <from step 3>
DATABASE_URL                     = <from step 4>
VITE_SUPABASE_ANON_KEY          = <from step 4>
```

### Add Repository Variables:

Go to: `Settings → Secrets and variables → Actions → Variables`

```
VITE_SUPABASE_URL    = https://xxxxx.supabase.co
VITE_API_BASE_URL    = https://presidio-api.redrock-12345678.eastus.azurecontainerapps.io/api
API_BASE_URL         = https://presidio-api.redrock-12345678.eastus.azurecontainerapps.io
```

## 6. Azure Container Apps Environment

Create Container Apps environment for backend services:

```bash
ENVIRONMENT_NAME="presidio-environment"

az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Create container apps (backend, AI services)
SERVICES=("presidio-api" "presidio-ai-review" "presidio-receipt-intelligence" "presidio-policy-assistant")

for SERVICE in "${SERVICES[@]}"; do
  az containerapp create \
    --name $SERVICE \
    --resource-group $RESOURCE_GROUP \
    --environment $ENVIRONMENT_NAME \
    --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --registry-server ${ACR_NAME}.azurecr.io \
    --registry-identity system
    
  # Get FQDN
  FQDN=$(az containerapp show \
    --name $SERVICE \
    --resource-group $RESOURCE_GROUP \
    --query "properties.configuration.ingress.fqdn" -o tsv)
  
  echo "$SERVICE FQDN: https://$FQDN"
done

# Update API_BASE_URL variable with presidio-api FQDN
```

## 7. Environment Configuration for Container Apps

Set environment variables for all services:

```bash
# Common environment variables
az containerapp update \
  --name presidio-api \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "DATABASE_URL=secretref:database-url" \
    "SUPABASE_URL=https://xxxxx.supabase.co" \
    "SUPABASE_SERVICE_KEY=secretref:supabase-service-key"

# Add secrets
az containerapp secret set \
  --name presidio-api \
  --resource-group $RESOURCE_GROUP \
  --secrets \
    database-url="<DATABASE_URL>" \
    supabase-service-key="<SUPABASE_SERVICE_ROLE_KEY>"

# Repeat for other services (ai-review, receipt-intelligence, policy-assistant)
```

## 8. Supabase Database Setup

Run migrations locally first time:

```bash
cd backend

# Set DATABASE_URL from Supabase
export DATABASE_URL="postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"

# Install dependencies
uv sync

# Run migrations
uv run alembic upgrade head
```

## 9. GitHub Actions Environment

Create protected environment for production:

1. Go to: `https://github.com/Shreesh-Sree/presidio_reimbursement_approval_tool/settings/environments`
2. Click "New environment"
3. Name: `azure-production`
4. (Optional) Add required reviewers
5. (Optional) Add deployment branches rule: only `main`

## 10. Test Deployment

Trigger deployment:

```bash
# Option 1: Push to main
git checkout main
git merge feat/production-ready
git push origin main

# Option 2: Manual trigger
# Go to Actions → Deploy to Production → Run workflow
```

## 11. Verify Deployment

Check workflow run:

```bash
# Visit: https://github.com/Shreesh-Sree/presidio_reimbursement_approval_tool/actions

# Or check URLs:
echo "Frontend: https://<swa-name>.azurestaticapps.net"
echo "Backend: https://<api-fqdn>/api/health"
```

## Troubleshooting

### Build containers failing
- Verify ACR credentials: `az acr show --name $ACR_NAME`
- Check service principal has AcrPush role
- Verify Dockerfiles exist in `backend/`, `ai_review_service/`, etc.

### Deploy frontend failing
- Check SWA token is valid (regenerate if needed)
- Verify `frontend/staticwebapp.config.json` exists
- Check build output contains `dist/index.html`

### Run migrations failing
- Verify DATABASE_URL is correct (use connection pooler port 6543)
- Check Supabase project is not paused
- Ensure Alembic migrations exist in `backend/alembic/versions/`

### Terraform apply failing
- Initialize Terraform backend first (see `deployment/terraform-azure/README.md`)
- Verify service principal has Contributor role
- Check state file backend is configured

### Container apps not updating
- Verify apps exist: `az containerapp list -g $RESOURCE_GROUP -o table`
- Check ACR has images: `az acr repository list -n $ACR_NAME`
- Review container logs: `az containerapp logs show -n presidio-api -g $RESOURCE_GROUP`

## Auto-Deploy Flow

Once configured, every push to `main` triggers:

1. **CI checks** (lint, test, build) run first
2. **Wait for CI** to pass (gate)
3. **Database migrations** run against Supabase
4. **Build containers** → push to ACR
5. **Deploy containers** to Azure Container Apps
6. **Deploy frontend** to Azure Static Web Apps
7. **Terraform apply** (if infra files changed)
8. **Health verification** checks all services live

Deployments take ~5-10 minutes total.

## Cost Estimate

- ACR Basic: $5/month
- Container Apps (4 services, 1GB each): ~$30-40/month
- Static Web Apps Free: $0
- Supabase Free tier: $0
- **Total: ~$35-45/month**

## Next Steps

1. Set up custom domain for Static Web Apps
2. Configure Supabase Auth providers (Google, GitHub OAuth)
3. Add Azure Application Insights for monitoring
4. Set up Azure Key Vault for secrets management
5. Configure CDN for frontend assets
