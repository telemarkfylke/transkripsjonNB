#!/usr/bin/env python3
"""
Transkripsjon SharePoint Library
Library with functions for SharePoint operations using Microsoft Graph API
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

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


def lastOppTilSP(upn: str) -> Optional[str]:
    """
    Upload Faktura_HF_August.pdf to SharePoint document library defined in .env.
    Set exclusive permissions so only the specified UPN can access the file.
    
    Args:
        upn: User Principal Name (email) that should have exclusive access to the file
    
    Returns:
        str: SharePoint URL of uploaded file if successful, None if failed
    """
    file_path = "./dokumenter/Mistral.pdf"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
    
    try:
        # Get authentication token
        token = hentToken()
        if not token:
            return None
        
        # Get site ID
        site_id = _hentSiteId(token)
        if not site_id:
            return None
        
        # Get transkripsjoner document library
        headers = {'Authorization': f'Bearer {token}'}
        drives_url = f"{GRAPH_URL}/sites/{site_id}/drives"
        drives_response = requests.get(drives_url, headers=headers)
        drives_response.raise_for_status()
        
        # Find the specified document library
        drives = drives_response.json()['value']
        drive_id = None
        for drive in drives:
            if drive['name'] == DEFAULT_LIBRARY:
                drive_id = drive['id']
                break
        
        if not drive_id:
            print(f"❌ Could not find '{DEFAULT_LIBRARY}' document library")
            return None
        
        # Upload file
        file_name = os.path.basename(file_path)
        upload_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/octet-stream'
        }
        
        upload_url = f"{GRAPH_URL}/sites/{site_id}/drives/{drive_id}/root:/{file_name}:/content"
        
        with open(file_path, 'rb') as f:
            response = requests.put(upload_url, headers=upload_headers, data=f)
        
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Uploaded: {file_name}")
        
        # Set exclusive permissions for the specified UPN
        file_id = result['id']
        success = _settTilganger(token, site_id, drive_id, file_id, upn)
        
        if success:
            print(f"✅ Granted exclusive access to: {upn}")
        else:
            print(f"⚠️ File uploaded but permission setting may have failed")
        
        # Generate a secure sharing link
        sharing_link = _lagDelingslenke(token, site_id, drive_id, file_id)
        
        if sharing_link:
            print(f"🔗 Secure sharing link created")
            return sharing_link
        else:
            print("⚠️ Using direct file URL (may have broader access)")
            return result['webUrl']
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None