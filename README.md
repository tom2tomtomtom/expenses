# Email Receipt Scraper - Setup and Usage Guide

## Overview

Email Receipt Scraper is a Python application that automatically extracts receipt data from your email accounts, parses the information, and stores it in a Google Spreadsheet. This tool is perfect for tracking expenses, organizing receipts for tax purposes, or analyzing your spending habits.

The application supports:
- Multiple email providers through both Gmail API and IMAP protocols
- Automatic receipt detection and data extraction
- Parsing of key receipt information (vendor, date, total, tax, etc.)
- Storage of receipt data in Google Sheets
- Local backup of receipt data as JSON files

## Requirements

- Python 3.7 or higher
- Google account (for Gmail API and Google Sheets)
- Email account access (Gmail, Outlook, Yahoo, etc.)

## Installation

1. Clone or download the repository to your local machine:
   ```
   git clone https://github.com/yourusername/email-receipt-scraper.git
   cd email-receipt-scraper
   ```

2. Install the required dependencies:
   ```
   pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib beautifulsoup4 python-dateutil
   ```

## Configuration

### Google API Setup (for Gmail API and Google Sheets)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Gmail API and Google Sheets API for your project
4. Configure the OAuth consent screen:
   - Set the user type to "External"
   - Add the required scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/spreadsheets`
   - Add your email as a test user
5. Create OAuth 2.0 Client ID credentials:
   - Choose "Desktop app" as the application type
   - Download the credentials JSON file
   - Save it as `credentials.json` in the application directory

### Configuration File

Create a `config.json` file in the application directory with the following structure:

```json
{
  "email": {
    "auth_type": "gmail_api",
    "credentials_file": "credentials.json",
    "token_file": "token.json",
    "search_query": "subject:receipt OR subject:order confirmation",
    "max_emails": 50
  },
  "sheets": {
    "credentials_file": "credentials.json",
    "token_file": "sheets_token.json",
    "spreadsheet_id": null,
    "spreadsheet_title": "Receipt Tracker"
  },
  "output": {
    "save_receipts": true,
    "receipts_dir": "receipts"
  }
}
```

#### Configuration Options:

**Email Settings:**
- `auth_type`: Authentication method to use (`gmail_api` or `imap`)
- `credentials_file`: Path to Google API credentials file (for Gmail API)
- `token_file`: Path to save authentication token
- `email_address`: Email address (required for IMAP)
- `password`: Email password (required for IMAP)
- `imap_server`: IMAP server address (required for IMAP)
- `imap_port`: IMAP server port (default: 993)
- `search_query`: Query to search for receipt emails
- `max_emails`: Maximum number of emails to process

**Google Sheets Settings:**
- `credentials_file`: Path to Google API credentials file
- `token_file`: Path to save Sheets authentication token
- `spreadsheet_id`: ID of existing spreadsheet (leave null to create new)
- `spreadsheet_title`: Title for new spreadsheet

**Output Settings:**
- `save_receipts`: Whether to save receipt data locally (true/false)
- `receipts_dir`: Directory to save receipt data

## Usage

### Basic Usage

Run the application with the default configuration:

```
python email_receipt_scraper.py
```

On first run, the application will:
1. Open a browser window for Google authentication
2. Ask you to authorize the application
3. Create a new Google Spreadsheet (if none specified)
4. Fetch emails matching the search query
5. Parse receipt data from the emails
6. Add the data to the spreadsheet
7. Save receipt data locally (if enabled)

### Command Line Options

The application supports various command line options:

```
python email_receipt_scraper.py --help
```

Common options:
- `--config`: Path to configuration file
- `--save-config`: Save configuration to file
- `--auth-type`: Authentication type (`gmail_api` or `imap`)
- `--email`: Email address (for IMAP)
- `--password`: Email password (for IMAP)
- `--imap-server`: IMAP server (for IMAP)
- `--credentials`: Path to credentials.json file
- `--query`: Search query for emails
- `--max`: Maximum number of emails to fetch
- `--spreadsheet-id`: ID of an existing spreadsheet
- `--spreadsheet-title`: Title for a new spreadsheet
- `--verbose`: Enable verbose logging

### Examples

**Using Gmail API:**
```
python email_receipt_scraper.py --auth-type gmail_api --credentials my_credentials.json --query "subject:receipt after:2025/01/01" --max 100
```

**Using IMAP (for non-Gmail accounts):**
```
python email_receipt_scraper.py --auth-type imap --email user@example.com --password mypassword --imap-server imap.example.com
```

**Using an existing spreadsheet:**
```
python email_receipt_scraper.py --spreadsheet-id 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

## Testing

The application includes a test script to verify receipt parsing functionality:

```
python test_parser.py --input test_data
```

This will process sample receipt data in the `test_data` directory and output the parsed results to the `test_results` directory.

## Troubleshooting

### Authentication Issues

- For Gmail API: Make sure you've enabled the Gmail API in your Google Cloud project and downloaded the correct credentials.json file.
- For IMAP with Gmail: You may need to enable "Less secure app access" or use an App Password if you have 2-factor authentication enabled.
- For other IMAP providers: Verify your IMAP server address and port.

### Parsing Issues

If receipts aren't being parsed correctly:
- Check that your emails match the search query
- Verify that the emails contain receipt information in a recognizable format
- Try adjusting the confidence threshold in the code if needed

### Google Sheets Issues

- Ensure you've enabled the Google Sheets API in your Google Cloud project
- Verify that your OAuth consent screen includes the necessary scopes
- Check that you have sufficient permissions to create or modify spreadsheets

## Scheduling Regular Runs

To automatically run the scraper on a schedule:

### On Linux/Mac (using cron):

```
# Run daily at 2 AM
0 2 * * * cd /path/to/email-receipt-scraper && python email_receipt_scraper.py
```

### On Windows (using Task Scheduler):

1. Open Task Scheduler
2. Create a Basic Task
3. Set the trigger (e.g., daily)
4. Set the action to "Start a program"
5. Program/script: `python`
6. Arguments: `C:\path\to\email_receipt_scraper.py`
7. Start in: `C:\path\to\email-receipt-scraper`

## Security Considerations

- The application stores authentication tokens locally. Keep these files secure.
- For IMAP authentication, consider using environment variables or a secure password manager instead of storing passwords in the configuration file.
- Review the OAuth permissions carefully when authorizing the application.

## Limitations

- Receipt parsing accuracy depends on the format of the receipt emails.
- Some vendors may use formats that are difficult to parse automatically.
- The application currently focuses on common receipt fields and may not extract all details from specialized receipts.

## Future Enhancements

- Support for more email providers
- Enhanced receipt parsing with machine learning
- Categorization of expenses
- Data visualization and reporting
- Export to accounting software
