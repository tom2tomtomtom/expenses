#!/usr/bin/env python3
"""
Email Receipt Scraper

This script combines email authentication, receipt parsing, and Google Sheets integration
to scrape receipts from email accounts and store the data in a Google spreadsheet.
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Import custom modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.email_auth import create_authenticator, EmailAuthenticator
from src.receipt_parser import ReceiptParserFactory
from src.sheets_integration import GoogleSheetsIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("email_receipt_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email_receipt_scraper")

class EmailReceiptScraper:
    """Main class for email receipt scraping application"""
    
    def __init__(self, config_file: str = None):
        """
        Initialize the email receipt scraper
        
        Args:
            config_file: Path to configuration file
        """
        self.config = self._load_config(config_file)
        self.email_auth = None
        self.receipt_parser = ReceiptParserFactory.create_parser()
        self.sheets_integration = None
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "email": {
                "auth_type": "gmail_api",
                "credentials_file": "credentials.json",
                "token_file": "token.json",
                "email_address": None,
                "password": None,
                "imap_server": None,
                "imap_port": 993,
                "search_query": "subject:receipt OR subject:order confirmation",
                "max_emails": 100
            },
            "sheets": {
                "credentials_file": "credentials.json",
                "token_file": "sheets_token.json",
                "spreadsheet_id": None,
                "spreadsheet_title": "Receipt Tracker"
            },
            "output": {
                "save_receipts": True,
                "receipts_dir": "receipts"
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                
                # Merge user config with defaults
                for section in default_config:
                    if section in user_config:
                        for key in default_config[section]:
                            if key in user_config[section]:
                                default_config[section][key] = user_config[section][key]
            except Exception as e:
                logger.error(f"Error loading config file: {str(e)}")
        
        return default_config
    
    def save_config(self, config_file: str) -> bool:
        """Save current configuration to file"""
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config file: {str(e)}")
            return False
    
    def setup_email_auth(self) -> bool:
        """Set up email authentication"""
        email_config = self.config["email"]
        auth_type = email_config["auth_type"]
        
        if auth_type == "gmail_api":
            self.email_auth = create_authenticator(
                "gmail_api",
                credentials_file=email_config["credentials_file"],
                token_file=email_config["token_file"]
            )
        elif auth_type == "imap":
            self.email_auth = create_authenticator(
                "imap",
                email_address=email_config["email_address"],
                password=email_config["password"],
                imap_server=email_config["imap_server"],
                imap_port=email_config["imap_port"]
            )
        else:
            logger.error(f"Unknown auth type: {auth_type}")
            return False
        
        return self.email_auth.authenticate()
    
    def setup_sheets_integration(self) -> bool:
        """Set up Google Sheets integration"""
        sheets_config = self.config["sheets"]
        
        self.sheets_integration = GoogleSheetsIntegration(
            credentials_file=sheets_config["credentials_file"],
            token_file=sheets_config["token_file"]
        )
        
        if not self.sheets_integration.authenticate():
            return False
        
        # Create spreadsheet if needed
        if not sheets_config["spreadsheet_id"]:
            spreadsheet_id = self.sheets_integration.create_spreadsheet(
                sheets_config["spreadsheet_title"]
            )
            
            if spreadsheet_id:
                sheets_config["spreadsheet_id"] = spreadsheet_id
                logger.info(f"Created new spreadsheet: {self.sheets_integration.get_spreadsheet_url(spreadsheet_id)}")
            else:
                logger.error("Failed to create spreadsheet")
                return False
        
        return True
    
    def fetch_and_process_emails(self) -> List[Dict]:
        """Fetch emails and process them for receipt data"""
        if not self.email_auth or not self.email_auth.is_authenticated():
            logger.error("Email authentication not set up")
            return []
        
        email_config = self.config["email"]
        query = email_config["search_query"]
        max_emails = email_config["max_emails"]
        
        logger.info(f"Fetching emails with query: {query}")
        emails = self.email_auth.fetch_emails(query=query, max_emails=max_emails)
        logger.info(f"Found {len(emails)} emails matching query")
        
        receipts = []
        
        for i, email_data in enumerate(emails):
            logger.info(f"Processing email {i+1}/{len(emails)}: {email_data.get('subject', 'No Subject')}")
            
            try:
                receipt_data = self.receipt_parser.parse(email_data)
                
                # Only include receipts with sufficient confidence
                if receipt_data["confidence"] >= 0.3:
                    receipts.append(receipt_data)
                    
                    # Save receipt data if configured
                    if self.config["output"]["save_receipts"]:
                        self._save_receipt_data(receipt_data, i)
                else:
                    logger.info(f"Skipping email with low confidence: {receipt_data['confidence']}")
            except Exception as e:
                logger.error(f"Error processing email: {str(e)}")
        
        logger.info(f"Successfully processed {len(receipts)} receipts")
        return receipts
    
    def _save_receipt_data(self, receipt_data: Dict, index: int) -> None:
        """Save receipt data to file"""
        receipts_dir = self.config["output"]["receipts_dir"]
        
        # Create directory if it doesn't exist
        if not os.path.exists(receipts_dir):
            os.makedirs(receipts_dir)
        
        # Generate filename
        vendor = receipt_data.get("vendor", "unknown")
        date = receipt_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        filename = f"{receipts_dir}/receipt_{date}_{vendor}_{index}.json"
        
        # Save to file
        try:
            with open(filename, 'w') as f:
                json.dump(receipt_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving receipt data: {str(e)}")
    
    def add_receipts_to_spreadsheet(self, receipts: List[Dict]) -> bool:
        """Add receipt data to Google Sheets"""
        if not self.sheets_integration or not self.sheets_integration.is_authenticated():
            logger.error("Google Sheets integration not set up")
            return False
        
        if not receipts:
            logger.info("No receipts to add to spreadsheet")
            return True
        
        spreadsheet_id = self.config["sheets"]["spreadsheet_id"]
        
        logger.info(f"Adding {len(receipts)} receipts to spreadsheet")
        result = self.sheets_integration.add_multiple_receipts(spreadsheet_id, receipts)
        
        if result:
            logger.info("Successfully added receipts to spreadsheet")
            return True
        else:
            logger.error("Failed to add receipts to spreadsheet")
            return False
    
    def run(self) -> bool:
        """Run the complete email receipt scraping process"""
        logger.info("Starting email receipt scraper")
        
        # Set up email authentication
        logger.info("Setting up email authentication")
        if not self.setup_email_auth():
            logger.error("Failed to set up email authentication")
            return False
        
        # Set up Google Sheets integration
        logger.info("Setting up Google Sheets integration")
        if not self.setup_sheets_integration():
            logger.error("Failed to set up Google Sheets integration")
            return False
        
        # Fetch and process emails
        logger.info("Fetching and processing emails")
        receipts = self.fetch_and_process_emails()
        
        # Add receipts to spreadsheet
        if receipts:
            logger.info("Adding receipts to spreadsheet")
            if not self.add_receipts_to_spreadsheet(receipts):
                logger.error("Failed to add receipts to spreadsheet")
                return False
        else:
            logger.info("No receipts found")
        
        logger.info("Email receipt scraping completed successfully")
        return True


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Email Receipt Scraper')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--save-config', help='Save configuration to file')
    parser.add_argument('--auth-type', choices=['gmail_api', 'imap'],
                        help='Authentication type (gmail_api or imap)')
    parser.add_argument('--email', help='Email address (for IMAP)')
    parser.add_argument('--password', help='Email password (for IMAP)')
    parser.add_argument('--imap-server', help='IMAP server (for IMAP)')
    parser.add_argument('--credentials', help='Path to credentials.json file')
    parser.add_argument('--query', help='Search query for emails')
    parser.add_argument('--max', type=int, help='Maximum number of emails to fetch')
    parser.add_argument('--spreadsheet-id', help='ID of an existing spreadsheet')
    parser.add_argument('--spreadsheet-title', help='Title for a new spreadsheet')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create scraper instance
    scraper = EmailReceiptScraper(args.config)
    
    # Update config from command line arguments
    if args.auth_type:
        scraper.config["email"]["auth_type"] = args.auth_type
    if args.email:
        scraper.config["email"]["email_address"] = args.email
    if args.password:
        scraper.config["email"]["password"] = args.password
    if args.imap_server:
        scraper.config["email"]["imap_server"] = args.imap_server
    if args.credentials:
        scraper.config["email"]["credentials_file"] = args.credentials
        scraper.config["sheets"]["credentials_file"] = args.credentials
    if args.query:
        scraper.config["email"]["search_query"] = args.query
    if args.max:
        scraper.config["email"]["max_emails"] = args.max
    if args.spreadsheet_id:
        scraper.config["sheets"]["spreadsheet_id"] = args.spreadsheet_id
    if args.spreadsheet_title:
        scraper.config["sheets"]["spreadsheet_title"] = args.spreadsheet_title
    
    # Save config if requested
    if args.save_config:
        if scraper.save_config(args.save_config):
            logger.info(f"Configuration saved to {args.save_config}")
        else:
            logger.error(f"Failed to save configuration to {args.save_config}")
    
    # Run the scraper
    success = scraper.run()
    
    if success:
        spreadsheet_id = scraper.config["sheets"]["spreadsheet_id"]
        if spreadsheet_id and scraper.sheets_integration:
            url = scraper.sheets_integration.get_spreadsheet_url(spreadsheet_id)
            print(f"\nReceipt data has been successfully added to the spreadsheet:")
            print(url)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
