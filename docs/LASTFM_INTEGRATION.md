# Last.fm Integration Guide

Audiovault integrates with Last.fm to provide personalized music recommendations and scrobbling capabilities. This guide explains how to set up the integration.

## Features

- **Personalized Recommendations**: Get track recommendations based on your listening history.
- **Scrobbling**: Automatically record your listening history to your Last.fm profile.
- **Top Charts**: View your top artists and tracks directly in Audiovault.

## Setup Instructions

To use Last.fm features, you need to obtain an API Key and Shared Secret from Last.fm and configure them in your Audiovault instance.

### Step 1: Get Last.fm API Credentials

1.  **Log in** to your Last.fm account.
2.  Go to the **[Create an API Account](https://www.last.fm/api/account/create)** page.
3.  Fill in the form:
    - **Application Name**: `Audiovault` (or any name you prefer)
    - **Application Description**: `Self-hosted music server`
    - **Callback URL**: You can leave this blank or set it to your server URL (e.g., `http://localhost:2137/settings`). _Note: Audiovault handles the callback internally._
4.  Submit the form.
5.  You will be shown your **API Key** and **Shared Secret**. Copy these values.

### Step 2: Configure Audiovault

Add the API credentials to your `.env` file in the Audiovault root directory:

```bash
# Last.fm Integration
LASTFM_API_KEY=your_copied_api_key
LASTFM_API_SECRET=your_copied_shared_secret
```

### Step 3: Apply Changes

Restart the backend container to apply the changes:

```bash
docker compose restart backend
```

### Step 4: Connect Account

1.  Open the Audiovault web interface.
2.  Go to the **Recommendations** page (or Settings).
3.  Click the **Connect Last.fm** button.
4.  You will be redirected to Last.fm to approve the access.
5.  Once approved, you will be redirected back to Audiovault, and your account will be connected.

## Troubleshooting

- **"Last.fm authentication failed"**: Check if your `LASTFM_API_KEY` and `LASTFM_API_SECRET` are correct in the `.env` file and that you have restarted the backend.
- **Recommendations not showing**: Ensure you have a listening history on Last.fm. Recommendations are based on your existing data.
