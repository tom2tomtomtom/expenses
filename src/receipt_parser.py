#!/usr/bin/env python3
"""
Receipt Parser Module for Email Receipt Scraper

This module provides functionality for parsing receipt data from email content,
extracting relevant information such as vendor, date, total amount, and items.
"""

import re
import json
import datetime
from typing import Dict, List, Optional, Any, Union
from bs4 import BeautifulSoup
import dateutil.parser

class ReceiptParser:
    """Base class for receipt parsing"""
    
    def __init__(self):
        """Initialize the receipt parser"""
        self.patterns = {
            'total': [
                r'(?:total|amount|sum)(?:\s+\w+){0,3}?\s*[:]\s*[$€£]?([0-9,]+\.[0-9]{2})',
                r'(?:total|amount|sum)(?:\s+\w+){0,3}?\s*[$€£]([0-9,]+\.[0-9]{2})',
                r'(?:total|amount|sum)(?:\s+\w+){0,3}?\s*\$\s*([0-9,]+\.[0-9]{2})',
                r'(?:total|amount|sum)(?:\s+\w+){0,3}?\s*\$([0-9,]+\.[0-9]{2})',
                r'(?:total|amount|sum)(?:\s+\w+){0,3}?\s*([0-9,]+\.[0-9]{2})',
            ],
            'date': [
                r'(?:date|purchased|order date|invoice date)(?:\s+\w+){0,3}?\s*[:]\s*([A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})',
                r'(?:date|purchased|order date|invoice date)(?:\s+\w+){0,3}?\s*[:]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(?:date|purchased|order date|invoice date)(?:\s+\w+){0,3}?\s*[:]\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
                r'(?:date|purchased|order date|invoice date)(?:\s+\w+){0,3}?\s*[:]\s*([A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})',
                r'(?:date|purchased|order date|invoice date)(?:\s+\w+){0,3}?\s*[:]\s*(\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4})',
                r'(?:date|purchased|order date|invoice date)(?:\s+\w+){0,3}?\s*[:]\s*(\d{4}\s+[A-Za-z]{3,9}\.?\s+\d{1,2})',
            ],
            'vendor': [
                r'(?:from|vendor|merchant|store|retailer)(?:\s+\w+){0,3}?\s*[:]\s*([A-Za-z0-9\s&\',\.]+)',
                r'(?:thank you for shopping at|thank you for your order from|thank you for your purchase from)(?:\s+\w+){0,3}?\s*([A-Za-z0-9\s&\',\.]+)',
                r'(?:receipt from|order from|purchase from)(?:\s+\w+){0,3}?\s*([A-Za-z0-9\s&\',\.]+)',
            ],
            'order_number': [
                r'(?:order|confirmation|reference|invoice|receipt)(?:\s+\w+){0,3}?\s*(?:number|#|no|id)(?:\s+\w+){0,3}?\s*[:]\s*([A-Za-z0-9\-]+)',
                r'(?:order|confirmation|reference|invoice|receipt)(?:\s+\w+){0,3}?\s*(?:number|#|no|id)(?:\s+\w+){0,3}?\s*([A-Za-z0-9\-]+)',
                r'(?:order|confirmation|reference|invoice|receipt)(?:\s+\w+){0,3}?\s*(?:#|no|id)(?:\s+\w+){0,3}?\s*[:]\s*([A-Za-z0-9\-]+)',
            ],
            'subtotal': [
                r'(?:subtotal|sub-total|sub total)(?:\s+\w+){0,3}?\s*[:]\s*[$€£]?([0-9,]+\.[0-9]{2})',
                r'(?:subtotal|sub-total|sub total)(?:\s+\w+){0,3}?\s*[$€£]([0-9,]+\.[0-9]{2})',
                r'(?:subtotal|sub-total|sub total)(?:\s+\w+){0,3}?\s*\$\s*([0-9,]+\.[0-9]{2})',
                r'(?:subtotal|sub-total|sub total)(?:\s+\w+){0,3}?\s*\$([0-9,]+\.[0-9]{2})',
                r'(?:subtotal|sub-total|sub total)(?:\s+\w+){0,3}?\s*([0-9,]+\.[0-9]{2})',
            ],
            'tax': [
                r'(?:tax|vat|gst|hst|pst)(?:\s+\w+){0,3}?\s*[:]\s*[$€£]?([0-9,]+\.[0-9]{2})',
                r'(?:tax|vat|gst|hst|pst)(?:\s+\w+){0,3}?\s*[$€£]([0-9,]+\.[0-9]{2})',
                r'(?:tax|vat|gst|hst|pst)(?:\s+\w+){0,3}?\s*\$\s*([0-9,]+\.[0-9]{2})',
                r'(?:tax|vat|gst|hst|pst)(?:\s+\w+){0,3}?\s*\$([0-9,]+\.[0-9]{2})',
                r'(?:tax|vat|gst|hst|pst)(?:\s+\w+){0,3}?\s*([0-9,]+\.[0-9]{2})',
            ],
            'shipping': [
                r'(?:shipping|delivery|freight)(?:\s+\w+){0,3}?\s*[:]\s*[$€£]?([0-9,]+\.[0-9]{2})',
                r'(?:shipping|delivery|freight)(?:\s+\w+){0,3}?\s*[$€£]([0-9,]+\.[0-9]{2})',
                r'(?:shipping|delivery|freight)(?:\s+\w+){0,3}?\s*\$\s*([0-9,]+\.[0-9]{2})',
                r'(?:shipping|delivery|freight)(?:\s+\w+){0,3}?\s*\$([0-9,]+\.[0-9]{2})',
                r'(?:shipping|delivery|freight)(?:\s+\w+){0,3}?\s*([0-9,]+\.[0-9]{2})',
            ],
            'discount': [
                r'(?:discount|savings|coupon|promo)(?:\s+\w+){0,3}?\s*[:]\s*[$€£]?([0-9,]+\.[0-9]{2})',
                r'(?:discount|savings|coupon|promo)(?:\s+\w+){0,3}?\s*[$€£]([0-9,]+\.[0-9]{2})',
                r'(?:discount|savings|coupon|promo)(?:\s+\w+){0,3}?\s*\$\s*([0-9,]+\.[0-9]{2})',
                r'(?:discount|savings|coupon|promo)(?:\s+\w+){0,3}?\s*\$([0-9,]+\.[0-9]{2})',
                r'(?:discount|savings|coupon|promo)(?:\s+\w+){0,3}?\s*([0-9,]+\.[0-9]{2})',
            ],
        }
        
        # Vendor-specific patterns for known receipt formats
        self.vendor_patterns = {
            'amazon': {
                'vendor': 'Amazon',
                'total': r'(?:Grand Total|Order Total):\s*\$([0-9,]+\.[0-9]{2})',
                'date': r'(?:Order Placed|Date):\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
                'order_number': r'(?:Order|Confirmation)?\s*#\s*([A-Z0-9\-]+)',
                'items': r'(?:Item\(s\) Subtotal|Subtotal):\s*\$([0-9,]+\.[0-9]{2})',
            },
            'walmart': {
                'vendor': 'Walmart',
                'total': r'(?:Total|Order Total):\s*\$([0-9,]+\.[0-9]{2})',
                'date': r'(?:Date|Order Date):\s*(\d{1,2}/\d{1,2}/\d{2,4})',
                'order_number': r'(?:Order|Receipt) #:\s*(\d+)',
            },
            'target': {
                'vendor': 'Target',
                'total': r'(?:Total):\s*\$([0-9,]+\.[0-9]{2})',
                'date': r'(?:Date):\s*(\d{1,2}/\d{1,2}/\d{2,4})',
                'order_number': r'(?:Receipt) #:\s*(\d+)',
            },
            'starbucks': {
                'vendor': 'Starbucks',
                'total': r'(?:Total):\s*\$([0-9,]+\.[0-9]{2})',
                'date': r'(?:Date):\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
                'order_number': r'(?:Order) #:\s*(\d+)',
            },
            'uber_eats': {
                'vendor': 'Uber Eats',
                'total': r'(?:Total):\s*\$([0-9,]+\.[0-9]{2})',
                'date': r'(?:Date):\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
                'order_number': r'(?:Order) #:\s*([A-Z0-9\-]+)',
            },
            'doordash': {
                'vendor': 'DoorDash',
                'total': r'(?:Total):\s*\$([0-9,]+\.[0-9]{2})',
                'date': r'(?:Date):\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',
                'order_number': r'(?:Order) #:\s*([A-Z0-9\-]+)',
            },
        }
    
    def parse(self, email_data: Dict) -> Dict:
        """
        Parse receipt data from an email
        
        Args:
            email_data: Email data dictionary with subject, body, etc.
            
        Returns:
            Dictionary with extracted receipt data
        """
        # Extract text from HTML if needed
        body = email_data.get('body', '')
        if '<html' in body.lower() or '<body' in body.lower():
            body = self._extract_text_from_html(body)
        
        # Initialize receipt data
        receipt_data = {
            'vendor': None,
            'date': None,
            'total': None,
            'subtotal': None,
            'tax': None,
            'shipping': None,
            'discount': None,
            'order_number': None,
            'items': [],
            'currency': 'USD',  # Default currency
            'email_subject': email_data.get('subject', ''),
            'email_from': email_data.get('from', ''),
            'email_date': email_data.get('date', ''),
            'confidence': 0.0,
        }
        
        # Try to identify vendor from email address or subject
        vendor = self._identify_vendor(email_data)
        if vendor:
            receipt_data['vendor'] = vendor
            # Use vendor-specific patterns if available
            if vendor.lower() in self.vendor_patterns:
                receipt_data = self._parse_vendor_specific(body, vendor.lower(), receipt_data)
        
        # Extract data using generic patterns
        receipt_data = self._extract_data_with_patterns(body, receipt_data)
        
        # Try to extract items if possible
        receipt_data['items'] = self._extract_items(body)
        
        # Calculate confidence score
        receipt_data['confidence'] = self._calculate_confidence(receipt_data)
        
        return receipt_data
    
    def _identify_vendor(self, email_data: Dict) -> Optional[str]:
        """Identify vendor from email data"""
        # Try to extract from email address
        from_addr = email_data.get('from', '')
        subject = email_data.get('subject', '')
        
        # Common receipt email patterns
        receipt_keywords = ['receipt', 'order', 'purchase', 'confirmation', 'invoice']
        
        # Check if it's a receipt email
        is_receipt = False
        for keyword in receipt_keywords:
            if keyword.lower() in subject.lower():
                is_receipt = True
                break
        
        if not is_receipt:
            return None
        
        # Extract domain from email
        domain_match = re.search(r'@([^>]+)', from_addr)
        if domain_match:
            domain = domain_match.group(1).lower()
            
            # Map common domains to vendor names
            domain_to_vendor = {
                'amazon.com': 'Amazon',
                'walmart.com': 'Walmart',
                'target.com': 'Target',
                'starbucks.com': 'Starbucks',
                'uber.com': 'Uber Eats',
                'doordash.com': 'DoorDash',
                'bestbuy.com': 'Best Buy',
                'homedepot.com': 'Home Depot',
                'lowes.com': 'Lowes',
                'costco.com': 'Costco',
                'samsclub.com': 'Sam\'s Club',
                'apple.com': 'Apple',
                'microsoft.com': 'Microsoft',
                'ebay.com': 'eBay',
                'etsy.com': 'Etsy',
            }
            
            for d, v in domain_to_vendor.items():
                if d in domain:
                    return v
        
        # Try to extract from subject
        for vendor_name in ['Amazon', 'Walmart', 'Target', 'Starbucks', 'Uber Eats', 
                           'DoorDash', 'Best Buy', 'Home Depot', 'Lowes', 'Costco', 
                           'Sam\'s Club', 'Apple', 'Microsoft', 'eBay', 'Etsy']:
            if vendor_name.lower() in subject.lower():
                return vendor_name
        
        return None
    
    def _parse_vendor_specific(self, body: str, vendor: str, receipt_data: Dict) -> Dict:
        """Parse receipt using vendor-specific patterns"""
        patterns = self.vendor_patterns.get(vendor, {})
        
        for field, pattern in patterns.items():
            if field == 'vendor':
                receipt_data[field] = patterns[field]
                continue
                
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                # Convert to appropriate type
                if field in ['total', 'subtotal', 'tax', 'shipping', 'discount']:
                    try:
                        value = float(value.replace(',', ''))
                    except ValueError:
                        continue
                
                receipt_data[field] = value
        
        return receipt_data
    
    def _extract_data_with_patterns(self, body: str, receipt_data: Dict) -> Dict:
        """Extract data using generic patterns"""
        for field, patterns in self.patterns.items():
            # Skip if already extracted by vendor-specific patterns
            if receipt_data.get(field) is not None:
                continue
                
            for pattern in patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    
                    # Convert to appropriate type
                    if field in ['total', 'subtotal', 'tax', 'shipping', 'discount']:
                        try:
                            value = float(value.replace(',', ''))
                        except ValueError:
                            continue
                    
                    receipt_data[field] = value
                    break
        
        # Try to parse date if found
        if receipt_data.get('date') and isinstance(receipt_data['date'], str):
            try:
                parsed_date = dateutil.parser.parse(receipt_data['date'])
                receipt_data['date'] = parsed_date.strftime('%Y-%m-%d')
            except:
                pass
        
        return receipt_data
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract text from HTML content"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text(separator=' ', strip=True)
            
            # Break into lines and remove leading and trailing space
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"Error extracting text from HTML: {str(e)}")
            return html
    
    def _extract_items(self, body: str) -> List[Dict]:
        """
        Extract item details from receipt
        
        This is a complex task and may not work for all receipt formats.
        A more robust solution would use machine learning or specialized
        receipt parsing libraries.
        """
        items = []
        
        # Look for common item patterns
        # Format: Item name, quantity, price
        item_patterns = [
            r'(\d+)\s+x\s+([\w\s\-&\']+)\s+\$?(\d+\.\d{2})',
            r'([\w\s\-&\']+)\s+\$?(\d+\.\d{2})\s+(?:ea|each)',
            r'([\w\s\-&\']+)\s+\$?(\d+\.\d{2})',
        ]
        
        for pattern in item_patterns:
            matches = re.findall(pattern, body)
            for match in matches:
                if len(match) == 3:  # Item with quantity
                    try:
                        quantity = int(match[0])
                        name = match[1].strip()
                        price = float(match[2])
                        items.append({
                            'name': name,
                            'quantity': quantity,
                            'price': price,
                            'total': quantity * price
                        })
                    except:
                        pass
                elif len(match) == 2:  # Item without explicit quantity
                    try:
                        name = match[0].strip()
                        price = float(match[1])
                        items.append({
                            'name': name,
                            'quantity': 1,
                            'price': price,
                            'total': price
                        })
                    except:
                        pass
        
        return items
    
    def _calculate_confidence(self, receipt_data: Dict) -> float:
        """Calculate confidence score for the parsed receipt"""
        # Count how many fields were successfully extracted
        required_fields = ['vendor', 'date', 'total']
        optional_fields = ['subtotal', 'tax', 'shipping', 'discount', 'order_number']
        
        required_count = sum(1 for field in required_fields if receipt_data.get(field) is not None)
        optional_count = sum(1 for field in optional_fields if receipt_data.get(field) is not None)
        
        # Calculate confidence score
        required_weight = 0.7
        optional_weight = 0.3
        
        required_score = required_count / len(required_fields) * required_weight
        optional_score = optional_count / len(optional_fields) * optional_weight
        
        return required_score + optional_score


class ReceiptParserFactory:
    """Factory for creating receipt parsers"""
    
    @staticmethod
    def create_parser() -> ReceiptParser:
        """Create a receipt parser instance"""
        return ReceiptParser()


if __name__ == "__main__":
    # Example usage
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Receipt Parser Test')
    parser.add_argument('--input', required=True, help='Input file with email data in JSON format')
    parser.add_argument('--output', help='Output file for parsed receipt data')
    
    args = parser.parse_args()
    
    try:
        with open(args.input, 'r') as f:
            email_data = json.load(f)
        
        parser = ReceiptParserFactory.create_parser()
        receipt_data = parser.parse(email_data)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(receipt_data, f, indent=2, default=str)
        else:
            print(json.dumps(receipt_data, indent=2, default=str))
            
    except Exception as e:
        print(f"Error: {str(e)}")
