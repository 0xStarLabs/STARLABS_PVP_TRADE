import pyrogram
from loguru import logger
import asyncio
import questionary
from questionary import Choice
from eth_account import Account
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import CYCLE_MODE

from src.utils.confirmation_messages import REVEAL_PRIVATE_KEY_MESSAGE, PRIVATE_KEY_MESSAGE, SETTINGS_MESSAGE, CLAN_REGISTRATION_MESSAGE, NEVER_SHARE_PRIVATE_KEY_MESSAGE


class ExportKeys:
    def __init__(self, sessions: list):
        self.sessions = sessions
        self.bot_username = "pvptrade_bot"

    def get_eth_address(self, private_key: str) -> str:
        """Convert private key to ETH address"""
        try:
            account = Account.from_key(private_key)
            return account.address
        except Exception as e:
            logger.error(f"Error converting private key to address: {str(e)}")
            return "error_converting_address"

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
            "Select session to export keys:",
            choices=choices,
            qmark="🔑",
            instruction="Use ↑↓ arrows to navigate, Enter to select"
        ).ask_async()

        if selected == "all":
            return self.sessions
        elif selected:
            return [selected]
        return []

    async def wait_for_message(self, app: pyrogram.Client, text: str, timeout: int = 30) -> tuple[bool, pyrogram.types.Message]:
        """Wait for a specific message to appear"""
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            async for message in app.get_chat_history(self.bot_username, limit=3):
                if message.text and text in message.text:
                    return True, message
            await asyncio.sleep(1)
        return False, None

    async def click_export_button(self, app: pyrogram.Client, settings_message) -> bool:
        """Click the export private key button"""
        try:
            if settings_message.reply_markup:
                for row in settings_message.reply_markup.inline_keyboard:
                    for button in row:
                        if "Export private key" in button.text:
                            logger.info("Found Export private key button")
                            try:
                                await app.request_callback_answer(
                                    chat_id=settings_message.chat.id,
                                    message_id=settings_message.id,
                                    callback_data="export",
                                )
                                logger.info("Export button clicked successfully")
                                # Wait for confirmation message
                                success, _ = await self.wait_for_message(app, NEVER_SHARE_PRIVATE_KEY_MESSAGE)
                                if success:
                                    return True
                                logger.error("Did not receive confirmation message after export click")
                                return False
                            except TimeoutError:
                                # logger.warning("Export button click timed out, but may have succeeded")
                                # Check if we got the message despite timeout
                                success, _ = await self.wait_for_message(app, NEVER_SHARE_PRIVATE_KEY_MESSAGE)
                                if success:
                                    return True
                                logger.error("Did not receive confirmation message after timeout")
                                return False
                            except Exception as e:
                                logger.error(f"Error clicking export button: {str(e)}")
                                return False
            logger.error("Export button not found in settings menu")
            return False
        except Exception as e:
            logger.error(f"Error clicking export button: {str(e)}")
            return False

    async def click_confirmation_button(self, app: pyrogram.Client) -> bool:
        """Click the confirmation button"""
        try:
            async for message in app.get_chat_history(self.bot_username, limit=3):
                if message.reply_markup:
                    for row in message.reply_markup.inline_keyboard:
                        for button in row:
                            if REVEAL_PRIVATE_KEY_MESSAGE in button.text:
                                logger.info("Found confirmation button")
                                try:
                                    await app.request_callback_answer(
                                        chat_id=message.chat.id,
                                        message_id=message.id,
                                        callback_data=button.callback_data,
                                    )
                                    logger.info("Confirmation button clicked successfully")
                                    # Wait for private key message
                                    success, _ = await self.wait_for_message(app, PRIVATE_KEY_MESSAGE)
                                    if success:
                                        return True
                                    logger.error("Did not receive private key after confirmation")
                                    return False
                                except TimeoutError:
                                    # logger.warning("Confirmation click timed out, but may have succeeded")
                                    # Check if we got the message despite timeout
                                    success, _ = await self.wait_for_message(app, PRIVATE_KEY_MESSAGE)
                                    if success:
                                        return True
                                    logger.error("Did not receive private key after timeout")
                                    return False
                                except Exception as e:
                                    logger.error(f"Error clicking confirmation button: {str(e)}")
                                    return False
            logger.error("Confirmation button not found")
            return False
        except Exception as e:
            logger.error(f"Error clicking confirmation button: {str(e)}")
            return False

    async def extract_and_save_key(self, app: pyrogram.Client, session: dict) -> bool:
        """Extract private key from message and save it"""
        try:
            async for message in app.get_chat_history(self.bot_username, limit=3):
                if message.text and PRIVATE_KEY_MESSAGE in message.text:
                    lines = message.text.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('0x'):
                            key = line
                            eth_address = self.get_eth_address(key)
                            export_line = f"{session['user']['username']}:{session['session_name']}:{key}:{eth_address}\n"
                            
                            # Read existing keys to avoid duplicates
                            existing_keys = set()
                            try:
                                with open("data/exported_wallets.txt", "r", encoding='utf-8') as f:
                                    existing_keys = set(f.readlines())
                            except FileNotFoundError:
                                pass

                            if export_line not in existing_keys:
                                with open("data/exported_wallets.txt", "a", encoding='utf-8') as f:
                                    f.write(export_line)
                                logger.success(f"Private key and address exported and saved for {session['session_name']}")
                                logger.info(f"ETH Address: {eth_address}")
                                return True
                            else:
                                logger.info(f"Key already exists for {session['session_name']}, skipping")
                                return True
            logger.error("Private key not found in messages")
            return False
        except Exception as e:
            logger.error(f"Error extracting and saving key: {str(e)}")
            return False

    async def export_single_session(self, session: dict) -> bool:
        """Export keys for a single session"""
        try:
            async with pyrogram.Client(
                name=session["session_name"],
                workdir="data/sessions"
            ) as app:
                logger.info(f"Exporting keys for session {session['session_name']}")
                
                # Send /settings command and wait for response
                await app.send_message(self.bot_username, "/settings")
                success, settings_message = await self.wait_for_message(app, SETTINGS_MESSAGE)
                if not success:
                    logger.error(f"Timeout waiting for settings menu for {session['session_name']}")
                    return False
                
                # Quick check for clan registration
                if CLAN_REGISTRATION_MESSAGE in settings_message.text:
                    logger.error(f"Session {session['session_name']} requires clan registration to proceed")
                    return False
                
                # Click export button (now includes waiting for confirmation message)
                if not await self.click_export_button(app, settings_message):
                    return False
                
                # Click confirmation button (now includes waiting for private key)
                if not await self.click_confirmation_button(app):
                    return False
                
                # Extract and save key
                return await self.extract_and_save_key(app, session)

        except Exception as e:
            logger.error(f"Error processing session {session['session_name']}: {str(e)}")
            return False

    async def export_keys(self):
        """Main export function"""
        selected_sessions = await self.select_sessions()
        if not selected_sessions:
            logger.info("Export cancelled")
            return

        exported_keys = set()
        total_exported = 0

        if CYCLE_MODE:
            # Sequential mode
            logger.info("Running in sequential mode")
            for session in selected_sessions:
                if session["session_name"] in exported_keys:
                    logger.info(f"Skipping already exported session: {session['session_name']}")
                    continue
                    
                if await self.export_single_session(session):
                    exported_keys.add(session["session_name"])
                    total_exported += 1
                await asyncio.sleep(1)  # Small delay between sessions
        else:
            # Parallel mode
            logger.info("Running in parallel mode")
            tasks = []
            for session in selected_sessions:
                if session["session_name"] not in exported_keys:
                    task = self.export_single_session(session)
                    tasks.append(task)
                else:
                    logger.info(f"Skipping already exported session: {session['session_name']}")

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for session, result in zip(selected_sessions, results):
                    if isinstance(result, Exception):
                        logger.error(f"Error exporting session {session['session_name']}: {str(result)}")
                    elif result:
                        exported_keys.add(session["session_name"])
                        total_exported += 1

        if total_exported > 0:
            logger.success(f"Successfully exported {total_exported} key(s)")
        else:
            logger.error("Failed to export any keys")


