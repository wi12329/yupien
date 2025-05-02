#!/usr/bin/env python
"""
Bot server script that runs on a different port than the main web server.
This script is called by the run_telegram_twitter_bot workflow.
"""

import os
import sys
import logging
import threading
import asyncio
from flask import Flask, render_template, jsonify
from bot import TelegramTwitterBot
from logger import logger

# Create Flask app for secondary port
bot_app = Flask(__name__)

# Global state to track bot status
bot_status = {
    "running": False,
    "last_error": None,
    "telegram_status": "Not started",
    "twitter_status": "Not connected",
    "last_tweet_time": None
}

# Global bot instance
bot_instance = None
bot_thread = None

def update_bot_status(running=False, telegram_status="Not started", twitter_status="Not connected", error=None):
    """Update the bot status information shown in the web UI"""
    bot_status["running"] = running
    bot_status["telegram_status"] = telegram_status
    bot_status["twitter_status"] = twitter_status
    
    if error:
        bot_status["last_error"] = str(error)
    
    logger.info(f"Bot status updated: {running}, {telegram_status}, {twitter_status}")

# Flask routes
@bot_app.route('/')
def index():
    """Home page route for the bot server."""
    return render_template('bot_server.html', status=bot_status)

@bot_app.route('/api/status')
def api_status():
    """API endpoint to get bot status."""
    return jsonify(bot_status)

@bot_app.route('/api/restart', methods=['POST'])
def api_restart():
    """API endpoint to restart the bot."""
    global bot_thread
    
    # Stop the existing bot if it's running
    if bot_thread and bot_thread.is_alive():
        update_bot_status(False, "Stopping bot...", "Disconnecting...")
        # We can't easily stop the bot from here, so we'll just let it run
        # and start a new one
    
    # Start a new bot
    bot_thread = start_bot_thread()
    
    return jsonify({
        "status": "Bot restart initiated", 
        "message": "Bot is being restarted"
    })

async def run_bot():
    """Async function to run the Telegram-X integration bot."""
    global bot_instance
    
    logger.info("Initializing Telegram-X integration bot...")
    
    try:
        # Create and start the bot
        bot_instance = TelegramTwitterBot()
        update_bot_status(True, "Starting...", "Connecting...")
        await bot_instance.start()
    except Exception as e:
        error_msg = str(e)
        logger.critical(f"Fatal error in bot: {error_msg}", exc_info=True)
        update_bot_status(False, "Error", "Error", error_msg)
        if bot_instance:
            try:
                await bot_instance.stop()
            except:
                pass

def start_bot_thread():
    """Start the bot in a separate thread."""
    def run_async_bot():
        asyncio.run(run_bot())
    
    # Start in a new thread to not block the Flask app
    thread = threading.Thread(target=run_async_bot)
    thread.daemon = True
    thread.start()
    return thread

# Create a template for the bot server page
os.makedirs('templates', exist_ok=True)
with open('templates/bot_server.html', 'w') as f:
    f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram-X Bot Server</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light">
    <div class="container mt-5">
        <h1 class="mb-4">Telegram-X Bot Server</h1>
        <div class="alert alert-warning">
            This is the dedicated bot server running on port 5001. For the main web interface, visit port 5000.
        </div>
        
        <div class="card bg-dark border-secondary mb-4">
            <div class="card-header">
                <h2 class="h5 mb-0">Bot Status</h2>
            </div>
            <div class="card-body">
                <div class="d-flex justify-content-between mb-3">
                    <span>Bot Running:</span>
                    <span id="bot-running" class="badge bg-success">{{ status.running }}</span>
                </div>
                <div class="d-flex justify-content-between mb-3">
                    <span>Telegram Status:</span>
                    <span id="telegram-status">{{ status.telegram_status }}</span>
                </div>
                <div class="d-flex justify-content-between mb-3">
                    <span>Twitter Status:</span>
                    <span id="twitter-status">{{ status.twitter_status }}</span>
                </div>
                {% if status.last_error %}
                <div class="alert alert-danger mt-3">
                    <strong>Last Error:</strong> {{ status.last_error }}
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="card bg-dark border-secondary">
            <div class="card-header">
                <h2 class="h5 mb-0">Administration</h2>
            </div>
            <div class="card-body">
                <button id="restart-button" class="btn btn-warning">Restart Bot</button>
            </div>
        </div>
    </div>
    
    <script>
        // Update status every 5 seconds
        setInterval(() => {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('bot-running').textContent = data.running;
                    document.getElementById('bot-running').className = data.running ? 'badge bg-success' : 'badge bg-danger';
                    document.getElementById('telegram-status').textContent = data.telegram_status;
                    document.getElementById('twitter-status').textContent = data.twitter_status;
                });
        }, 5000);
        
        // Restart button functionality
        document.getElementById('restart-button').addEventListener('click', () => {
            fetch('/api/restart', {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                alert('Bot restart initiated. Please wait a moment for the bot to reconnect.');
            });
        });
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" TELEGRAM-X BOT SERVER (PORT 5001)")
    print("="*50 + "\n")
    
    try:
        # Start the bot in a background thread
        logger.info("Starting bot thread...")
        bot_thread = start_bot_thread()
        
        # Run the Flask app on a different port
        logger.info("Starting bot server on port 5001...")
        bot_app.run(host="0.0.0.0", port=5001, debug=False)
    except KeyboardInterrupt:
        logger.info("Bot server interrupted by user")
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        raise