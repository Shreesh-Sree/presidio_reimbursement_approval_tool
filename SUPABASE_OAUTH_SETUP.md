# Supabase OAuth Configuration

Complete OAuth setup for production deployment at `https://presidio.algoqx.tech`

## 1. Site URL Configuration

1. Open https://supabase.com/dashboard/project/gprhswxnzcipyqyrwcdr/settings/auth
2. Navigate to **Authentication → URL Configuration**
3. Set:
   - **Site URL**: `https://presidio.algoqx.tech`
   - **Redirect URLs** (add these):
     - `https://presidio.algoqx.tech/reports`
     - `https://presidio.algoqx.tech/**` (wildcard for all routes)

## 2. Enable Google OAuth

### Step 1: Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID (or use existing):
   - Application type: **Web application**
   - Name: `Presidio Reimbursement Tool`
   - **Authorized JavaScript origins**:
     - `https://presidio.algoqx.tech`
   - **Authorized redirect URIs**:
     - `https://gprhswxnzcipyqyrwcdr.supabase.co/auth/v1/callback`
3. Copy **Client ID** and **Client Secret**

### Step 2: Configure in Supabase

1. Open https://supabase.com/dashboard/project/gprhswxnzcipyqyrwcdr/settings/auth
2. Navigate to **Authentication → Providers**
3. Find **Google** provider, click **Enable**
4. Paste:
   - **Client ID**: `<from Google Cloud Console>`
   - **Client Secret**: `<from Google Cloud Console>`
5. **Authorized Client IDs**: (leave empty unless using native apps)
6. Click **Save**

## 3. Enable GitHub OAuth (Optional)

### Step 1: Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**:
   - Application name: `Presidio Reimbursement Tool`
   - Homepage URL: `https://presidio.algoqx.tech`
   - Authorization callback URL: `https://gprhswxnzcipyqyrwcdr.supabase.co/auth/v1/callback`
3. Click **Register application**
4. Generate **Client Secret**
5. Copy **Client ID** and **Client Secret**

### Step 2: Configure in Supabase

1. Open https://supabase.com/dashboard/project/gprhswxnzcipyqyrwcdr/settings/auth
2. Navigate to **Authentication → Providers**
3. Find **GitHub** provider, click **Enable**
4. Paste:
   - **Client ID**: `<from GitHub>`
   - **Client Secret**: `<from GitHub>`
5. Click **Save**

## 4. Email Settings (Optional but Recommended)

1. Navigate to **Authentication → Email Templates**
2. Configure **Confirm signup**, **Magic Link**, **Change Email Address** templates
3. Set **Sender Name**: `AlgoQX Expense Management`
4. Set **Sender Email**: (your verified email or use Supabase default)

## 5. Verification

After configuration:

1. Open https://presidio.algoqx.tech/sign-in
2. Click **Continue with Google** (or GitHub)
3. Authenticate
4. Should redirect to `https://presidio.algoqx.tech/reports` (dashboard)
5. Check network tab - should see successful `/api/auth/me` call

## Troubleshooting

### Error: "Invalid Redirect URL"
- Ensure `https://presidio.algoqx.tech/reports` added to Supabase redirect URLs
- Ensure Google/GitHub callback URL is exactly `https://gprhswxnzcipyqyrwcdr.supabase.co/auth/v1/callback`

### Error: "Unauthorized client"
- Double-check Client ID and Secret in Supabase match Google Cloud Console
- Ensure OAuth consent screen is configured in Google Cloud Console

### Stuck on sign-in page after OAuth
- Check browser console for errors
- Verify frontend `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are correct
- Ensure backend `/api/auth/me` endpoint accessible

### "Access not granted" error
- User exists in Supabase but not in backend database
- Check backend logs for user creation errors
- May need to manually add user to `users` table

## Current Configuration

- **Supabase Project**: gprhswxnzcipyqyrwcdr
- **Supabase URL**: https://gprhswxnzcipyqyrwcdr.supabase.co
- **Frontend URL**: https://presidio.algoqx.tech
- **Backend API**: https://presidio-reimburse-prod-api.redstone-3836f13b.centralindia.azurecontainerapps.io

## Next Steps

1. Complete OAuth provider setup in Supabase dashboard (above)
2. Merge PR #20 to deploy redirect fix
3. Test OAuth flow end-to-end
4. Configure email templates if using magic links
