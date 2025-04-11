#!/usr/bin/env python3
"""
Google Sheets Integration Module for Email Receipt Scraper

This module provides functionality for integrating with Google Sheets,
allowing the application to store parsed receipt data in a spreadsheet.
"""

import os
import json
import pickle
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Google Sheets API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    SHEETS_API_AVAILABLE = True
except ImportError:
    SHEETS_API_AVAILABLE = False

class GoogleSheetsIntegration:
    """Google Sheets integration for storing receipt data"""
    
    def __init__(self, credentials_file: str = 'credentials.json', 
                 token_file: str = 'sheets_token.json',
                 scopes: List[str] = None):
        """
        Initialize Google Sheets integration
        
        Args:
            credentials_file: Path to the credentials.json file
            token_file: Path to save/load the token
            scopes: OAuth scopes to request
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        
        # Default scopes if none provided
        if scopes is None:
            self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        else:
            self.scopes = scopes
            
        self.creds = None
        self.service = None
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API using OAuth
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not SHEETS_API_AVAILABLE:
            print("Google Sheets API libraries not available. Install with:")
            print("pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            return False
            
        try:
            # Check if we already have valid credentials
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # If no valid credentials available, let the user log in
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        print(f"Credentials file '{self.credentials_file}' not found.")
                        print("Please download it from Google Cloud Console.")
                        return False
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes)
                    self.creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            # Build the Sheets API service
            self.service = build('sheets', 'v4', credentials=self.creds)
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if the integration is authenticated"""
        return self.authenticated
    
    def create_spreadsheet(self, title: str) -> Optional[str]:
        """
        Create a new Google Sheets spreadsheet
        
        Args:
            title: Title of the spreadsheet
            
        Returns:
            str: Spreadsheet ID if successful, None otherwise
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'Receipts',
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        }
                    }
                ]
            }
            
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            
            # Set up header row
            self.update_values(
                spreadsheet_id,
                'Receipts!A1:K1',
                [['Date', 'Vendor', 'Total', 'Subtotal', 'Tax', 'Shipping', 
                  'Discount', 'Order Number', 'Currency', 'Email Subject', 'Confidence']]
            )
            
            # Format header row
            format_requests = [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': 0,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 0.8,
                                    'green': 0.8,
                                    'blue': 0.8
                                },
                                'horizontalAlignment': 'CENTER',
                                'textFormat': {
                                    'bold': True
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                    }
                },
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': 0,
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }
            ]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': format_requests}
            ).execute()
            
            print(f"Spreadsheet created: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
            return spreadsheet_id
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def get_spreadsheet_url(self, spreadsheet_id: str) -> str:
        """Get the URL for a spreadsheet"""
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    
    def update_values(self, spreadsheet_id: str, range_name: str, 
                     values: List[List[Any]]) -> bool:
        """
        Update values in a spreadsheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to update (e.g., 'Sheet1!A1:B2')
            values: Values to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False
    
    def append_values(self, spreadsheet_id: str, range_name: str, 
                     values: List[List[Any]]) -> bool:
        """
        Append values to a spreadsheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to append to (e.g., 'Sheet1!A:B')
            values: Values to append
            
        Returns:
            bool: True if append successful, False otherwise
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False
    
    def get_values(self, spreadsheet_id: str, range_name: str) -> List[List[Any]]:
        """
        Get values from a spreadsheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to get (e.g., 'Sheet1!A1:B2')
            
        Returns:
            List of rows with values
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get('values', [])
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def add_receipt_to_spreadsheet(self, spreadsheet_id: str, receipt_data: Dict) -> bool:
        """
        Add receipt data to a spreadsheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            receipt_data: Receipt data dictionary
            
        Returns:
            bool: True if add successful, False otherwise
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # Prepare row data
            row = [
                receipt_data.get('date', ''),
                receipt_data.get('vendor', ''),
                receipt_data.get('total', ''),
                receipt_data.get('subtotal', ''),
                receipt_data.get('tax', ''),
                receipt_data.get('shipping', ''),
                receipt_data.get('discount', ''),
                receipt_data.get('order_number', ''),
                receipt_data.get('currency', 'USD'),
                receipt_data.get('email_subject', ''),
                receipt_data.get('confidence', 0.0)
            ]
            
            # Append row to spreadsheet
            return self.append_values(spreadsheet_id, 'Receipts!A:K', [row])
            
        except Exception as e:
            print(f"Error adding receipt to spreadsheet: {str(e)}")
            return False
    
    def add_multiple_receipts(self, spreadsheet_id: str, 
                             receipt_data_list: List[Dict]) -> bool:
        """
        Add multiple receipt data entries to a spreadsheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            receipt_data_list: List of receipt data dictionaries
            
        Returns:
            bool: True if add successful, False otherwise
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # Prepare rows data
            rows = []
            
            for receipt_data in receipt_data_list:
                row = [
                    receipt_data.get('date', ''),
                    receipt_data.get('vendor', ''),
                    receipt_data.get('total', ''),
                    receipt_data.get('subtotal', ''),
                    receipt_data.get('tax', ''),
                    receipt_data.get('shipping', ''),
                    receipt_data.get('discount', ''),
                    receipt_data.get('order_number', ''),
                    receipt_data.get('currency', 'USD'),
                    receipt_data.get('email_subject', ''),
                    receipt_data.get('confidence', 0.0)
                ]
                rows.append(row)
            
            # Append rows to spreadsheet
            return self.append_values(spreadsheet_id, 'Receipts!A:K', rows)
            
        except Exception as e:
            print(f"Error adding receipts to spreadsheet: {str(e)}")
            return False


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Sheets Integration Test')
    parser.add_argument('--credentials', default='credentials.json',
                        help='Path to credentials.json file')
    parser.add_argument('--create', action='store_true',
                        help='Create a new spreadsheet')
    parser.add_argument('--title', default='Receipt Tracker',
                        help='Title for the new spreadsheet')
    parser.add_argument('--spreadsheet-id',
                        help='ID of an existing spreadsheet')
    parser.add_argument('--add-receipt', 
                        help='Path to receipt data JSON file to add')
    
    args = parser.parse_args()
    
    sheets = GoogleSheetsIntegration(credentials_file=args.credentials)
    
    if sheets.authenticate():
        print("Authentication successful!")
        
        if args.create:
            spreadsheet_id = sheets.create_spreadsheet(args.title)
            if spreadsheet_id:
                print(f"Created spreadsheet: {sheets.get_spreadsheet_url(spreadsheet_id)}")
        
        if args.spreadsheet_id and args.add_receipt:
            try:
                with open(args.add_receipt, 'r') as f:
                    receipt_data = json.load(f)
                
                if sheets.add_receipt_to_spreadsheet(args.spreadsheet_id, receipt_data):
                    print("Receipt added successfully!")
                else:
                    print("Failed to add receipt.")
            except Exception as e:
                print(f"Error: {str(e)}")
    else:
        print("Authentication failed.")
