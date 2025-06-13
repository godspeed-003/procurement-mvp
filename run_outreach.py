import os
import sys
import json
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env")

async def main():
    """Run outreach for a specific supplier JSON file"""
    # Display banner
    print("\n" + "="*60)
    print("🚀 SUPPLIER OUTREACH TOOL")
    print("="*60)
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python run_outreach.py <path_to_json_file> [--live]")
        print("\nOptions:")
        print("  --live    Run in live mode (actually sends emails and SMS)")
        print("\nExample:")
        print("  python run_outreach.py D:\\AI\\agent\\procurement\\data\\suppliers_20250613_005039.json")
        print("="*60)
        return
        
    # Get JSON file path
    json_path = sys.argv[1]
    
    # Check if live mode is enabled
    live_mode = "--live" in sys.argv
        
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return
        
    # Load the supplier data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not data.get('suppliers'):
            print("Error: Invalid supplier JSON format - 'suppliers' key not found")
            return
            
        supplier_count = len(data['suppliers'])
        print(f"📋 Found {supplier_count} suppliers in {os.path.basename(json_path)}")
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return
        
    # Collect procurement details
    procurement_details = {}
    print("\n📝 Please provide procurement details:")
    procurement_details['product_types'] = input("Product types: ")
    procurement_details['quantity'] = input("Quantity: ")
    procurement_details['delivery_timeline'] = input("Delivery timeline: ")
    procurement_details['delivery_location'] = input("Delivery location: ")
    
    # Configure Mailjet
    mailjet_config = {
        'api_key': os.environ.get('MJ_API', ''),
        'api_secret': os.environ.get('MJ_secret', ''),
        'from_email': os.environ.get('MJ_FROM_EMAIL', ''),
        'from_name': os.environ.get('MJ_FROM_NAME', 'Procurement Team'),
        'demo_mode': live_mode  # Only send real emails in live mode
    }
    
    # Configure Twilio
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
            'demo_mode': not live_mode,  # Only send real SMS in live mode
            'debug_mode': True  # Enable debug mode
        }
    
    # Run the outreach
    from outreach import run_supplier_outreach
    
    if not live_mode:
        print("\n⚠️ RUNNING IN DEMO MODE - No actual emails or SMS will be sent")
        print("Use --live flag to send real messages")
    else:
        print("\n🔴 RUNNING IN LIVE MODE - Real emails and SMS will be sent!")
        
    print("\n⏳ Running outreach campaign...")
    result = await run_supplier_outreach(
        json_path,
        procurement_details,
        mailjet_config,
        twilio_config
    )
    
    print("\n✅ Outreach completed")

if __name__ == "__main__":
    asyncio.run(main())
