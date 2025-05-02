# Setting Up Your Bot with PythonAnywhere

This guide walks you through setting up your bot on PythonAnywhere (free plan) so it stays online 24/7.

## Step 1: Create a PythonAnywhere Account

1. Go to [PythonAnywhere.com](https://www.pythonanywhere.com/)
2. Click "Pricing & Signup" 
3. Select "Create a Beginner account" (free)
4. Complete the registration process

## Step 2: Set Up the Bot Watcher Script

1. After logging in, navigate to the "Files" tab in the dashboard
2. Click "New file" in the Files page
3. Name it `replit_stalker.py` and click "OK"
4. In the editor that opens, paste the entire content of the `replit_stalker.py` file from your Replit project
5. Click "Save" to save the file

## Step 3: Create a Scheduled Task

1. Go to the "Tasks" tab in the dashboard
2. In the "Create a new scheduled task" section:
   - Set the time you want it to run daily (free accounts allow one daily task)
   - For "Command to run", enter:
     ```
     python3 /home/YourUsername/replit_stalker.py
     ```
     (Replace `YourUsername` with your actual PythonAnywhere username)
3. Click "Create" to schedule the task

## Step 4: Test Your Setup

1. Go back to the "Consoles" tab
2. Start a new "Bash" console
3. Run the following command to test your script:
   ```
   python3 replit_stalker.py
   ```
4. You should see output confirming that your Replit bot was successfully reached

## Step 5: Verify Uptime

1. Now your bot should stay online even when you're not using Replit
2. Your PythonAnywhere task will ping your bot daily to keep it awake
3. Check your Telegram bot regularly to make sure it's responding

## Pro Tips

- **For More Frequent Pings**: The free tier limits you to one scheduled task per day. Consider upgrading to the "Hacker" plan ($5/month) for hourly pings.
- **Multiple Free Accounts**: You can create multiple free PythonAnywhere accounts and schedule them to run at different times of day for more frequent pings.
- **GitHub Actions Supplement**: Use GitHub Actions (free) in addition to PythonAnywhere for more frequent pings.

## Troubleshooting

- If the script fails to connect to your bot, your Replit URL may have changed
- The script is designed to detect URL changes, but it may need time to adapt
- Run the script manually to force it to find the new URL

Remember that if your PythonAnywhere free account becomes inactive (no logins for 3 months), it may be deleted. Log in periodically to keep it active.