# Fix Invalid Supabase Anon Key

## Problem
Frontend getting 401 error: `Invalid API key` when calling Supabase API.

## Root Cause
GitHub secret `VITE_SUPABASE_ANON_KEY` contains old/invalid key.

## Solution

### Step 1: Get Current Anon Key from Supabase Dashboard

1. Open https://supabase.com/dashboard/project/gprhswxnzcipyqyrwcdr/settings/api
2. Find **Project API keys** section
3. Copy the **anon public** key (starts with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)

### Step 2: Update GitHub Secret

Run this command with the correct key:

```bash
# Replace <ANON_KEY> with the actual key from dashboard
gh secret set VITE_SUPABASE_ANON_KEY --body "<ANON_KEY>"
```

Or update via GitHub UI:
1. Go to https://github.com/Shreesh-Sree/presidio_reimbursement_approval_tool/settings/secrets/actions
2. Click **VITE_SUPABASE_ANON_KEY**
3. Click **Update secret**
4. Paste new anon key
5. Click **Update secret**

### Step 3: Redeploy Frontend

Trigger a new deployment to pick up the updated secret:

```bash
gh workflow run deploy-azure.yml
```

Or push any change to `main` branch (deployment runs automatically).

### Step 4: Verify

1. Open https://presidio.algoqx.tech
2. Check browser console - no 401 errors
3. Sign in with Google OAuth
4. Should redirect to `/reports` successfully

## Current Configuration

- **Supabase Project**: gprhswxnzcipyqyrwcdr
- **Supabase URL**: https://gprhswxnzcipyqyrwcdr.supabase.co
- **Frontend URL**: https://presidio.algoqx.tech

## Testing Anon Key

Test if a key is valid:

```bash
curl "https://gprhswxnzcipyqyrwcdr.supabase.co/rest/v1/" \
  -H "apikey: YOUR_ANON_KEY_HERE"
```

Valid key returns: `{"message":"Welcome to PostgREST"}`
Invalid key returns: `{"message":"Invalid API key"}`
