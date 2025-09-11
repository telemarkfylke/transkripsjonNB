#!/usr/bin/env python3
"""
Transkripsjon SharePoint Library
Library with functions for SharePoint operations using Microsoft Graph API
"""

import os
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Load environment variables
load_dotenv()

# Configuration from .env
TENANT_ID = os.getenv('TENANT_ID')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
SHAREPOINT_SITE_URL = os.getenv('SHAREPOINT_SITE_URL')
DEFAULT_LIBRARY = os.getenv('DEFAULT_LIBRARY', 'Documents')
GRAPH_URL = "https://graph.microsoft.com/v1.0"


def hentToken() -> Optional[str]:
    """
    Authenticate to Microsoft Graph using app credentials and return access token.
    
    Returns:
        str: Access token if successful, None if failed
    """
    try:
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = requests.post(token_url, data=token_data, headers=headers)
        response.raise_for_status()
        
        token_info = response.json()
        access_token = token_info['access_token']
        
        return access_token
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None


def _hentSiteId(token: str) -> Optional[str]:
    """Get SharePoint site ID from URL."""
    try:
        parts = SHAREPOINT_SITE_URL.replace('https://', '').split('/')
        hostname = parts[0]
        site_path = '/'.join(parts[1:])
        
        headers = {'Authorization': f'Bearer {token}'}
        url = f"{GRAPH_URL}/sites/{hostname}:/{site_path}"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()['id']
        
    except Exception as e:
        print(f"❌ Failed to get site ID: {e}")
        return None


def _settTilganger(token: str, site_id: str, drive_id: str, file_id: str, upn: str) -> bool:
    """Grant read permission to specified UPN on a file."""
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Grant read permission to the specified user
        permission_data = {
            'recipients': [{'email': upn}],
            'roles': ['read'],
            'requireSignIn': True,
            'sendInvitation': False
        }
        
        invite_url = f"{GRAPH_URL}/sites/{site_id}/drives/{drive_id}/items/{file_id}/invite"
        invite_response = requests.post(invite_url, headers=headers, json=permission_data)
        
        if invite_response.status_code in [200, 201]:
            return True
        else:
            print(f"⚠️ Permission grant response: {invite_response.status_code}")
            print(f"Response: {invite_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Permission setting failed: {e}")
        return False


def _lagDelingslenke(token: str, site_id: str, drive_id: str, file_id: str) -> Optional[str]:
    """Create a sharing link that respects the file's permissions."""
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Create a sharing link that respects existing permissions
        sharing_data = {
            'type': 'view',
            'scope': 'users'  # Only users with permissions can access
        }
        
        url = f"{GRAPH_URL}/sites/{site_id}/drives/{drive_id}/items/{file_id}/createLink"
        response = requests.post(url, headers=headers, json=sharing_data)
        
        if response.status_code in [200, 201]:
            return response.json()['link']['webUrl']
        else:
            print(f"⚠️ Sharing link creation failed: {response.status_code}")
            return None
        
    except Exception as e:
        print(f"❌ Sharing link creation failed: {e}")
        return None


