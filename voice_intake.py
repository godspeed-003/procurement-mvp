import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    metrics,
    RoomInputOptions,
)
from livekit.plugins import (
    neuphonic,  # Changed from cartesia to neuphonic
    google,  # Changed from openai to google
    deepgram,
    silero,
)

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")
logger = logging.getLogger("voice-agent")


class ProcurementRequirements:
    def __init__(self):
        self.product_types: Optional[str] = None
        self.quantity: Optional[str] = None
        self.delivery_timeline: Optional[str] = None
        self.procurement_source_location: Optional[str] = None  # Where to procure from
        self.delivery_location: Optional[str] = None  # Where to deliver to
        self.quality_certification_filters: Optional[str] = None
        self.current_step: int = 0
        self.session_id: Optional[str] = None
        self.is_complete: bool = False
        self.last_updated: str = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_types": self.product_types,
            "quantity": self.quantity,
            "delivery_timeline": self.delivery_timeline,
            "procurement_source_location": self.procurement_source_location,
            "delivery_location": self.delivery_location,
            "quality_certification_filters": self.quality_certification_filters,
            "current_step": self.current_step,
            "session_id": self.session_id,
            "is_complete": self.is_complete,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcurementRequirements':
        req = cls()
        for key, value in data.items():
            if hasattr(req, key):
                setattr(req, key, value)
        return req


