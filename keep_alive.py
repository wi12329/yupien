"""
Keep-alive script to prevent Replit from shutting down the bot.
This script creates a simple web server that can be pinged by an external
service (like UptimeRobot) to keep the repl active.
"""

import os
import threading
import time
import logging
from flask import Flask

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create the Flask app
keep_alive_app = Flask(__name__)

@keep_alive_app.route('/ping')
def ping():
    """Simple endpoint for monitoring services to ping."""
    return "OK", 200

@keep_alive_app.route('/')
def home():
    """Home page with status of the bot."""
    status_info = "Bot is running"
    
    # Try to read current status from status file
    try:
        if os.path.exists('bot_status.json'):
            import json
            with open('bot_status.json', 'r') as f:
                status = json.load(f)
                telegram_status = status.get('telegram_status', 'Unknown')
                twitter_status = status.get('twitter_status', 'Unknown')
                last_updated = status.get('last_updated', 0)
                
                # Calculate time since last update
                time_diff = time.time() - last_updated
                time_str = f"{int(time_diff // 60)}m {int(time_diff % 60)}s ago"
                
                status_info = f"""
                <p><strong>Bot Status:</strong></p>
                <p>Telegram: {telegram_status}</p>
                <p>Twitter: {twitter_status}</p>
                <p>Last updated: {time_str}</p>
                """
    except Exception as e:
        status_info = f"Bot is running (Status error: {str(e)})"
    
    # Get the Replit URL from environment
    replit_url = os.environ.get('REPLIT_SLUG', 'your-replit-project')
    replit_owner = os.environ.get('REPLIT_OWNER', 'owner')
    
    # Construct the full URL
    full_url = f"https://{replit_url}.{replit_owner}.repl.co"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram-X Bot - Keep Alive</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            .ping-url {{
                padding: 10px;
                background-color: #2d2d2d;
                border-radius: 4px;
                font-family: monospace;
                margin: 15px 0;
                word-break: break-all;
            }}
            .setup-steps {{
                margin-top: 30px;
                border-top: 1px solid #444;
                padding-top: 20px;
            }}
            .setup-steps h3 {{
                margin-top: 0;
            }}
        </style>
    </head>
    <body class="bg-dark text-light">
        <div class="container mt-5">
            <h1 class="mb-4">Telegram-X Bot Keep-Alive Service</h1>
            <div class="alert alert-success">
                <strong>Keep-alive service is active!</strong> This helps prevent your bot from sleeping.
            </div>
            
            <div class="card bg-dark border-secondary mb-4">
                <div class="card-header">
                    <h2 class="h5 mb-0">Bot Status</h2>
                </div>
                <div class="card-body">
                    {status_info}
                    <div class="mt-3">
                        <span class="badge bg-success">Keep-alive server: Running</span>
                    </div>
                </div>
            </div>
            
            <div class="card bg-dark border-secondary mb-4">
                <div class="card-header">
                    <h2 class="h5 mb-0">24/7 Setup Instructions</h2>
                </div>
                <div class="card-body">
                    <p>For your bot to run 24/7, you need to set up an <strong>external pinging service</strong> 
                    that will keep your Replit project awake.</p>
                    
                    <h3 class="h6 mt-4">URL to ping:</h3>
                    <div class="ping-url">
                        {full_url}/ping
                    </div>
                    
                    <div class="setup-steps">
                        <h3 class="h6">How to set up 24/7 operation:</h3>
                        <ol>
                            <li>Create a free account on <a href="https://uptimerobot.com/" target="_blank" class="text-info">UptimeRobot</a></li>
                            <li>Add a new monitor (HTTP(s) type)</li>
                            <li>Enter the ping URL: <code>{full_url}/ping</code></li>
                            <li>Set the monitoring interval to 5 minutes</li>
                            <li>Save your monitor</li>
                        </ol>
                        <p class="mt-3">This will ping your bot every 5 minutes, preventing Replit from putting it to sleep.</p>
                        
                        <div class="alert alert-warning mt-3">
                            <strong>Important:</strong> Make sure both workflows (web server and bot) are running in 
                            Replit. Your bot will only stay active 24/7 if:
                            <ol class="mt-2 mb-0">
                                <li>Both workflows are running</li>
                                <li>You've set up the external pinging service</li>
                                <li>Your Replit account has sufficient resources allocated</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="text-muted small mt-4">
                <p>Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Keep-alive server running on port 8080</p>
            </div>
        </div>
    </body>
    </html>
    """

def run_keep_alive():
    """Run the keep-alive server in a separate thread."""
    # Use a different port than the main app to avoid conflicts
    port = int(os.environ.get('KEEP_ALIVE_PORT', 8080))
    logger.info(f"Starting keep-alive server on port {port}")
    
    # Start the Flask app in a thread
    threading.Thread(target=lambda: keep_alive_app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )).start()
    
    logger.info("Keep-alive server started")

if __name__ == "__main__":
    run_keep_alive()