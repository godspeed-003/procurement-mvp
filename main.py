import logging
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("smartprocure-main")

class SmartProcureOrchestrator:
    """Main orchestrator for the SmartProcure Agent pipeline"""
    
    def __init__(self):
        self.session_data = {}
        self.current_phase = None
        
    async def run_procurement_pipeline(self, mode: str = "text"):
        """Run the complete procurement pipeline"""
        logger.info("🚀 Starting SmartProcure Agent Pipeline")
        logger.info("="*60)
        
        try:
            # Phase 1: Requirements Intake
            logger.info("📋 Phase 1: Requirements Intake")
            requirements = await self.phase_1_requirements_intake(mode)
            
            if not requirements:
                logger.error("❌ Requirements intake failed")
                return
            
            # Phase 2: Supplier Discovery
            logger.info("🔍 Phase 2: Supplier Discovery")
            suppliers_file = await self.phase_2_supplier_discovery(requirements)
            
            if not suppliers_file:
                logger.error("❌ Supplier discovery failed")
                return
            
            # Phase 3: Supplier Outreach - NEW
            logger.info("🎯 Phase 3: Supplier Outreach")
            outreach_result = await self.phase_3_supplier_outreach(suppliers_file, requirements)
            
            if not outreach_result:
                logger.warning("⚠️ Supplier outreach had issues")
                # Continue anyway, as partial outreach may have succeeded
            
            # Future phases
            logger.info("🤝 Phase 4: Negotiation & Confirmation (Coming soon...)")
            logger.info("📊 Phase 5: Reporting & Handoff (Coming soon...)")
            
            logger.info("✅ SmartProcure Pipeline completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return

    async def phase_1_requirements_intake(self, mode: str) -> Optional[Dict[str, Any]]:
        """Phase 1: Voice/Text intake of procurement requirements"""
        try:
            if mode.lower() == "voice":
                logger.info("🎤 Starting voice intake mode...")
                return await self.run_voice_intake()
            else:
                logger.info("💬 Starting text intake mode...")
                return await self.run_text_intake()
                
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            return None

    async def run_voice_intake(self) -> Optional[Dict[str, Any]]:
        """Run voice intake using LiveKit"""
        try:
            from voice_intake import cli, WorkerOptions, entrypoint, prewarm
            
            logger.info("Starting LiveKit voice agent...")
            logger.info("Connect to the LiveKit room to begin voice interaction")
            
            # This would start the LiveKit agent
            cli.run_app(
                WorkerOptions(
                    entrypoint_fnc=entrypoint,
                    prewarm_fnc=prewarm,
                ),
            )
            
            # In a real implementation, we'd need to capture the results
            # For now, return None as this requires LiveKit connection
            return None
            
        except Exception as e:
            logger.error(f"Voice intake failed: {e}")
            return None

    async def run_text_intake(self) -> Optional[Dict[str, Any]]:
        """Run text-based intake using console input"""
        try:
            from voice_intake import ProcurementRequirements
            
            print("\n" + "="*60)
            print("🤖 SMARTPROCURE AGENT - REQUIREMENTS INTAKE")
            print("="*60)
            print("I'll help you gather your procurement requirements.")
            print("Please answer the following questions:\n")
            
            requirements = ProcurementRequirements()
            requirements.session_id = f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Question 1: Product types
            print("1. What product types are you looking to procure?")
            print("   Please be as specific as possible (e.g., 'Hydrochloric acid 10%' instead of just 'chemicals')")
            requirements.product_types = input("   → ").strip()
            
            # Question 2: Quantity
            print("\n2. What quantity do you need?")
            print("   Please include units (kg, pieces, tons, liters, etc.)")
            requirements.quantity = input("   → ").strip()
            
            # Question 3: Delivery timeline
            print("\n3. What is your delivery timeline?")
            print("   You can use relative dates like 'next week', 'in 2 weeks', or specific dates")
            requirements.delivery_timeline = input("   → ").strip()
            
            # Question 4: Procurement source location
            print("\n4. Which city or state would you prefer to procure these products from?")
            print("   This helps us find suppliers in your preferred region")
            requirements.procurement_source_location = input("   → ").strip()
            
            # Question 5: Delivery location
            print("\n5. Which city or state do you want the products delivered to?")
            requirements.delivery_location = input("   → ").strip()
            
            # Question 6: Quality/Certification requirements
            print("\n6. Do you have any specific quality or certification requirements?")
            print("   (e.g., ISO certified, FDA approved, or type 'none' if not applicable)")
            cert_input = input("   → ").strip()
            requirements.quality_certification_filters = "None" if cert_input.lower() in ['none', 'skip', 'no'] else cert_input
            
            # Show summary and confirm
            requirements.is_complete = True
            requirements.last_updated = datetime.now().isoformat()
            
            print(self._display_requirements_summary(requirements))
            
            # Confirmation
            while True:
                confirm = input("\nIs this information correct? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y', 'correct', 'confirm']:
                    logger.info("✅ Requirements confirmed by user")
                    return requirements.to_dict()
                elif confirm in ['no', 'n']:
                    print("Please restart the requirements gathering process.")
                    return None
                else:
                    print("Please answer 'yes' or 'no'")
            
        except KeyboardInterrupt:
            print("\n\n❌ Process interrupted by user")
            return None
        except Exception as e:
            logger.error(f"Text intake failed: {e}")
            return None

    def _display_requirements_summary(self, requirements: 'ProcurementRequirements') -> str:
        """Display formatted requirements summary"""
        summary = "\n" + "="*60
        summary += "\n📋 PROCUREMENT REQUIREMENTS SUMMARY"
        summary += "\n" + "="*60
        summary += f"\n🔹 Product Specification: {requirements.product_types}"
        summary += f"\n🔹 Required Quantity: {requirements.quantity}"
        summary += f"\n🔹 Delivery Timeframe: {requirements.delivery_timeline}"
        summary += f"\n🔹 Preferred Sourcing Location: {requirements.procurement_source_location}"
        summary += f"\n🔹 Delivery Destination: {requirements.delivery_location}"
        summary += f"\n🔹 Quality/Certification Requirements: {requirements.quality_certification_filters}"
        summary += f"\n\nSession ID: {requirements.session_id}"
        summary += "\n" + "="*60
        return summary

    async def phase_2_supplier_discovery(self, requirements: Dict[str, Any]) -> Optional[str]:
        """Phase 2: Discover suppliers using web scraping"""
        try:
            from scraper import discover_suppliers
            
            logger.info("🔍 Starting supplier discovery...")
            print("\n🕸️  Searching IndiaMART for suppliers...")
            print("🤖 Using AI to find and rank the best matches...")
            
            # Run supplier discovery
            json_filepath = await discover_suppliers(requirements)
            
            if json_filepath:
                logger.info(f"✅ Supplier discovery completed: {json_filepath}")
                return json_filepath
            else:
                logger.warning("❌ No suppliers found")
                return None
                
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            return None

    async def phase_3_supplier_outreach(self, suppliers_file: str, requirements: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 3: Contact suppliers via email and SMS"""
        try:
            from outreach import run_supplier_outreach
            
            logger.info("🚀 Starting supplier outreach...")
            print("\n📧 Contacting suppliers via email and SMS...")
            
            # Get Mailjet configuration - use the direct API keys now
            mailjet_config = {
                'api_key': os.environ.get('MJ_API', ''),  # Use the new MJ_API env variable
                'api_secret': os.environ.get('MJ_secret', ''),  # Use the new MJ_secret env variable
                'from_email': os.environ.get('MJ_FROM_EMAIL', ''),
                'from_name': os.environ.get('MJ_FROM_NAME', 'Procurement Team'),
                'demo_mode': False  # Set to False to actually send emails
            }
            
            # Check if Mailjet credentials are available
            if not all([mailjet_config['api_key'], mailjet_config['api_secret'], mailjet_config['from_email']]):
                logger.warning("❌ Mailjet credentials not set in environment variables")
                print("\n⚠️ Email outreach disabled - Mailjet credentials not configured")
                print("To enable email outreach, set the following environment variables:")
                print("  - MJ_API (your Mailjet API key)")
                print("  - MJ_secret (your Mailjet API secret)")
                print("  - MJ_FROM_EMAIL (your sender email address)")
                print("  - MJ_FROM_NAME (optional: your sender name)")
                print("\nSkipping outreach phase...")
                return None
            
            # Optional: Get Twilio configuration if available, with better error handling
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
                    'demo_mode': False,  # Set to False to actually send SMS
                    'debug_mode': True   # Enable debug mode for better error logging
                }
                logger.info("📱 SMS outreach enabled with Twilio")
            else:
                logger.info("📱 SMS outreach disabled - Twilio credentials not configured")
            
            # Run outreach
            result = await run_supplier_outreach(
                suppliers_file,
                requirements,
                mailjet_config,
                twilio_config
            )
            
            if "error" in result:
                logger.error(f"❌ Supplier outreach failed: {result['error']}")
                return None
                
            # Show outreach summary
            print("\n" + "="*60)
            print("📊 OUTREACH SUMMARY:")
            print("="*60)
            print(f"✅ Emails sent: {result['email_sent']}/{result['suppliers_with_email']}")
            if twilio_config:
                print(f"✅ SMS sent: {result['sms_sent']}/{result['suppliers_with_phone']}")
            print(f"📊 Total suppliers contacted: {result['total_suppliers']}")
            print("="*60)
            
            logger.info(f"✅ Supplier outreach completed")
            return result
                
        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            return None

def print_banner():
    """Print application banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     🤖 SMARTPROCURE AGENT - AI PROCUREMENT ASSISTANT    ║
    ║                                                          ║
    ║     Created by: Nesar, CEO - ThinkLoop AI               ║
    ║     Version: MVP v1                                      ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_help():
    """Print help information"""
    help_text = """
    USAGE:
        python main.py [mode]
    
    MODES:
        text    - Run in text/console mode (default)
        voice   - Run in voice mode using LiveKit
        help    - Show this help message
    
    EXAMPLES:
        python main.py              # Run in text mode
        python main.py text          # Run in text mode
        python main.py voice         # Run in voice mode
        python main.py help          # Show help
    
    DESCRIPTION:
        SmartProcure Agent automates the procurement workflow by:
        1. 📋 Gathering requirements through voice or text input
        2. 🔍 Discovering suppliers from IndiaMART using AI
        3. 📞 (Coming soon) Contacting suppliers automatically
        4. 🤝 (Coming soon) Negotiating and confirming orders
        5. 📊 (Coming soon) Generating reports and handoffs
    """
    print(help_text)

async def main():
    """Main entry point"""
    print_banner()
    
    # Parse command line arguments
    mode = "text"  # default mode
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "help":
            print_help()
            return
        elif arg in ["voice", "text"]:
            mode = arg
        else:
            print(f"❌ Invalid mode: {arg}")
            print("Use 'python main.py help' for usage information")
            return
    
    # Initialize and run orchestrator
    orchestrator = SmartProcureOrchestrator()
    await orchestrator.run_procurement_pipeline(mode)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! SmartProcure Agent terminated by user.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
        sys.exit(1)