class Assistant(Agent):
    def __init__(self, text_mode=False) -> None:
        self.requirements = ProcurementRequirements()
        self.questions = [
            "What product types are you looking to procure? Please be as specific as possible.",
            "What quantity do you need? Please include the units too (kg, pieces, tons, etc.).",
            "What is your delivery timeline? You could mention relative dates too like 'next month' or 'in 2 weeks'.",
            "Which city or state would you prefer to procure these products from?",
            "Which city or state do you want the products delivered to?",
            "Do you have any specific quality or certification requirements? If not, just say 'none' or 'skip'.",
        ]
        self.text_mode = text_mode

        if text_mode:
            # Text mode configuration - no TTS/STT needed
            super().__init__(
                instructions=(
                    "You are an intelligent procurement assistant helping businesses gather requirements for supplier database search. "
                    "Your goal is to collect enough detailed information to effectively search and match suppliers. "
                    "Follow these 6 main categories in order: Product types, Quantity with units, Delivery timeline, Procurement source location, Delivery location, Quality/certification requirements. "
                    "You may ask follow-up questions within each category if the information provided is too vague or insufficient for effective supplier matching. "
                    "For example: if someone says 'chemicals' ask for specifics like 'hydrochloric acid' or concentration. "
                    "Only move to the next category when you have sufficient information for that requirement. "
                    "After all information is gathered, provide a comprehensive summary with clear descriptions of what was collected. "
                    "Be conversational and helpful while staying focused on gathering procurement requirements."
                ),
                llm=google.LLM(
                    model="gemini-2.0-flash",
                    temperature=0.3,  # Moderate temperature for intelligent follow-ups
                )
            )
        else:
            # Voice mode configuration - full stack
            super().__init__(
                instructions=(
                    "You are an intelligent procurement assistant helping businesses gather requirements for supplier database search. "
                    "Your goal is to collect enough detailed information to effectively search and match suppliers. "
                    "Follow these 6 main categories in order: Product types, Quantity with units, Delivery timeline, Procurement source location, Delivery location, Quality/certification requirements. "
                    "You may ask follow-up questions within each category if the information provided is too vague or insufficient for effective supplier matching. "
                    "For example: if someone says 'chemicals' ask for specifics like 'hydrochloric acid' or concentration. "
                    "Only move to the next category when you have sufficient information for that requirement. "
                    "After all information is gathered, provide a comprehensive summary with clear descriptions of what was collected. "
                    "Be conversational and helpful while staying focused on gathering procurement requirements."
                ),
                stt=deepgram.STT(model="nova-3", language="multi"),
                llm=google.LLM(
                    model="gemini-2.0-flash",
                    temperature=0.3,
                ),
                tts=neuphonic.TTS(
                    voice_id="fc854436-2dac-4d21-aa69-ae17b54e98eb",
                    speed=1.0,
                    model="neu_hq",
                    lang_code="en"
                ),
                vad=silero.VAD.load(),
            )

    def _get_dynamic_instructions(self) -> str:
        base_instructions = (
            "You are a procurement assistant helping businesses gather their requirements. "
            "You should use short and concise responses, avoiding unpronounceable punctuation. "
            "Always be professional and focused on gathering accurate procurement information. "
        )

        if self.requirements.current_step < len(self.questions):
            current_question = self.questions[self.requirements.current_step]
            return f"{base_instructions} Currently asking: {current_question}"
        else:
            return f"{base_instructions} All requirements collected, ready for confirmation."

    def _save_session_data(self):
        """Save current session data to file"""
        try:
            # Create sessions directory if it doesn't exist
            sessions_dir = "d:/AI/agent/procurement/sessions"
            os.makedirs(sessions_dir, exist_ok=True)
            
            filename = f"session_{self.requirements.session_id}.json"
            filepath = os.path.join(sessions_dir, filename)
            with open(filepath, "w") as f:
                json.dump(self.requirements.to_dict(), f)
            logger.info(f"Session data saved for {self.requirements.session_id}")
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")

    def _load_session_data(self, session_id: str) -> bool:
        """Load existing session data"""
        try:
            filename = f"session_{session_id}.json"
            filepath = os.path.join("d:/AI/agent/procurement/sessions", filename)
            with open(filepath, "r") as f:
                data = json.load(f)
                self.requirements = ProcurementRequirements.from_dict(data)
            logger.info(f"Session data loaded for {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to load session data: {e}")
            return False

    def _get_summary(self) -> str:
        """Generate comprehensive summary of current requirements"""
        summary = "Here's a comprehensive summary of your procurement requirements:\n\n"
        
        if self.requirements.product_types:
            summary += f"🔹 Product Specification: {self.requirements.product_types}\n"
        if self.requirements.quantity:
            summary += f"🔹 Required Quantity: {self.requirements.quantity}\n"
        if self.requirements.delivery_timeline:
            summary += f"🔹 Delivery Timeframe: {self.requirements.delivery_timeline}\n"
        if self.requirements.procurement_source_location:
            summary += f"🔹 Preferred Sourcing Location: {self.requirements.procurement_source_location}\n"
        if self.requirements.delivery_location:
            summary += f"🔹 Delivery Destination: {self.requirements.delivery_location}\n"
        if self.requirements.quality_certification_filters:
            summary += f"🔹 Quality/Certification Requirements: {self.requirements.quality_certification_filters}\n"
        
        summary += "\nThis information will be used to search our supplier database and find the best matches for your requirements.\n"
        return summary

    async def on_enter(self):
        # Generate a session ID
        self.requirements.session_id = f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        greeting = (
            "Hello! I'm your procurement assistant. I'll help you gather your requirements "
            "for supplier sourcing. Let me ask you a few questions. "
            f"{self.questions[0]}"
        )

        await self._send_message(greeting)

    async def on_user_speech_committed(self, user_message):
        """Handle user responses and progress through questions"""
        user_response = user_message.content.strip()

        # Check for modification requests
        if "change" in user_response.lower() or "modify" in user_response.lower():
            await self._handle_modification_request(user_response)
            return

        # Check for confirmation requests
        if self.requirements.current_step >= len(self.questions):
            await self._handle_confirmation(user_response)
            return

        # Store the current response
        await self._store_current_response(user_response)

        # Move to next question or complete
        self.requirements.current_step += 1
        self.requirements.last_updated = datetime.now().isoformat()
        self._save_session_data()

        if self.requirements.current_step < len(self.questions):
            # Ask next question
            next_question = self.questions[self.requirements.current_step]
            response_msg = f"Thank you. Next question: {next_question}"
            await self.session.say(response_msg)
        else:
            # All questions asked, provide summary and ask for confirmation
            summary = self._get_summary()
            confirmation_message = (
                f"{summary}\n"
                "Is this information correct? Say 'yes' to confirm, or tell me what you'd like to change."
            )
            await self.session.say(confirmation_message)

    async def on_user_turn_completed(self, session: AgentSession, *args, **kwargs):
        """Handle text mode interactions"""
        if not self.text_mode:
            return  # Voice mode is handled by on_user_speech_committed
            
        # Get the last user message for text mode
        last_input = ""
        if hasattr(session, "last_user_message") and session.last_user_message is not None:
            last_input = session.last_user_message.text_content or ""
        
        logger.debug(f"Processing input: {last_input}")
        logger.debug(f"Current step: {self.requirements.current_step}")
        
        # Process the input with structured approach
        await self._process_user_input_structured(last_input)

    async def _process_user_input_structured(self, user_response: str):
        """Process input with intelligent follow-up questions for better supplier matching"""
        user_response = user_response.strip()

        # Check for modification requests
        if "change" in user_response.lower() or "modify" in user_response.lower():
            await self._handle_modification_request(user_response)
            return

        # Check for confirmation requests
        if self.requirements.current_step >= len(self.questions):
            await self._handle_confirmation(user_response)
            return

        # Store the current response directly
        await self._store_current_response(user_response)

        # Move to next question or complete
        self.requirements.current_step += 1
        self.requirements.last_updated = datetime.now().isoformat()
        self._save_session_data()

        if self.requirements.current_step < len(self.questions):
            # Let the LLM intelligently ask the next question with context
            next_question = self.questions[self.requirements.current_step]
            
            # Provide context to the LLM for intelligent questioning
            context_prompt = (
                f"The user just provided: '{user_response}' for the previous requirement. "
                f"Now move to the next requirement category if you are satisfied with the response. Ask this question: '{next_question}'. "
                f"You may add helpful context or examples to make it easier for the user to provide specific information that will help with supplier matching. "
                f"Keep it conversational and helpful."
            )
            
            # Let the LLM handle the response intelligently
            await self.session.say(context_prompt, allow_interruptions=True)
        else:
            # All questions asked, provide comprehensive summary and ask for confirmation
            summary = self._get_summary()
            
            # Print gathered data for debugging
            print("\n" + "="*60)
            print("GATHERED PROCUREMENT DATA:")
            print("="*60)
            requirements_dict = self.requirements.to_dict()
            for key, value in requirements_dict.items():
                if value and key not in ['current_step', 'session_id', 'is_complete', 'last_updated']:
                    print(f"{key.replace('_', ' ').title()}: {value}")
            print("="*60 + "\n")
            
            confirmation_prompt = (
                f"Great! I've collected all the necessary information. {summary}\n"
                "Please review this summary carefully. Is all this information correct and sufficient for finding suppliers? "
                "Say 'yes' to confirm and proceed with supplier search, or tell me what you'd like to modify."
            )
            
            if self.text_mode:
                print(f"\n🤖 Assistant: {confirmation_prompt}")
            else:
                await self.session.say(confirmation_prompt, allow_interruptions=True)

    async def _send_message(self, message: str):
        """Send message in appropriate mode (text or voice)"""
        if self.text_mode:
            # Don't use session.say in text mode, just print directly
            print(f"\n🤖 Assistant: {message}")
        else:
            await self.session.say(message)

    async def _store_current_response(self, response: str):
        """Store user response in appropriate field"""
        step = self.requirements.current_step

        if step == 0:  # Product types
            self.requirements.product_types = response
        elif step == 1:  # Quantity
            self.requirements.quantity = response
        elif step == 2:  # Delivery timeline
            self.requirements.delivery_timeline = response
        elif step == 3:  # Procurement source location
            self.requirements.procurement_source_location = response
        elif step == 4:  # Delivery location
            self.requirements.delivery_location = response
        elif step == 5:  # Quality/Certification filters
            if response.lower() in ['none', 'skip', 'no']:
                self.requirements.quality_certification_filters = "None"
            else:
                self.requirements.quality_certification_filters = response

    async def _handle_modification_request(self, user_message: str):
        """Handle requests to modify previously entered information"""
        # Simple keyword matching for now - can be enhanced with NLP
        if "product" in user_message.lower():
            self.requirements.current_step = 0
            msg = self.questions[0]
        elif "quantity" in user_message.lower():
            self.requirements.current_step = 1
            msg = self.questions[1]
        elif "delivery" in user_message.lower() or "timeline" in user_message.lower():
            self.requirements.current_step = 2
            msg = self.questions[2]
        elif "source" in user_message.lower() or "procure from" in user_message.lower():
            self.requirements.current_step = 3
            msg = self.questions[3]
        elif "deliver" in user_message.lower() or "delivery location" in user_message.lower():
            self.requirements.current_step = 4
            msg = self.questions[4]
        elif "quality" in user_message.lower() or "certification" in user_message.lower():
            self.requirements.current_step = 5
            msg = self.questions[5]
        else:
            # Ask which field they want to modify
            msg = "Which requirement would you like to change? Please mention: product types, quantity, delivery timeline, procurement source location, delivery location, or quality requirements."
        
        await self._send_message(msg)

    async def _handle_confirmation(self, user_response: str):
        """Handle final confirmation with detailed summary"""
        if "yes" in user_response.lower() or "correct" in user_response.lower() or "confirm" in user_response.lower():
            self.requirements.is_complete = True
            self.requirements.last_updated = datetime.now().isoformat()
            self._save_session_data()

            # Print final comprehensive data
            print("\n" + "="*60)
            print("FINAL PROCUREMENT REQUIREMENTS:")
            print("="*60)
            
            print("Product Details:")
            print(f"  - Type: {self.requirements.product_types}")
            print(f"  - Quantity: {self.requirements.quantity}")
            print(f"  - Quality/Certification: {self.requirements.quality_certification_filters}")
            
            print("\nLogistics Information:")
            print(f"  - Delivery Timeline: {self.requirements.delivery_timeline}")
            print(f"  - Source Location: {self.requirements.procurement_source_location}")
            print(f"  - Delivery Location: {self.requirements.delivery_location}")
            
            print(f"\nSession Details:")
            print(f"  - Session ID: {self.requirements.session_id}")
            print(f"  - Completed: {self.requirements.is_complete}")
            print(f"  - Last Updated: {self.requirements.last_updated}")
            print("="*60)
            
            # Pass data to next component in pipeline
            await self._pass_to_next_component()

            success_message = (
                "Perfect! I've successfully captured all your procurement requirements with sufficient detail for effective supplier matching. "
                "The system will now search our supplier database using these specifications and begin the outreach process to find the best matches. "
                "You'll receive updates as we identify and contact potential suppliers for your requirements."
            )
            
            if self.text_mode:
                print(f"\n🤖 Assistant: {success_message}")
            else:
                await self.session.say(success_message, allow_interruptions=True)
        else:
            # User wants to make changes
            change_message = (
                "No problem! I'm here to help you get the requirements exactly right. "
                "Please tell me specifically what you'd like to change - you can mention: "
                "product specifications, quantity details, delivery timeline, sourcing location, delivery location, or quality requirements."
            )
            
            if self.text_mode:
                print(f"\n🤖 Assistant: {change_message}")
            else:
                await self.session.say(change_message, allow_interruptions=True)

    async def _pass_to_next_component(self):
        """Pass the collected data to the next component in the pipeline"""
        logger.info(f"Procurement requirements complete: {self.requirements.to_dict()}")
        
        # Note: Pipeline logic moved to main.py
        # This method now just logs completion for potential external orchestration
        print("\n✅ Requirements gathering completed!")
        print("🔄 Pipeline orchestration handled by main.py")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice agent for participant {participant.identity}")

    usage_collector = metrics.UsageCollector()

    # Log metrics and collect usage data
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)

    # Determine if we're in text mode based on the room name or environment
    text_mode = ctx.room.name == "console" or ctx.room.name == "fake_room"
    
    if text_mode:
        # Text mode setup - minimal configuration
        session = AgentSession()
    else:
        # Voice mode setup - full configuration
        session = AgentSession(
            vad=silero.VAD.load(),
            min_endpointing_delay=0.5,
            max_endpointing_delay=5.0,
        )

    # Trigger the on_metrics_collected function when metrics are collected
    session.on("metrics_collected", on_metrics_collected)

    await session.start(
        room=ctx.room,
        agent=Assistant(text_mode=text_mode),
        room_input_options=RoomInputOptions(),
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )

