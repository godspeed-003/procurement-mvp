# SmartProcure Agent

An AI-powered procurement automation system that helps businesses discover and contact suppliers efficiently.

## Overview

SmartProcure Agent automates the procurement workflow with these key phases:
1. **Requirements Intake** - Capture detailed procurement needs via text or voice
2. **Supplier Discovery** - Find and rank relevant suppliers through web scraping
3. **Supplier Outreach** - Contact suppliers via email and SMS
4. **Negotiation & Confirmation** - (Coming soon)
5. **Reporting & Handoff** - (Coming soon)

## Setup Instructions

### Environment Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install livekit-agents livekit-plugins-deepgram livekit-plugins-google livekit-plugins-cartesia livekit-plugins-silero python-dotenv crawl4ai mailjet-rest twilio
   ```

3. Configure environment variables:
   - Copy the `.env.example` file to `.env`
   - Fill in all required API keys and credentials

## Running the Components

### 1. Main Application

The main application orchestrates the entire procurement workflow:

```bash
python main.py
```

Options:
- `python main.py text` - Run in text mode (default)
- `python main.py voice` - Run in voice mode
- `python main.py help` - Show help information

### 2. Voice Intake Only

To run only the voice/text requirements gathering component:

```bash
python voice_intake.py
```

This will start the procurement requirements gathering assistant. The assistant will:
- Ask for product types, quantity, delivery timeline, etc.
- Generate a structured requirements document
- Save the session data for later use

### 3. Supplier Discovery Only

To run only the supplier discovery component:

```bash
python scraper.py
```

This will:
- Use a test set of procurement requirements (modify the script to use custom requirements)
- Search for suppliers on IndiaMART
- Generate optimized search keywords
- Extract and rank supplier information
- Save results to a JSON file in the `data` directory

### 4. Supplier Outreach Only

To run the supplier outreach tool for a specific supplier list:

```bash
python run_outreach.py path/to/suppliers.json
```

Options:
- `--live` - Run in live mode to actually send emails and SMS (default is demo mode)

Example:
```bash
# Demo mode (no actual emails/SMS sent)
python run_outreach.py d:/AI/agent/procurement/data/suppliers_20250613_003428.json

# Live mode (real emails/SMS sent)
python run_outreach.py d:/AI/agent/procurement/data/suppliers_20250613_003428.json --live
```

## Configuration

### Email Configuration (Mailjet)

The system uses Mailjet for sending emails. Configure the following in your `.env` file:

```
MJ_API=your_mailjet_api_key
MJ_secret=your_mailjet_api_secret
MJ_FROM_EMAIL=your_sender_email@example.com
MJ_FROM_NAME=Procurement Team
```

### SMS Configuration (Twilio)

For SMS functionality, configure Twilio credentials in your `.env` file:

```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

## Directory Structure

```
d:/AI/agent/procurement/
├── .env                  # Environment variables
├── main.py               # Main orchestrator application
├── voice_intake.py       # Requirements intake module
├── scraper.py            # Supplier discovery module
├── outreach.py           # Supplier outreach module
├── run_outreach.py       # CLI tool for supplier outreach
├── data/                 # Supplier data storage
│   └── suppliers_*.json  # Discovered suppliers
└── sessions/             # Intake session storage
    └── session_*.json    # User session data
```

## Development Notes

- The application is designed to run in "demo mode" by default, meaning it won't actually send emails or SMS.
- To send real communications, use the `--live` flag with the outreach tool or set `demo_mode=False` in the code.
- All supplier data is saved in the `data` directory for reference and future use.
- Session data from requirements intake is saved in the `sessions` directory.

## Troubleshooting

### Mailjet Issues

If you encounter Mailjet authentication errors:
1. Verify your API key and secret in the `.env` file
2. Ensure your Mailjet account is active
3. Check if your sender email is verified in Mailjet

### Twilio Issues

If SMS sending fails:
1. Verify your Twilio credentials
2. Check if your Twilio phone number is active
3. Ensure phone numbers are in the correct format (+[country code][number])
4. For trial accounts, verify that the recipient numbers are confirmed in your Twilio account

## License

Copyright © 2025 ThinkLoop AI. All rights reserved.
