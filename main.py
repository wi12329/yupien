import os
import sys
import logging
import threading
import subprocess
import asyncio
import time
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from logger import logger
from bot import TelegramTwitterBot
from status_manager import get_status
from models import db, TweetQueue
from keep_alive import run_keep_alive

# Check if this script was run directly from the bot workflow
# We know in this case because our workflows are configured to run different commands
script_name = os.path.basename(sys.argv[0]) if len(sys.argv) > 0 else ""
if script_name == "main.py" and 'REPL_ID' in os.environ:
    # Check if port 5000 is already in use (meaning we're in the second workflow)
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('0.0.0.0', 5000))
        # Port is free, this is the primary workflow
        s.close()
    except socket.error:
        # Port is in use, this is the secondary workflow - run the bot only
        s.close()
        logger.info("Port 5000 is already in use. Starting bot-only mode...")
        try:
            # Run the robust Telegram bot instead of importing it
            # This is important to avoid event loop conflicts
            logger.info("Running the Telegram-X bot subprocess...")
            import subprocess
            process = subprocess.Popen([sys.executable, "run_telegram_bot.py"])
            logger.info(f"Telegram-X bot process started with PID {process.pid}")
            
            # Wait for the subprocess
            process.wait()
            
            sys.exit(process.returncode)
        except Exception as e:
            logger.error(f"Failed to start Telegram-X bot: {e}")
            sys.exit(1)

# Special case if explicitly called with the flag
if len(sys.argv) > 1 and sys.argv[1] == "--bot-only":
    # We're being called with a flag to run just the bot
    try:
        logger.info("Starting bot in bot-only mode...")
        import run_bot_only
        sys.exit(0)  # Exit after running bot_runner
    except Exception as e:
        logger.error(f"Failed to start bot_runner: {e}")
        sys.exit(1)

# Create Flask app
app = Flask(__name__)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# Create all tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created")

# Global state to track bot status
bot_status = {
    "running": False,
    "last_error": None,
    "telegram_status": "Not started",
    "twitter_status": "Not connected",
    "last_tweet_time": None
}

def update_bot_status(running=False, telegram_status="Not started", twitter_status="Not connected", error=None):
    """Update the bot status information shown in the web UI"""
    bot_status["running"] = running
    bot_status["telegram_status"] = telegram_status
    bot_status["twitter_status"] = twitter_status
    
    if error:
        bot_status["last_error"] = str(error)
    
    logger.info(f"Bot status updated: {running}, {telegram_status}, {twitter_status}")

# Flask routes
@app.route('/')
def index():
    """Home page route."""
    # Get the status from the shared status file
    current_status = get_status()
    return render_template('index.html', status=current_status)

@app.route('/ping')
def ping():
    """Enhanced endpoint for uptime monitoring services to ping."""
    # Log that the ping endpoint was accessed with User-Agent
    user_agent = request.headers.get('User-Agent', '')
    logger.info(f"Ping endpoint accessed from IP: {request.remote_addr}, User-Agent: {user_agent}")
    
    # Get current status
    current_status = get_status()
    
    # Create a more detailed response for monitoring services
    response = {
        "status": "OK",
        "timestamp": time.time(),
        "bot_running": current_status.get("running", False),
        "telegram_status": current_status.get("telegram_status", "Unknown"),
        "version": "1.0.0"
    }
    
    # Return JSON with 200 status code for better monitoring
    return jsonify(response), 200

# Add a plain text version for simple monitoring services
@app.route('/ping.txt')
def ping_txt():
    """Simple plain text endpoint for basic monitoring services."""
    user_agent = request.headers.get('User-Agent', '')
    logger.info(f"Plain ping endpoint accessed from IP: {request.remote_addr}, User-Agent: {user_agent}")
    return "OK", 200
    
