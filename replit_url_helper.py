"""
Replit URL helper - helps determine the proper Replit URL for ping services.
This script will help identify your app's public-facing URL.
"""

import os
import socket
import requests
import time

def get_replit_url():
    """
    Get the public-facing URL of this Replit application.
    Returns the URL or None if it can't be determined.
    """
    # First, try to get it from environment variables
    replit_url = os.environ.get('REPLIT_DB_URL', '')
    if replit_url:
        # Extract the hostname from the DB URL
        try:
            # The DB URL is usually like https://kv.replit.com/v0/...
            # We need to extract our own repl's URL
            parts = replit_url.split('/')
            if len(parts) >= 3:
                hostname = parts[2]  # e.g., kv.replit.com
                if 'replit' in hostname:
                    repl_id = hostname.split('.')[0]
                    return f"https://{repl_id}.replit.app"
        except Exception as e:
            print(f"Error parsing REPLIT_DB_URL: {e}")
    
    # Try another approach to get the Replit app URL
    try:
        # Try to get the Repl ID from the REPL_ID environment variable
        repl_id = os.environ.get('REPL_ID')
        repl_owner = os.environ.get('REPL_OWNER')
        repl_slug = os.environ.get('REPL_SLUG')
        
        if repl_id:
            return f"https://{repl_id}.id.replit.app"
        
        if repl_owner and repl_slug:
            return f"https://{repl_slug}.{repl_owner}.repl.co"
    except Exception as e:
        print(f"Error getting Replit environment variables: {e}")
    
    # As a last resort, try to get the hostname via socket
    try:
        hostname = socket.gethostname()
        if 'replit' in hostname:
            return f"https://{hostname}"
    except Exception as e:
        print(f"Error getting hostname: {e}")
    
    # If all else fails, return None
    return None

def test_replit_url():
    """
    Test if the Replit URL is accessible.
    """
    url = get_replit_url()
    if not url:
        print("Could not determine Replit URL.")
        return False
    
    print(f"Testing Replit URL: {url}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"✅ URL is accessible! Status code: {response.status_code}")
            return True
        else:
            print(f"❌ URL returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing URL: {e}")
        return False

if __name__ == "__main__":
    # Get and print the Replit URL
    url = get_replit_url()
    print(f"Detected Replit URL: {url}")
    
    # Test the URL
    test_replit_url()