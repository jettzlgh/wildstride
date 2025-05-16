import requests
import urllib.parse
import time
import streamlit as st
from storage import Storage

storage = Storage()

CLIENT_ID = st.secrets["strava_client_id"]
CLIENT_SECRET = st.secrets["strava_client_secret"]

# REDIRECT_URI = "http://localhost:8501"
REDIRECT_URI = "https://wildstride.streamlit.app/"

def remove_character(text: str, char_to_remove: str) -> str:
    return text.replace(char_to_remove, "")

def get_strava_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "activity:read_all,activity:write"
    }
    return "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(params)

@st.cache_data
def get_token(code):
    """Exchange authorization code for access token"""
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }
    )
    return response.json()

@st.cache_data
def get_activities(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers)
    return response.json()

@st.cache_data
def get_activity_details(access_token, activity_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    url=f"https://www.strava.com/api/v3/activities/{activity_id}?include_all_efforts=true"
    response = requests.get(url, headers=headers)
    return response.json()

@st.cache_data
def get_athlete_details(access_token):
    """Get detailed information about the authenticated athlete"""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://www.strava.com/api/v3/athlete", headers=headers)
    return response.json()

@st.cache_data
def get_athlete_stats(access_token, athlete_id):
    """Get statistics about the authenticated athlete"""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"https://www.strava.com/api/v3/athletes/{athlete_id}/stats", headers=headers)
    return response.json()

def refresh_token(refresh_token: str) -> dict:
    """Refresh the Strava access token"""
    print(f"Refreshing token...")
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
    )
    return response.json()

@st.cache_data
def get_valid_token(athlete_id: str = None) -> tuple:
    """Get a valid Strava access token, refreshing if necessary"""
    if not athlete_id:
        return None, None

    # Try to get stored tokens
    stored_tokens = storage.get_strava_tokens(athlete_id)
    if not stored_tokens:
        print("No stored tokens found")
        return None, None

    current_time = time.time()
    expires_at = stored_tokens.get('expires_at')



    # Check if token needs refresh (add 5 minute buffer)
    if expires_at and expires_at < current_time + 300:
        print("Token needs refresh")
        # Refresh the token
        new_tokens = refresh_token(stored_tokens['refresh_token'])
        if 'access_token' in new_tokens:
            print("Token refreshed successfully")
            # Save new tokens
            storage.save_strava_tokens(athlete_id, new_tokens)
            return new_tokens['access_token'], athlete_id
        print("Token refresh failed")
        return None, None

    print("Using existing token")
    return stored_tokens['access_token'], athlete_id
