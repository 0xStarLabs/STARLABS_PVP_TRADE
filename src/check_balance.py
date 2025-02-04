import pyrogram
from loguru import logger
import asyncio
import questionary
from questionary import Choice
import re
import sys
import os

# Import configuration
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import CYCLE_MODE


class CheckBalances:
    def __init__(self, sessions: list):
        self.sessions = sessions
        self.bot_username = "pvptrade_bot"

    async def select_sessions(self):
        """Interactive session selection"""
        choices = [
            Choice(
                title="📱 All Sessions",
                value="all"
            )
        ]
        
        # Add individual sessions
        for i, session in enumerate(self.sessions, 1):
            user = session["user"]
            choice_text = (
                f"{i}. Session: {session['session_name']} | "
                f"User: {user['username']} ({user['first_name']} {user['last_name']})"
            )
            choices.append(Choice(title=choice_text, value=session))
        
        # Add cancel option
        choices.append(Choice(title="❌ Cancel", value=None))

        selected = await questionary.select(
            "Select session to check balance:",
            choices=choices,
            qmark="💰",
            instruction="Use ↑↓ arrows to navigate, Enter to select"
        ).ask_async()

        if selected == "all":
            return self.sessions
        elif selected:
            return [selected]
        return []

    def parse_balance_message(self, message_text: str) -> tuple:
        """Extract balance information from message"""
        try:
            # Extract perps balance using regex
            perps_match = re.search(r"Perps Balance: \$(\d+\.\d+) \(Available to trade: \$(\d+\.\d+)\)", message_text)
            perps_balance = float(perps_match.group(1)) if perps_match else 0.0
            perps_available = float(perps_match.group(2)) if perps_match else 0.0

            # Extract spot balance using regex
            spot_match = re.search(r"Spot Balance: \$(\d+\.\d+) \(Available to trade: \$(\d+\.\d+)\)", message_text)
            spot_balance = float(spot_match.group(1)) if spot_match else 0.0
            spot_available = float(spot_match.group(2)) if spot_match else 0.0

            return perps_balance, perps_available, spot_balance, spot_available
        except Exception as e:
            logger.error(f"Error parsing balance message: {str(e)}")
            return 0.0, 0.0, 0.0, 0.0

    async def check_single_balance(self, session: dict) -> bool:
        """Check balance for a single session"""
        try:
            async with pyrogram.Client(
                name=session["session_name"],
                workdir="data/sessions"
            ) as app:
                logger.info(f"Checking balance for session {session['session_name']}")
                
                # Send /wallet command
                await app.send_message(self.bot_username, "/wallet")
                
                # First quick check for clan registration message
                await asyncio.sleep(2)
                async for message in app.get_chat_history(self.bot_username, limit=1):
                    if message.text and "Create your clan" in message.text:
                        logger.warning(f"Session {session['session_name']} requires clan registration to proceed")
                        return False
                
                # Poll for response with timeout
                balance_found = False
                timeout = 30  # 30 seconds timeout
                start_time = asyncio.get_event_loop().time()
                
                while not balance_found and (asyncio.get_event_loop().time() - start_time) < timeout:
                    # Get wallet information
                    async for message in app.get_chat_history(self.bot_username, limit=3):
                        if message.text and "Create your clan" in message.text:
                            logger.warning(f"Session {session['session_name']} requires clan registration to proceed")
                            return False
                            
                        if message.text and "Your Wallet" in message.text:
                            perps_balance, perps_available, spot_balance, spot_available = self.parse_balance_message(message.text)
                            total_balance = perps_balance + spot_balance
                            
                            balance_line = (
                                f"\n{'='*50}\n"
                                f"Session: {session['session_name']}\n"
                                f"User: {session['user']['username']}\n"
                                f"Perps: ${perps_balance:.2f} (Available: ${perps_available:.2f}) | "
                                f"Spot: ${spot_balance:.2f} (Available: ${spot_available:.2f}) | "
                                f"Total: ${total_balance:.2f}\n"
                                f"{'='*50}"
                            )
                            
                            logger.info(balance_line)
                            balance_found = True
                            return True
                    
                    if not balance_found:
                        await asyncio.sleep(1)  # Wait 1 second before next check
                        
                if not balance_found:
                    logger.error(f"Timeout: Could not find balance info for {session['session_name']} after {timeout} seconds")
                    return False

        except Exception as e:
            logger.error(f"Error checking balance for {session['session_name']}: {str(e)}")
            return False

    async def check_balances(self):
        """Check balances for selected sessions"""
        selected_sessions = await self.select_sessions()
        if not selected_sessions:
            logger.info("Balance check cancelled")
            return

        total_checked = 0
        total_perps = 0.0
        total_spot = 0.0
        
        if CYCLE_MODE:
            # Sequential mode
            logger.info("Running in sequential mode")
            for session in selected_sessions:
                if await self.check_single_balance(session):
                    total_checked += 1
                    # Get the last message to extract balances
                    async with pyrogram.Client(name=session["session_name"], workdir="data/sessions") as app:
                        async for message in app.get_chat_history(self.bot_username, limit=3):
                            if message.text and "Your Wallet" in message.text:
                                perps_balance, _, spot_balance, _ = self.parse_balance_message(message.text)
                                total_perps += perps_balance
                                total_spot += spot_balance
                                break
                await asyncio.sleep(1)  # Small delay between sessions
        else:
            # Parallel mode
            logger.info("Running in parallel mode")
            tasks = []
            for session in selected_sessions:
                async def check_and_get_balance(sess):
                    if await self.check_single_balance(sess):
                        async with pyrogram.Client(name=sess["session_name"], workdir="data/sessions") as app:
                            async for message in app.get_chat_history(self.bot_username, limit=3):
                                if message.text and "Your Wallet" in message.text:
                                    return self.parse_balance_message(message.text)
                    return None

                tasks.append(check_and_get_balance(session))
            
            results = await asyncio.gather(*tasks)
            for result in results:
                if result:
                    perps_balance, _, spot_balance, _ = result
                    total_perps += perps_balance
                    total_spot += spot_balance
                    total_checked += 1

        if total_checked > 0:
            total_balance = total_perps + total_spot
            summary = (
                f"\n{'='*50}\n"
                f"TOTAL BALANCE SUMMARY\n"
                f"Total Perps: ${total_perps:.2f}\n"
                f"Total Spot: ${total_spot:.2f}\n"
                f"Total Overall: ${total_balance:.2f}\n"
                f"Accounts checked: {total_checked}\n"
                f"{'='*50}"
            )
            logger.info(summary)
            logger.success(f"Successfully checked balances for {total_checked} session(s)")
        else:
            logger.error("Failed to check any balances")
        