# Add a dedicated UptimeRobot health check page
@app.route('/health')
def health_check():
    """Detailed health check page for UptimeRobot and other monitoring services."""
    user_agent = request.headers.get('User-Agent', '')
    logger.info(f"Health check accessed from IP: {request.remote_addr}, User-Agent: {user_agent}")
    
    # Get current status
    current_status = get_status()
    
    # Get uptime information
    uptime_seconds = int(time.time() - os.path.getmtime(__file__))
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    
    # Create HTML response
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bot Health Check</title>
        <meta name="robots" content="noindex">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            .status {{ padding: 10px; margin-bottom: 10px; border-radius: 5px; }}
            .ok {{ background-color: #d4edda; color: #155724; }}
            .warning {{ background-color: #fff3cd; color: #856404; }}
            .error {{ background-color: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <h1>Telegram-X Bot Health Check</h1>
        <div class="status {'ok' if current_status.get('running', False) else 'error'}">
            <strong>Status:</strong> {'ONLINE' if current_status.get('running', False) else 'OFFLINE'}
        </div>
        <div>
            <strong>Uptime:</strong> {days}d {hours}h {minutes}m
        </div>
        <div>
            <strong>Telegram Status:</strong> {current_status.get('telegram_status', 'Unknown')}
        </div>
        <div>
            <strong>Twitter Status:</strong> {current_status.get('twitter_status', 'Unknown')}
        </div>
        <div>
            <strong>Last Updated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}
        </div>
        <p>For monitoring services: This page returns HTTP 200 if the bot is running properly.</p>
    </body>
    </html>
    """
    
    return html, 200

@app.route('/api/status')
def api_status():
    """API endpoint to get bot status."""
    # Get the status from the shared status file instead of using the local variable
    current_status = get_status()
    
    # Calculate a "last updated" timestamp in human-readable format
    if "last_updated" in current_status:
        last_update_time = current_status["last_updated"]
        time_diff = time.time() - last_update_time
        
        if time_diff < 60:  # Less than a minute
            current_status["last_updated_human"] = "Just now"
        elif time_diff < 3600:  # Less than an hour
            minutes = int(time_diff / 60)
            current_status["last_updated_human"] = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif time_diff < 86400:  # Less than a day
            hours = int(time_diff / 3600)
            current_status["last_updated_human"] = f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(time_diff / 86400)
            current_status["last_updated_human"] = f"{days} day{'s' if days != 1 else ''} ago"
    
    # Add queue information
    try:
        with app.app_context():
            wait_time = TweetQueue.time_until_next_available()
            if wait_time > 0:
                minutes = int(wait_time / 60)
                seconds = int(wait_time % 60)
                current_status["queue_status"] = f"Wait time: {minutes}m {seconds}s"
                current_status["can_tweet"] = False
            else:
                current_status["queue_status"] = "Ready to tweet"
                current_status["can_tweet"] = True
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        current_status["queue_status"] = "Queue status unknown"
        current_status["can_tweet"] = False
    
    return jsonify(current_status)

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """API endpoint to restart the bot."""
    # For now, we'll just update the status
    # We won't start another bot to avoid conflicts with the run_telegram_twitter_bot workflow
    bot_status["telegram_status"] = "Bot restart requested"
    bot_status["last_error"] = None
    return jsonify({
        "status": "Bot restart requested", 
        "note": "Use the Replit workspace to restart the bot workflow"
    })

@app.route('/keep-alive')
def browser_ping_page():
    """Serve the browser-based pinger page for manual monitoring."""
    logger.info(f"Browser ping page accessed from IP: {request.remote_addr}, User-Agent: {request.headers.get('User-Agent', '')}")
    
    # Read the HTML file
    try:
        with open('server_ping.html', 'r') as f:
            html_content = f.read()
        return html_content
    except Exception as e:
        logger.error(f"Error reading browser ping page: {e}")
        return "Error loading page. Please check the logs.", 500

# Create the templates directory and index.html file if they don't exist
os.makedirs('templates', exist_ok=True)
if not os.path.exists('templates/index.html'):
    with open('templates/index.html', 'w') as f:
        f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram-X Integration Bot</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light">
    <div class="container mt-5">
        <h1 class="mb-4">Telegram-X Integration Bot</h1>
        
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
                <div class="d-flex justify-content-between mb-3">
                    <span>Queue Status:</span>
                    <span id="queue-status">{{ status.queue_status|default("Unknown") }}</span>
                </div>
                {% if status.last_error %}
                <div class="alert alert-danger mt-3">
                    <strong>Last Error:</strong> {{ status.last_error }}
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="card bg-dark border-secondary mb-4">
            <div class="card-header">
                <h2 class="h5 mb-0">Bot Commands</h2>
            </div>
            <div class="card-body">
                <p>Your Telegram bot accepts the following commands:</p>
                <ul class="list-group list-group-flush bg-dark">
                    <li class="list-group-item bg-dark text-light"><code>/tweet [message]</code> - Post a tweet to X</li>
                    <li class="list-group-item bg-dark text-light"><code>/status</code> - Check bot status</li>
                    <li class="list-group-item bg-dark text-light"><code>/help</code> - Show help information</li>
                </ul>
            </div>
        </div>
        
        <div class="card bg-dark border-secondary">
            <div class="card-header">
                <h2 class="h5 mb-0">Administration</h2>
            </div>
            <div class="card-body">
                <button id="restart-button" class="btn btn-warning me-2">Restart Bot</button>
                <a href="/keep-alive" class="btn btn-info">Open Keep-Alive Page</a>
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
                    
                    // Update queue status
                    if (data.queue_status) {
                        const queueStatus = document.getElementById('queue-status');
                        queueStatus.textContent = data.queue_status;
                        
                        // Change the style based on whether tweeting is allowed
                        if (data.can_tweet) {
                            queueStatus.className = 'badge bg-success';
                        } else {
                            queueStatus.className = 'badge bg-warning text-dark';
                        }
                    }
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

# This file no longer handles bot startup.
# All bot functionality is in bot_runner.py

# We don't automatically start the bot here anymore, to avoid conflicts 
# with the separate bot_runner.py process

def start_queue_processor():
    """Start the queue processor in a background thread."""
    try:
        logger.info("Starting queue processor thread...")
        from queue_processor import process_queue
        
        def queue_processor_thread():
            """Background thread function to run the queue processor periodically."""
            while True:
                try:
                    # Process pending tweets
                    with app.app_context():
                        logger.info("Running queue processor...")
                        process_queue()
                        logger.info("Queue processor completed cycle")
                except Exception as e:
                    logger.error(f"Error in queue processor thread: {e}")
                
                # Sleep for 2 minutes before checking again
                time.sleep(120)
        
        # Start the thread as a daemon (will exit when the main program exits)
        thread = threading.Thread(target=queue_processor_thread, daemon=True)
        thread.start()
        logger.info("Queue processor thread started successfully!")
        return thread
    except Exception as e:
        logger.error(f"Error starting queue processor: {e}")
        return None

if __name__ == "__main__":
    # Only run Flask app, not the bot
    try:
        # Update status to show we're just running the web UI
        bot_status["telegram_status"] = "Bot not started from web UI (using workflow instead)"
        bot_status["twitter_status"] = "Not connected from web UI (using workflow instead)"
        logger.info("Running Flask app only - bot should be started from the run_telegram_twitter_bot workflow")
        
        # Start the queue processor thread first
        queue_processor_thread = start_queue_processor()
        logger.info("Tweet queue processor is now running in the background")
        
        # Start the keep-alive server on port 8080
        # This will help prevent Replit from putting the bot to sleep
        try:
            logger.info("Starting keep-alive server on port 8080")
            run_keep_alive()
            logger.info("Keep-alive server started successfully")
            
            # Start the self-pinger to keep the app alive without external services
            try:
                from self_ping import start_self_pinger
                logger.info("Starting self-pinger thread...")
                self_ping_thread = start_self_pinger()
                logger.info("Self-pinger thread started successfully!")
            except Exception as ping_error:
                logger.error(f"Error starting self-pinger: {ping_error}")
        except Exception as e:
            logger.error(f"Error starting keep-alive server: {e}")
        
        # We don't start the bot here anymore - use bot_runner.py via workflow instead
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        raise
