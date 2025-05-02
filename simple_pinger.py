"""
Ultra-Simple Bot Pinger - Keep your Replit bot running 24/7
Extremely minimal version with NO dependencies - just standard Python libraries
"""

import time
import urllib.request
import random
import datetime
import socket

# === CONFIGURATION ===
URL = "https://9aff7d4d-c131-4692-a733-762029a6d8e4-00-378m7x1uk4bp1.kirk.replit.dev/health"

# Ping interval (4-5 minutes)
MIN_INTERVAL = 240
MAX_INTERVAL = 300

def ping():
    """Send ping to URL"""
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pinging {URL}...")
    try:
        # Set a timeout so it doesn't hang forever
        response = urllib.request.urlopen(URL, timeout=20)
        code = response.getcode()
        if code == 200:
            print(f"Success! Status code: {code}")
            return True
        else:
            print(f"Error: Status code {code}")
            return False
    except socket.timeout:
        print("Error: Connection timed out")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    """Main loop"""
    print("=" * 50)
    print("YupienBot Simple Pinger Started")
    print("=" * 50)
    print("Keep this script running to maintain your bot online")
    print("Press Ctrl+C to stop")
    
    success = 0
    failure = 0
    
    try:
        while True:
            if ping():
                success += 1
            else:
                failure += 1
                
            total = success + failure
            if total > 0:
                uptime = (success / total) * 100
                print(f"Stats: {success} successes, {failure} failures ({uptime:.1f}% uptime)")
            
            # Random interval
            interval = random.randint(MIN_INTERVAL, MAX_INTERVAL)
            next_time = datetime.datetime.now() + datetime.timedelta(seconds=interval)
            print(f"Next ping in {interval} seconds (at {next_time.strftime('%H:%M:%S')})")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nPinger stopped by user")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        time.sleep(60)
        main()  # Restart on error

if __name__ == "__main__":
    main()