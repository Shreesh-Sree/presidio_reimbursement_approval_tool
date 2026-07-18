#!/bin/bash
set -e

echo "Azure Infrastructure Setup for GitHub Actions"
echo "=============================================="
echo ""

# Configuration
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-$(az account show --query id -o tsv)}"
RESOURCE_GROUP="presidio-reimbursement-rg"
LOCATION=$(az group show -n $RESOURCE_GROUP --query location -o tsv 2>/dev/null || echo "eastus")
GITHUB_ORG="Shreesh-Sree"
GITHUB_REPO="presidio_reimbursement_approval_tool"
ACR_NAME="presidiosree2026"  # Must be globally unique
SWA_NAME="presidio-frontend"
ENVIRONMENT_NAME="presidio-environment"

echo "Subscription: $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "ACR Name: $ACR_NAME"
echo ""
read -p "Continue with these settings? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "=== 1. Checking Resource Group ==="
if az group show --name $RESOURCE_GROUP &>/dev/null; then
    echo "✓ Resource group already exists in $LOCATION"
else
    az group create --name $RESOURCE_GROUP --location $LOCATION
    echo "✓ Resource group created"
fi

echo ""
echo "=== 2. Creating Service Principal with OIDC ==="
APP_NAME="presidio-github-actions"

# Check if app exists
APP_ID=$(az ad app list --display-name $APP_NAME --query "[0].appId" -o tsv)
if [ -z "$APP_ID" ]; then
    echo "Creating new app registration..."
    az ad app create --display-name $APP_NAME
    APP_ID=$(az ad app list --display-name $APP_NAME --query "[0].appId" -o tsv)
else
    echo "Using existing app: $APP_ID"
fi

# Create service principal if not exists
SP_EXISTS=$(az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv)
if [ -z "$SP_EXISTS" ]; then
    az ad sp create --id $APP_ID
    echo "✓ Service principal created"
else
    echo "✓ Service principal already exists"
fi

SP_OBJECT_ID=$(az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv)

# Assign Contributor role
SUBSCRIPTION_SCOPE="/subscriptions/$SUBSCRIPTION_ID"
ROLE_EXISTS=$(az role assignment list --assignee $APP_ID --role Contributor --scope "$SUBSCRIPTION_SCOPE" --query "[0].id" -o tsv)
if [ -z "$ROLE_EXISTS" ]; then
    az role assignment create \
        --role Contributor \
        --assignee-object-id $SP_OBJECT_ID \
        --assignee-principal-type ServicePrincipal \
        --scope "$SUBSCRIPTION_SCOPE"
    echo "✓ Contributor role assigned"
else
    echo "✓ Contributor role already assigned"
fi

# Add federated credential
CRED_EXISTS=$(az ad app federated-credential list --id $APP_ID --query "[?name=='github-main'].name" -o tsv)
if [ -z "$CRED_EXISTS" ]; then
    az ad app federated-credential create --id $APP_ID --parameters @- <<EOF
{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:${GITHUB_ORG}/${GITHUB_REPO}:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
}
EOF
    echo "✓ Federated credential created"
else
    echo "✓ Federated credential already exists"
fi

TENANT_ID=$(az account show --query tenantId -o tsv)

echo ""
echo "=== 3. Creating Azure Container Registry ==="
ACR_EXISTS=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP 2>/dev/null || echo "")
if [ -z "$ACR_EXISTS" ]; then
    az acr create \
        --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME \
        --sku Basic \
        --admin-enabled false
    echo "✓ ACR created"
else
    echo "✓ ACR already exists"
fi

# Grant AcrPush role
ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)
ACR_ROLE_EXISTS=$(az role assignment list --assignee $APP_ID --role AcrPush --scope $ACR_ID --query "[0].id" -o tsv)
if [ -z "$ACR_ROLE_EXISTS" ]; then
    az role assignment create \
        --role AcrPush \
        --assignee $APP_ID \
        --scope $ACR_ID
    echo "✓ AcrPush role assigned"
else
    echo "✓ AcrPush role already assigned"
fi

echo ""
echo "=== 4. Creating Azure Static Web Apps ==="
SWA_EXISTS=$(az staticwebapp show --name $SWA_NAME --resource-group $RESOURCE_GROUP 2>/dev/null || echo "")
if [ -z "$SWA_EXISTS" ]; then
    az staticwebapp create \
        --name $SWA_NAME \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --sku Free
    echo "✓ Static Web App created"
else
    echo "✓ Static Web App already exists"
fi

SWA_TOKEN=$(az staticwebapp secrets list \
    --name $SWA_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "properties.apiKey" -o tsv)

echo ""
echo "=== 5. Creating Container Apps Environment ==="
ENV_EXISTS=$(az containerapp env show --name $ENVIRONMENT_NAME --resource-group $RESOURCE_GROUP 2>/dev/null || echo "")
if [ -z "$ENV_EXISTS" ]; then
    az containerapp env create \
        --name $ENVIRONMENT_NAME \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION
    echo "✓ Container Apps environment created"
else
    echo "✓ Container Apps environment already exists"
fi

echo ""
echo "=== 6. Creating Container Apps ==="
SERVICES=("presidio-api" "presidio-ai-review" "presidio-receipt-intelligence" "presidio-policy-assistant")

for SERVICE in "${SERVICES[@]}"; do
    APP_EXISTS=$(az containerapp show --name $SERVICE --resource-group $RESOURCE_GROUP 2>/dev/null || echo "")
    if [ -z "$APP_EXISTS" ]; then
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
        echo "✓ $SERVICE created"
    else
        echo "✓ $SERVICE already exists"
    fi

    # Get FQDN
    FQDN=$(az containerapp show \
        --name $SERVICE \
        --resource-group $RESOURCE_GROUP \
        --query "properties.configuration.ingress.fqdn" -o tsv)

    if [ "$SERVICE" = "presidio-api" ]; then
        API_FQDN="https://$FQDN"
    fi
done

echo ""
echo "================================================"
echo "✓ Azure infrastructure setup complete!"
echo "================================================"
echo ""
echo "GitHub Secrets (copy these):"
echo "----------------------------"
echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
echo "ACR_LOGIN_SERVER=${ACR_NAME}.azurecr.io"
echo "AZURE_STATIC_WEB_APPS_API_TOKEN=$SWA_TOKEN"
echo ""
echo "GitHub Variables (copy these):"
echo "------------------------------"
echo "API_BASE_URL=$API_FQDN"
echo "VITE_API_BASE_URL=${API_FQDN}/api"
echo ""
echo "Next steps:"
echo "1. Get DATABASE_URL and keys from Supabase dashboard"
echo "2. Run: ./scripts/setup-github-secrets.sh"
echo "3. Merge feat/production-ready to main"
echo ""
echo "Save these credentials now!"
