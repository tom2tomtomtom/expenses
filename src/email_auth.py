#!/usr/bin/env python3
"""
Email Authentication Module for Receipt Scraper

This module provides authentication functionality for accessing email accounts
using either Gmail API or IMAP protocols.
"""

import os
import pickle
import base64
import imaplib
import email
from email.header import decode_header
import getpass
from typing import Dict, List, Tuple, Optional, Any, Union

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False

class EmailAuthenticator:
    """Base class for email authentication"""
    
    def __init__(self):
        self.authenticated = False
    
    def is_authenticated(self) -> bool:
        """Check if the authenticator is authenticated"""
        return self.authenticated
    
    def authenticate(self) -> bool:
        """Authenticate with the email service"""
        raise NotImplementedError("Subclasses must implement authenticate()")
    
    def disconnect(self) -> None:
        """Disconnect from the email service"""
        raise NotImplementedError("Subclasses must implement disconnect()")
    
    def fetch_emails(self, query: str = "ALL", max_emails: int = 100) -> List[Dict]:
        """Fetch emails based on query"""
        raise NotImplementedError("Subclasses must implement fetch_emails()")


class GmailAPIAuthenticator(EmailAuthenticator):
    """Gmail API authenticator for accessing Gmail accounts"""
    
    def __init__(self, credentials_file: str = 'credentials.json', 
                 token_file: str = 'token.json',
                 scopes: List[str] = None):
        """
        Initialize Gmail API authenticator
        
        Args:
            credentials_file: Path to the credentials.json file
            token_file: Path to save/load the token
            scopes: OAuth scopes to request
        """
        super().__init__()
        self.credentials_file = credentials_file
        self.token_file = token_file
        
        # Default scopes if none provided
        if scopes is None:
            self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        else:
            self.scopes = scopes
            
        self.creds = None
        self.service = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not GMAIL_API_AVAILABLE:
            print("Gmail API libraries not available. Install with:")
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
            
            # Build the Gmail API service
            self.service = build('gmail', 'v1', credentials=self.creds)
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Gmail API service"""
        self.service = None
        self.authenticated = False
    
    def fetch_emails(self, query: str = "ALL", max_emails: int = 100) -> List[Dict]:
        """
        Fetch emails from Gmail using the Gmail API
        
        Args:
            query: Gmail search query (e.g., "subject:receipt")
            max_emails: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with metadata and content
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # Get list of messages matching query
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_emails).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("No messages found.")
                return []
            
            email_list = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full').execute()
                
                # Extract headers
                headers = {}
                for header in msg['payload']['headers']:
                    headers[header['name'].lower()] = header['value']
                
                # Extract body
                body = self._get_body_from_message(msg)
                
                # Extract attachments
                attachments = self._get_attachments_from_message(msg)
                
                email_data = {
                    'id': msg['id'],
                    'thread_id': msg['threadId'],
                    'subject': headers.get('subject', ''),
                    'from': headers.get('from', ''),
                    'to': headers.get('to', ''),
                    'date': headers.get('date', ''),
                    'body': body,
                    'attachments': attachments
                }
                
                email_list.append(email_data)
            
            return email_list
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def _get_body_from_message(self, message: Dict) -> str:
        """Extract body text from a Gmail API message"""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    return base64.urlsafe_b64decode(
                        part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    return base64.urlsafe_b64decode(
                        part['body']['data']).decode('utf-8')
                elif 'parts' in part:
                    for subpart in part['parts']:
                        if subpart['mimeType'] == 'text/plain' and 'data' in subpart['body']:
                            return base64.urlsafe_b64decode(
                                subpart['body']['data']).decode('utf-8')
        
        # If we couldn't find the body in parts, try the payload directly
        if 'body' in message['payload'] and 'data' in message['payload']['body']:
            return base64.urlsafe_b64decode(
                message['payload']['body']['data']).decode('utf-8')
        
        return ""
    
    def _get_attachments_from_message(self, message: Dict) -> List[Dict]:
        """Extract attachments from a Gmail API message"""
        attachments = []
        
        def extract_attachments_from_parts(parts):
            for part in parts:
                if 'filename' in part and part['filename']:
                    attachment = {
                        'id': part['body'].get('attachmentId', ''),
                        'filename': part['filename'],
                        'mimeType': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    }
                    attachments.append(attachment)
                
                if 'parts' in part:
                    extract_attachments_from_parts(part['parts'])
        
        if 'parts' in message['payload']:
            extract_attachments_from_parts(message['payload']['parts'])
        
        return attachments
    
    def download_attachment(self, message_id: str, attachment_id: str, 
                           destination: str) -> bool:
        """
        Download an attachment from a Gmail message
        
        Args:
            message_id: Gmail message ID
            attachment_id: Attachment ID
            destination: Path to save the attachment
            
        Returns:
            bool: True if download successful, False otherwise
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            
            with open(destination, 'wb') as f:
                f.write(file_data)
            
            return True
            
        except Exception as e:
            print(f"Error downloading attachment: {str(e)}")
            return False


class IMAPAuthenticator(EmailAuthenticator):
    """IMAP authenticator for accessing email accounts via IMAP protocol"""
    
    def __init__(self, email_address: str = None, password: str = None, 
                 imap_server: str = None, imap_port: int = 993):
        """
        Initialize IMAP authenticator
        
        Args:
            email_address: Email address
            password: Email password
            imap_server: IMAP server address
            imap_port: IMAP server port
        """
        super().__init__()
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.connection = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with IMAP server
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # If email address not provided, prompt user
            if not self.email_address:
                self.email_address = input("Enter email address: ")
            
            # If password not provided, prompt user securely
            if not self.password:
                self.password = getpass.getpass(f"Enter password for {self.email_address}: ")
            
            # If server not provided, try to guess from email domain
            if not self.imap_server:
                domain = self.email_address.split('@')[-1]
                if domain == 'gmail.com':
                    self.imap_server = 'imap.gmail.com'
                elif domain == 'outlook.com' or domain == 'hotmail.com':
                    self.imap_server = 'outlook.office365.com'
                elif domain == 'yahoo.com':
                    self.imap_server = 'imap.mail.yahoo.com'
                else:
                    self.imap_server = input(f"Enter IMAP server for {domain}: ")
            
            # Connect to the IMAP server
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            
            # Login to the server
            self.connection.login(self.email_address, self.password)
            
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"IMAP authentication failed: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from IMAP server"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
        self.authenticated = False
    
    def fetch_emails(self, query: str = "ALL", max_emails: int = 100) -> List[Dict]:
        """
        Fetch emails from IMAP server
        
        Args:
            query: IMAP search criteria (e.g., 'SUBJECT "receipt"')
            max_emails: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with metadata and content
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # Select the mailbox (inbox by default)
            self.connection.select('INBOX')
            
            # Search for messages matching criteria
            status, data = self.connection.search(None, query)
            
            if status != 'OK':
                print(f"Search failed: {status}")
                return []
            
            # Get message IDs
            message_ids = data[0].split()
            
            # Limit to max_emails
            if len(message_ids) > max_emails:
                message_ids = message_ids[:max_emails]
            
            email_list = []
            
            for msg_id in message_ids:
                # Fetch the message
                status, data = self.connection.fetch(msg_id, '(RFC822)')
                
                if status != 'OK':
                    continue
                
                # Parse the email
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Extract headers
                subject = self._decode_header(msg['Subject'])
                from_addr = self._decode_header(msg['From'])
                to_addr = self._decode_header(msg['To'])
                date = msg['Date']
                
                # Extract body
                body = self._get_body_from_message(msg)
                
                # Extract attachments
                attachments = self._get_attachments_from_message(msg)
                
                email_data = {
                    'id': msg_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'to': to_addr,
                    'date': date,
                    'body': body,
                    'attachments': attachments,
                    'raw_message': msg
                }
                
                email_list.append(email_data)
            
            return email_list
            
        except Exception as e:
            print(f"Error fetching emails: {str(e)}")
            return []
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if header is None:
            return ""
            
        decoded_header = decode_header(header)
        header_parts = []
        
        for content, encoding in decoded_header:
            if isinstance(content, bytes):
                if encoding:
                    header_parts.append(content.decode(encoding))
                else:
                    try:
                        header_parts.append(content.decode('utf-8'))
                    except UnicodeDecodeError:
                        header_parts.append(content.decode('latin-1'))
            else:
                header_parts.append(content)
        
        return " ".join(header_parts)
    
    def _get_body_from_message(self, msg) -> str:
        """Extract body text from an email message"""
        if msg.is_multipart():
            # If the message has multiple parts, find the text/plain part
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get the body text
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                        return body
                    except:
                        pass
            
            # If no text/plain part found, try to get the first part
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get the body text
                if content_type == "text/html":
                    try:
                        body = part.get_payload(decode=True).decode()
                        return body
                    except:
                        pass
        else:
            # If the message is not multipart, just get the payload
            try:
                body = msg.get_payload(decode=True).decode()
                return body
            except:
                pass
        
        return ""
    
    def _get_attachments_from_message(self, msg) -> List[Dict]:
        """Extract attachments from an email message"""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                
                # Check if it's an attachment
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    
                    if filename:
                        attachment = {
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True)),
                            'part': part
                        }
                        attachments.append(attachment)
        
        return attachments
    
    def download_attachment(self, attachment: Dict, destination: str) -> bool:
        """
        Download an attachment from an email
        
        Args:
            attachment: Attachment dictionary from _get_attachments_from_message
            destination: Path to save the attachment
            
        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            if 'part' in attachment:
                payload = attachment['part'].get_payload(decode=True)
                
                with open(destination, 'wb') as f:
                    f.write(payload)
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error downloading attachment: {str(e)}")
            return False


def create_authenticator(auth_type: str = 'gmail_api', **kwargs) -> EmailAuthenticator:
    """
    Factory function to create an appropriate authenticator
    
    Args:
        auth_type: Type of authenticator ('gmail_api' or 'imap')
        **kwargs: Additional arguments to pass to the authenticator
        
    Returns:
        EmailAuthenticator: An authenticator instance
    """
    if auth_type.lower() == 'gmail_api':
        return GmailAPIAuthenticator(**kwargs)
    elif auth_type.lower() == 'imap':
        return IMAPAuthenticator(**kwargs)
    else:
        raise ValueError(f"Unknown authenticator type: {auth_type}")


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Email Authentication Test')
    parser.add_argument('--type', choices=['gmail_api', 'imap'], default='gmail_api',
                        help='Authentication type (gmail_api or imap)')
    parser.add_argument('--email', help='Email address (for IMAP)')
    parser.add_argument('--password', help='Email password (for IMAP)')
    parser.add_argument('--server', help='IMAP server (for IMAP)')
    parser.add_argument('--credentials', default='credentials.json',
                        help='Path to credentials.json file (for Gmail API)')
    parser.add_argument('--query', default='SUBJECT "receipt"',
                        help='Search query for emails')
    parser.add_argument('--max', type=int, default=10,
                        help='Maximum number of emails to fetch')
    
    args = parser.parse_args()
    
    if args.type == 'gmail_api':
        auth = create_authenticator('gmail_api', credentials_file=args.credentials)
    else:
        auth = create_authenticator('imap', email_address=args.email,
                                   password=args.password, imap_server=args.server)
    
    if auth.authenticate():
        print("Authentication successful!")
        
        emails = auth.fetch_emails(query=args.query, max_emails=args.max)
        
        print(f"Found {len(emails)} emails matching query: {args.query}")
        
        for i, email_data in enumerate(emails):
            print(f"\nEmail {i+1}:")
            print(f"Subject: {email_data['subject']}")
            print(f"From: {email_data['from']}")
            print(f"Date: {email_data['date']}")
            print(f"Attachments: {len(email_data['attachments'])}")
        
        auth.disconnect()
    else:
        print("Authentication failed.")
