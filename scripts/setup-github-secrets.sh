#!/bin/bash
set -e

# GitHub repository
REPO="Shreesh-Sree/presidio_reimbursement_approval_tool"

echo "Setting up GitHub Secrets and Variables for $REPO"
echo "=================================================="
echo ""
echo "This script will prompt you for values. Get them from:"
echo "1. Azure: Run azure-setup.sh first"
echo "2. Supabase: Dashboard → Project Settings"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) not installed"
    echo "Install: sudo apt install gh"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Not authenticated. Running gh auth login..."
    gh auth login
fi

echo ""
echo "=== SECRETS (encrypted) ==="
echo ""

# Azure credentials
read -p "AZURE_CLIENT_ID (from Azure setup): " AZURE_CLIENT_ID
gh secret set AZURE_CLIENT_ID --repo $REPO --body "$AZURE_CLIENT_ID"
echo "✓ AZURE_CLIENT_ID set"

read -p "AZURE_TENANT_ID (from Azure setup): " AZURE_TENANT_ID
gh secret set AZURE_TENANT_ID --repo $REPO --body "$AZURE_TENANT_ID"
echo "✓ AZURE_TENANT_ID set"

read -p "AZURE_SUBSCRIPTION_ID (from Azure setup): " AZURE_SUBSCRIPTION_ID
gh secret set AZURE_SUBSCRIPTION_ID --repo $REPO --body "$AZURE_SUBSCRIPTION_ID"
echo "✓ AZURE_SUBSCRIPTION_ID set"

read -p "ACR_LOGIN_SERVER (e.g., presidioregistry.azurecr.io): " ACR_LOGIN_SERVER
gh secret set ACR_LOGIN_SERVER --repo $REPO --body "$ACR_LOGIN_SERVER"
echo "✓ ACR_LOGIN_SERVER set"

read -p "AZURE_STATIC_WEB_APPS_API_TOKEN (from SWA setup): " SWA_TOKEN
gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --repo $REPO --body "$SWA_TOKEN"
echo "✓ AZURE_STATIC_WEB_APPS_API_TOKEN set"

read -p "DATABASE_URL (Supabase connection string): " DATABASE_URL
gh secret set DATABASE_URL --repo $REPO --body "$DATABASE_URL"
echo "✓ DATABASE_URL set"

read -p "VITE_SUPABASE_ANON_KEY (Supabase anon key): " ANON_KEY
gh secret set VITE_SUPABASE_ANON_KEY --repo $REPO --body "$ANON_KEY"
echo "✓ VITE_SUPABASE_ANON_KEY set"

echo ""
echo "=== VARIABLES (public, not encrypted) ==="
echo ""

read -p "VITE_SUPABASE_URL (e.g., https://xxxxx.supabase.co): " SUPABASE_URL
gh variable set VITE_SUPABASE_URL --repo $REPO --body "$SUPABASE_URL"
echo "✓ VITE_SUPABASE_URL set"

read -p "VITE_API_BASE_URL (Container App FQDN + /api): " VITE_API_BASE_URL
gh variable set VITE_API_BASE_URL --repo $REPO --body "$VITE_API_BASE_URL"
echo "✓ VITE_API_BASE_URL set"

read -p "API_BASE_URL (Container App FQDN): " API_BASE_URL
gh variable set API_BASE_URL --repo $REPO --body "$API_BASE_URL"
echo "✓ API_BASE_URL set"

echo ""
echo "=== ENVIRONMENT ==="
echo ""

# Create azure-production environment
gh api repos/$REPO/environments/azure-production -X PUT --silent 2>/dev/null || {
    echo "✓ Environment 'azure-production' already exists or created"
}

echo ""
echo "========================================"
echo "✓ All secrets and variables configured!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Verify: gh secret list --repo $REPO"
echo "2. Verify: gh variable list --repo $REPO"
echo "3. Run Azure setup: ./scripts/azure-setup.sh"
echo "4. Merge to main to trigger deployment"
