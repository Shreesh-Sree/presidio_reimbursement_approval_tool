# Vercel Production Setup

## Required Environment Variables

The following environment variables must be configured in Vercel for production:

### 1. VITE_CLERK_PUBLISHABLE_KEY
**Value:** Your Clerk publishable key (starts with `pk_test_` or `pk_live_`)
**Environment:** Production
**Visibility:** Public (browser-visible)

Get this from your Clerk dashboard.

### 2. VITE_API_BASE_URL
**Value:** `https://api.algoqx.tech/api`
**Environment:** Production
**Visibility:** Public (browser-visible)

This points to the backend API deployed via Terraform.

### 3. VITE_CLERK_JWT_TEMPLATE
**Value:** `presidio-api`
**Environment:** Production
**Visibility:** Public (browser-visible)

This must match the JWT template name configured in your Clerk dashboard.

## Setting Environment Variables

```bash
cd frontend

# Add environment variables
vercel env add VITE_CLERK_PUBLISHABLE_KEY production --value "pk_test_..." --yes
vercel env add VITE_API_BASE_URL production --value "https://api.algoqx.tech/api" --yes
vercel env add VITE_CLERK_JWT_TEMPLATE production --value "presidio-api" --yes

# Verify
vercel env ls
```

## Project Root Directory Configuration

**CRITICAL:** Vercel project settings must have the correct root directory configured.

1. Go to https://vercel.com/shreesh/presidio-reimbursement/settings
2. Navigate to **General** → **Root Directory**
3. Ensure it's set to `frontend` (NOT `frontend/frontend`)
4. Save changes

## Redeployment

After setting environment variables or changing project settings:

1. **Automatic:** Push to `main` branch triggers automatic deployment
2. **Manual:** Click "Redeploy" on the latest deployment in Vercel dashboard

## Troubleshooting

### OAuth sign-in not configured error
- Verify `VITE_CLERK_PUBLISHABLE_KEY` is set and not empty
- Check that the value starts with `pk_test_` or `pk_live_`
- Ensure the Clerk key matches your production Clerk application

### API calls failing
- Verify `VITE_API_BASE_URL` points to the correct backend
- Test backend health: `curl https://api.algoqx.tech/api/health`
- Check that backend is deployed and running

### Deployment path errors
- Verify Root Directory is set to `frontend` in Vercel project settings
- Do NOT set it to `frontend/frontend` or any other path
