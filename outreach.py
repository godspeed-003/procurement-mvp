import json
import logging
import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time
import re

# Import for Mailjet
try:
    from mailjet_rest import Client as MailjetClient
    MAILJET_AVAILABLE = True
except ImportError:
    MAILJET_AVAILABLE = False
    print("Mailjet not available. Email functionality will be disabled.")
    print("Install with: pip install mailjet-rest")

# For Twilio SMS
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio not available. SMS functionality will be disabled.")
    print("Install with: pip install twilio")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("supplier-outreach")

class OutreachManager:
    """Manager for supplier outreach via email and SMS"""
    
    def __init__(self, 
                 json_filepath: str,
                 mailjet_config: Dict[str, str],
                 twilio_config: Optional[Dict[str, str]] = None,
                 procurement_details: Dict[str, str] = None):
        """
        Initialize the outreach manager
        
        Args:
            json_filepath: Path to the JSON file containing supplier information
            mailjet_config: Mailjet configuration dictionary with keys:
                - api_key, api_secret, from_email, from_name
            twilio_config: Twilio configuration dictionary with keys:
                - account_sid, auth_token, from_number
            procurement_details: Details about the procurement requirements
        """
        self.json_filepath = json_filepath
        self.mailjet_config = mailjet_config
        self.twilio_config = twilio_config
        self.procurement_details = procurement_details or {}
        self.suppliers = []
        self.results = {
            "email_sent": 0,
            "email_failed": 0,
            "sms_sent": 0,
            "sms_failed": 0,
            "total_suppliers": 0,
            "suppliers_with_email": 0,
            "suppliers_with_phone": 0,
            "start_time": None,
            "end_time": None,
            "details": []
        }
        
        # Initialize Mailjet client if available
        if MAILJET_AVAILABLE and mailjet_config:
            try:
                self.mailjet = MailjetClient(
                    auth=(mailjet_config['api_key'], mailjet_config['api_secret']), 
                    version='v3.1'
                )
            except Exception as e:
                logger.error(f"Failed to initialize Mailjet client: {e}")
                self.mailjet = None
        else:
            self.mailjet = None
            
    def load_suppliers(self) -> bool:
        """Load supplier data from JSON file"""
        try:
            if not os.path.exists(self.json_filepath):
                logger.error(f"Supplier file not found: {self.json_filepath}")
                return False
                
            with open(self.json_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if 'suppliers' in data:
                self.suppliers = data['suppliers']
                self.results["total_suppliers"] = len(self.suppliers)
                
                # Count suppliers with contact info
                self.results["suppliers_with_email"] = sum(1 for s in self.suppliers if s.get("email"))
                self.results["suppliers_with_phone"] = sum(1 for s in self.suppliers if s.get("mobile_number"))
                
                logger.info(f"Loaded {len(self.suppliers)} suppliers from {self.json_filepath}")
                return True
            else:
                logger.error("Invalid supplier JSON format - 'suppliers' key not found")
                return False
                
        except Exception as e:
            logger.error(f"Error loading suppliers: {e}")
            return False
            
    def _create_email_message(self, supplier: Dict[str, Any]) -> Dict[str, Any]:
        """Create email message for a supplier in Mailjet format"""
        if not supplier.get('email'):
            raise ValueError("Supplier has no email address")
            
        # Create customized email using Mailjet format
        company_name = supplier.get('company_name', 'Supplier')
        recipient_email = supplier.get('email')
        
        # Create HTML body with procurement details
        html_body = f"""
        <html>
        <body>
        <p>Dear {company_name},</p>
        
        <p>We are interested in procuring the following:</p>
        
        <ul>
            <li><strong>Product:</strong> {self.procurement_details.get('product_types', 'N/A')}</li>
            <li><strong>Quantity:</strong> {self.procurement_details.get('quantity', 'N/A')}</li>
            <li><strong>Required by:</strong> {self.procurement_details.get('delivery_timeline', 'N/A')}</li>
            <li><strong>Delivery Location:</strong> {self.procurement_details.get('delivery_location', 'N/A')}</li>
        </ul>
        
        <p>Can you provide a quotation for the above requirements? We need this urgently.</p>
        
        <p>Please reply with:</p>
        <ol>
            <li>Price per unit</li>
            <li>Total cost including taxes</li>
            <li>Delivery timeframe</li>
            <li>Payment terms</li>
        </ol>
        
        <p>Thank you and we look forward to your prompt response.</p>
        
        <p>Best regards,<br/>
        Procurement Team<br/>
        ThinkLoop AI</p>
        </body>
        </html>
        """
        
        # Create text-only version
        text_body = f"""
        Dear {company_name},
        
        We are interested in procuring the following:
        
        - Product: {self.procurement_details.get('product_types', 'N/A')}
        - Quantity: {self.procurement_details.get('quantity', 'N/A')}
        - Required by: {self.procurement_details.get('delivery_timeline', 'N/A')}
        - Delivery Location: {self.procurement_details.get('delivery_location', 'N/A')}
        
        Can you provide a quotation for the above requirements? We need this urgently.
        
        Please reply with:
        1. Price per unit
        2. Total cost including taxes
        3. Delivery timeframe
        4. Payment terms
        
        Thank you and we look forward to your prompt response.
        
        Best regards,
        Procurement Team
        ThinkLoop AI
        """
        
        # Create subject with procurement info
        product_type = self.procurement_details.get('product_types', 'your products')
        subject = f"Urgent Procurement Request: {product_type}"
        
        # Format message in Mailjet format
        message = {
            "From": {
                "Email": self.mailjet_config.get('from_email'),
                "Name": self.mailjet_config.get('from_name', 'Procurement Team')
            },
            "To": [
                {
                    "Email": recipient_email,
                    "Name": company_name
                }
            ],
            "Subject": subject,
            "TextPart": text_body,
            "HTMLPart": html_body
        }
        
        return message
        
    def _create_sms_message(self, supplier: Dict[str, Any]) -> str:
        """Create SMS message for a supplier"""
        company_name = supplier.get('company_name', 'Supplier').split(" ")[0]  # Use first word of company name to keep SMS short
        product_type = self.procurement_details.get('product_types', 'products')
        quantity = self.procurement_details.get('quantity', '')
        
        # Create a concise SMS under 160 characters
        sms_body = (
            f"Hi {company_name}, we need to procure {quantity} of {product_type}. "
            f"Please reply with quotation ASAP. Email sent with details. ThinkLoop AI Procurement"
        )
        
        # Ensure message is not too long for a single SMS
        if len(sms_body) > 160:
            sms_body = sms_body[:157] + "..."
            
        return sms_body
    
    async def send_email(self, supplier: Dict[str, Any]) -> bool:
        """Send email to a supplier using Mailjet"""
        if not supplier.get('email'):
            logger.warning(f"No email for supplier: {supplier.get('company_name', 'Unknown')}")
            return False
            
        try:
            # In demonstration mode, don't actually send emails
            if self.mailjet_config.get('demo_mode', True):
                recipient = supplier.get('email')
                company_name = supplier.get('company_name')
                logger.info(f"[DEMO MODE] Would send email to {recipient} at {company_name}")
                print(f"📧 Would send email to {recipient} ({company_name})")
                return True
                
            # Create and send real email using Mailjet
            if not self.mailjet:
                logger.error("Mailjet client not initialized")
                return False
            
            message = self._create_email_message(supplier)
            data = {
                'Messages': [message]
            }
            
            # Make API call to Mailjet
            result = self.mailjet.send.create(data=data)
            
            if result.status_code == 200:
                recipient = supplier.get('email')
                logger.info(f"Email sent successfully to {recipient}")
                print(f"📧 Email sent to {recipient} ({supplier.get('company_name')})")
                return True
            else:
                logger.error(f"Mailjet API error: {result.status_code} - {result.json()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {supplier.get('email')}: {e}")
            return False
    
    async def send_sms(self, supplier: Dict[str, Any]) -> bool:
        """Send SMS to a supplier"""
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio not available. Cannot send SMS.")
            return False
            
        if not supplier.get('mobile_number'):
            logger.warning(f"No phone number for supplier: {supplier.get('company_name', 'Unknown')}")
            return False
            
        if not self.twilio_config:
            logger.warning("Twilio configuration not provided. Cannot send SMS.")
            return False
            
        try:
            phone_number = supplier['mobile_number']
            # Ensure the phone number is properly formatted
            if not phone_number.startswith('+'):
                # Check if it's an Indian number (starts with 9,8,7,6)
                if re.match(r'^[6-9]\d{9}$', phone_number):
                    phone_number = f"+91{phone_number}"
                # Check if it begins with a country code but missing + sign
                elif re.match(r'^[1-9]\d{1,3}[6-9]\d{9}$', phone_number):
                    phone_number = f"+{phone_number}"
                    
            # In demonstration mode, don't actually send SMS
            if self.twilio_config.get('demo_mode', True):
                company_name = supplier.get('company_name')
                logger.info(f"[DEMO MODE] Would send SMS to {phone_number} at {company_name}")
                print(f"📱 Would send SMS to {phone_number} ({company_name})")
                return True
                
            # Send real SMS if not in demo mode
            client = TwilioClient(
                self.twilio_config['account_sid'], 
                self.twilio_config['auth_token']
            )
            
            # Debug mode - log detailed info about the phone number
            if self.twilio_config.get('debug_mode'):
                logger.info(f"SMS Debug - Phone: {phone_number}, Format valid: {bool(re.match(r'^\+[1-9]\d{6,14}$', phone_number))}")
                print(f"🔍 SMS Debug - Sending to: {phone_number}")
                
            message = client.messages.create(
                body=self._create_sms_message(supplier),
                from_=self.twilio_config['from_number'],
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully to {phone_number} (SID: {message.sid})")
            print(f"📱 SMS sent to {phone_number} ({supplier.get('company_name')})")
            return True
            
        except Exception as e:
            # Enhanced error handling for Twilio
            error_msg = str(e)
            if "not a valid phone number" in error_msg.lower():
                logger.error(f"Invalid phone number for {supplier.get('company_name')}: {supplier.get('mobile_number')}")
                print(f"⚠️ Invalid phone number for {supplier.get('company_name')}")
            elif "authenticate" in error_msg.lower():
                logger.error(f"Twilio authentication failed: {error_msg}")
                print(f"⚠️ Twilio authentication failed - check your credentials")
            elif "permission" in error_msg.lower() or "not enabled" in error_msg.lower():
                logger.error(f"Twilio permission error: {error_msg}")
                print(f"⚠️ Twilio error: You may not have permissions to send SMS to this number")
            else:
                logger.error(f"Failed to send SMS to {supplier.get('mobile_number')}: {e}")
                print(f"⚠️ SMS failed: {error_msg[:100]}...")
                
            return False
    
    async def contact_supplier(self, supplier: Dict[str, Any]) -> Dict[str, Any]:
        """Contact a supplier via email and SMS"""
        result = {
            "supplier": supplier.get("company_name", "Unknown"),
            "email_sent": False,
            "sms_sent": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send email first (primary method)
        if supplier.get('email'):
            result["email_sent"] = await self.send_email(supplier)
            if result["email_sent"]:
                self.results["email_sent"] += 1
            else:
                self.results["email_failed"] += 1
        
        # Add a small delay between email and SMS
        await asyncio.sleep(1)
        
        # Send SMS as additional channel if email failed or to reinforce urgency
        if self.twilio_config and supplier.get('mobile_number'):
            result["sms_sent"] = await self.send_sms(supplier)
            if result["sms_sent"]:
                self.results["sms_sent"] += 1
            else:
                self.results["sms_failed"] += 1
                
        self.results["details"].append(result)
        return result
        
    async def run_outreach_campaign(self) -> Dict[str, Any]:
        """Run the complete outreach campaign to all suppliers"""
        if not self.suppliers:
            success = self.load_suppliers()
            if not success:
                logger.error("Failed to load suppliers. Cannot continue.")
                return self.results
                
        self.results["start_time"] = datetime.now().isoformat()
        logger.info(f"Starting outreach campaign to {len(self.suppliers)} suppliers")
        print(f"\n📊 Starting outreach to {len(self.suppliers)} suppliers")
        print(f"📋 Product: {self.procurement_details.get('product_types', 'N/A')}")
        print(f"📦 Quantity: {self.procurement_details.get('quantity', 'N/A')}")
        print(f"🗓️ Timeline: {self.procurement_details.get('delivery_timeline', 'N/A')}")
        print("="*50)
        
        # Process suppliers in parallel with rate limiting (max 5 concurrent tasks)
        sem = asyncio.Semaphore(5)
        
        async def contact_with_rate_limit(supplier):
            async with sem:
                result = await self.contact_supplier(supplier)
                # Add a small delay to prevent overwhelming the API
                await asyncio.sleep(2)
                return result
                
        # Create tasks for all suppliers
        tasks = [contact_with_rate_limit(supplier) for supplier in self.suppliers]
        await asyncio.gather(*tasks)
        
        # Record completion time
        self.results["end_time"] = datetime.now().isoformat()
        
        # Save results to file
        self.save_outreach_results()
        
        # Summary
        print("\n" + "="*50)
        print("📊 OUTREACH CAMPAIGN COMPLETED")
        print("="*50)
        print(f"✅ Emails: {self.results['email_sent']}/{self.results['suppliers_with_email']} successful")
        print(f"✅ SMS: {self.results['sms_sent']}/{self.results['suppliers_with_phone']} successful")
        print(f"⏱️ Time: {datetime.fromisoformat(self.results['end_time']) - datetime.fromisoformat(self.results['start_time'])}")
        print("="*50)
        
        logger.info(f"Outreach campaign completed. "
                  f"Emails: {self.results['email_sent']}/{self.results['suppliers_with_email']} successful, "
                  f"SMS: {self.results['sms_sent']}/{self.results['suppliers_with_phone']} successful.")
        
        return self.results
        
    def save_outreach_results(self) -> str:
        """Save outreach results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(self.json_filepath), "outreach_data")
        os.makedirs(output_dir, exist_ok=True)
        results_file = os.path.join(output_dir, f"outreach_results_{timestamp}.json")
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
            
        logger.info(f"Outreach results saved to {results_file}")
        return results_file

async def run_supplier_outreach(
    json_filepath: str,
    procurement_details: Dict[str, Any],
    mailjet_config: Dict[str, str],
    twilio_config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Run supplier outreach campaign
    
    Args:
        json_filepath: Path to supplier JSON file
        procurement_details: Procurement requirement details
        mailjet_config: Mailjet configuration
        twilio_config: Optional Twilio configuration
        
    Returns:
        Results dictionary
    """
    # Set demo mode by default for safety
    mailjet_config['demo_mode'] = mailjet_config.get('demo_mode', True)
    if twilio_config:
        twilio_config['demo_mode'] = twilio_config.get('demo_mode', True)
    
    # Check if demo mode is active
    if mailjet_config.get('demo_mode'):
        print("\n🔔 RUNNING IN DEMONSTRATION MODE")
        print("📧 Emails and SMS will be logged but not actually sent")
        print("✏️ Set demo_mode=False in config to send real communications\n")
    
    # Check if Mailjet is available
    if not MAILJET_AVAILABLE:
        print("\n❌ Mailjet client library not installed!")
        print("📦 Please install it using: pip install mailjet-rest\n")
        return {"error": "Mailjet client library not installed"}
    
    # Validate required Mailjet config
    required_mailjet_keys = ['api_key', 'api_secret', 'from_email']
    missing_keys = [key for key in required_mailjet_keys if key not in mailjet_config]
    if missing_keys:
        logger.error(f"Missing required Mailjet configuration keys: {', '.join(missing_keys)}")
        return {"error": f"Missing Mailjet config: {', '.join(missing_keys)}"}
    
    # Initialize and run outreach
    outreach = OutreachManager(
        json_filepath=json_filepath,
        mailjet_config=mailjet_config,
        twilio_config=twilio_config,
        procurement_details=procurement_details
    )
    
    print(f"\n🔍 Analyzing supplier data from: {os.path.basename(json_filepath)}")
    
    return await outreach.run_outreach_campaign()

if __name__ == "__main__":
    # Direct script execution - read JSON and show results in terminal
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Supplier Outreach Tool')
    parser.add_argument('json_file', help='Path to the supplier JSON file')
    parser.add_argument('--demo', action='store_true', help='Run in demonstration mode (no actual emails/SMS)')
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.json_file):
        print(f"Error: File not found: {args.json_file}")
        exit(1)
    
    # Load procurement details from json metadata
    procurement_details = {}
    try:
        with open(args.json_file, 'r') as f:
            data = json.load(f)
            # Try to extract requirements if they exist
            if 'procurement_requirements' in data:
                procurement_details = data['procurement_requirements']
    except Exception as e:
        print(f"Error reading procurement details: {e}")
    
    # Default demo Mailjet config
    mailjet_config = {
        'api_key': os.environ.get('MJ_APIKEY_PUBLIC', ''),
        'api_secret': os.environ.get('MJ_APIKEY_PRIVATE', ''),
        'from_email': os.environ.get('MJ_FROM_EMAIL', ''),
        'from_name': os.environ.get('MJ_FROM_NAME', 'Procurement Team'),
        'demo_mode': args.demo
    }
    
    # Twilio config if available
    twilio_config = None
    if all([
        os.environ.get('TWILIO_ACCOUNT_SID'),
        os.environ.get('TWILIO_AUTH_TOKEN'),
        os.environ.get('TWILIO_PHONE_NUMBER')
    ]):
        twilio_config = {
            'account_sid': os.environ.get('TWILIO_ACCOUNT_SID'),
            'auth_token': os.environ.get('TWILIO_AUTH_TOKEN'),
            'from_number': os.environ.get('TWILIO_PHONE_NUMBER'),
            'demo_mode': args.demo
        }
    
    print("\n🚀 SUPPLIER OUTREACH TOOL")
    print("="*50)
    
    if not procurement_details:
        print("⚠️ No procurement details found in the JSON file.")
        print("Enter procurement details manually:")
        procurement_details = {
            'product_types': input("Product types: "),
            'quantity': input("Quantity: "),
            'delivery_timeline': input("Delivery timeline: "),
            'delivery_location': input("Delivery location: ")
        }
    
    # Run the outreach
    asyncio.run(run_supplier_outreach(
        args.json_file,
        procurement_details,
        mailjet_config,
        twilio_config
    ))
