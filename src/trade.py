import pyrogram
from typing import Set, Dict, List
import asyncio
from loguru import logger
import json
import os
from datetime import datetime
from src.utils.confirmation_messages import (
    TICKER_MESSAGE,
    CHOOSE_LEVERAGE_MESSAGE,
    CHOOSE_POSITION_SIZE_MESSAGE,
    CONFIRM_POSITION_MESSAGE,
    CLOSE_POSITION_MESSAGE,
    CHOOSE_PERCENTAGE_MESSAGE,
    ORDER_PLACED_MESSAGE,
    CLOSED_POSITION_MESSAGE
)
from config import LEVERAGE, TIME_RANGE
import random


class Trade:
    def __init__(self, instructions: dict):
        self.instructions = instructions
        self.sessions = self.extract_session_names()
        self.bot_username = "pvptrade_bot"
        self.instructions_file = None  # Will store the file path
        
    def extract_session_names(self) -> Set[str]:
        """Extract unique session names from trade instructions"""
        session_names = set()
        for trade in self.instructions.get('trades', {}).values():
            for account in trade.get('long', {}).get('accounts', []):
                if 'telegram' in account:
                    session_names.add(account['telegram'])
            for account in trade.get('short', {}).get('accounts', []):
                if 'telegram' in account:
                    session_names.add(account['telegram'])
        return session_names

    async def wait_for_message(self, app: pyrogram.Client, text: str, timeout: int = 30) -> tuple[bool, pyrogram.types.Message]:
        """Wait for a specific message to appear"""
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            async for message in app.get_chat_history(self.bot_username, limit=3):
                if message.text and text in message.text:
                    return True, message
            await asyncio.sleep(1)
        return False, None

    async def select_leverage(self, app: pyrogram.Client, leverage_msg, side: str, ticker: str) -> bool:
        """Select leverage and wait for position size message"""
        if leverage_msg.reply_markup:
            for row in leverage_msg.reply_markup.inline_keyboard:
                for button in row:
                    if f"{LEVERAGE}x" in button.text.lower():
                        try:
                            await app.request_callback_answer(
                                chat_id=leverage_msg.chat.id,
                                message_id=leverage_msg.id,
                                callback_data=button.callback_data
                            )
                            logger.debug(f"Selected {LEVERAGE}x leverage")
                            # Wait for position size message
                            success, _ = await self.wait_for_message(app, CHOOSE_POSITION_SIZE_MESSAGE)
                            if success:
                                return True
                            logger.error("Did not receive position size message after leverage selection")
                            return False
                        except TimeoutError:
                            # Check if we got the message despite timeout
                            success, _ = await self.wait_for_message(app, CHOOSE_POSITION_SIZE_MESSAGE)
                            if success:
                                return True
                            logger.error("Did not receive position size message after timeout")
                            return False
                        except Exception as e:
                            logger.error(f"Error selecting leverage: {str(e)}")
                            return False
        logger.error(f"Could not find {LEVERAGE}x leverage button")
        return False

    async def click_confirm_button(self, app: pyrogram.Client, confirm_msg) -> bool:
        """Click confirm button and wait for confirmation"""
        if confirm_msg.reply_markup:
            for row in confirm_msg.reply_markup.inline_keyboard:
                for button in row:
                    if "confirm" in button.text.lower():
                        try:
                            await app.request_callback_answer(
                                chat_id=confirm_msg.chat.id,
                                message_id=confirm_msg.id,
                                callback_data=button.callback_data
                            )
                            logger.debug("Clicked confirm button")
                            # Wait for order placed message
                            success, _ = await self.wait_for_message(app, ORDER_PLACED_MESSAGE)
                            if success:
                                return True
                            logger.error("Did not receive order placed message after confirmation")
                            return False
                        except TimeoutError:
                            # Check if we got the message despite timeout
                            success, _ = await self.wait_for_message(app, ORDER_PLACED_MESSAGE)
                            if success:
                                return True
                            logger.error("Did not receive order placed message after timeout")
                            return False
                        except Exception as e:
                            logger.error(f"Error clicking confirm: {str(e)}")
                            return False
        logger.error("Could not find confirm button")
        return False

    async def execute_position(self, app: pyrogram.Client, side: str, volume: float, pair: str) -> bool:
        """Execute a single position (long or short)"""
        try:
            # Send trade command
            command = "/long" if side.lower() == "long" else "/short"
            await app.send_message(self.bot_username, command)
            
            # Wait for ticker selection message
            success, msg = await self.wait_for_message(app, TICKER_MESSAGE)
            if not success:
                logger.error("Timeout waiting for ticker message")
                return False

            # Send ticker
            ticker = pair.replace("-PERP", "").lower()
            await app.send_message(self.bot_username, ticker)
            logger.debug(f"Sent ticker: {ticker}")

            # Wait for leverage selection message
            success, leverage_msg = await self.wait_for_message(app, CHOOSE_LEVERAGE_MESSAGE)
            if not success:
                logger.error("Timeout waiting for leverage message")
                return False

            # Debug log all buttons
            # if leverage_msg.reply_markup:
            #     logger.debug("Available leverage buttons:")
            #     for row_idx, row in enumerate(leverage_msg.reply_markup.inline_keyboard):
            #         for btn_idx, button in enumerate(row):
            #             logger.debug(f"Button [{row_idx}][{btn_idx}]: text='{button.text}', callback_data='{button.callback_data}'")

            # Select leverage and wait for position size message
            if not await self.select_leverage(app, leverage_msg, side, ticker):
                return False

            # Send volume
            await app.send_message(self.bot_username, str(volume))
            logger.debug(f"Sent volume: {volume}")

            # Wait for confirmation message
            success, confirm_msg = await self.wait_for_message(app, CONFIRM_POSITION_MESSAGE)
            if not success:
                logger.error("Timeout waiting for confirmation message")
                return False

            # # Debug log confirmation buttons
            # if confirm_msg.reply_markup:
            #     logger.debug("Available confirmation buttons:")
            #     for row_idx, row in enumerate(confirm_msg.reply_markup.inline_keyboard):
            #         for btn_idx, button in enumerate(row):
            #             logger.debug(f"Button [{row_idx}][{btn_idx}]: text='{button.text}', callback_data='{button.callback_data}'")

            # Click confirm button and wait for position opened message
            if not await self.click_confirm_button(app, confirm_msg):
                return False

            logger.success(f"Position executed: {side} {volume} {pair}")
            return True

        except Exception as e:
            logger.error(f"Error executing position: {str(e)}")
            return False

    async def close_position(self, app: pyrogram.Client, pair: str) -> bool:
        """Close position for a specific pair"""
        try:
            # Send close command
            await app.send_message(self.bot_username, "/close")
            logger.debug("Sent /close command")

            # Small delay to ensure we get the bot's response
            await asyncio.sleep(2)

            # Debug log recent messages
            # logger.debug("Recent messages after /close:")
            # async for message in app.get_chat_history(self.bot_username, limit=5):
            #     logger.debug(f"Message text: '{message.text}'")

            # Wait for close position message
            success, close_msg = await self.wait_for_message(app, CLOSE_POSITION_MESSAGE)
            if not success:
                logger.error(f"Timeout waiting for close position message. Expected text: '{CLOSE_POSITION_MESSAGE}'")
                return False

            # Send ticker to close
            ticker = pair.replace("-PERP", "").lower()
            await app.send_message(self.bot_username, ticker)
            logger.debug(f"Sent ticker to close: {ticker}")

            # Wait for percentage selection message
            success, percentage_msg = await self.wait_for_message(app, CHOOSE_PERCENTAGE_MESSAGE)
            if not success:
                logger.error("Timeout waiting for percentage selection message")
                return False

            # # Debug log percentage buttons
            # if percentage_msg.reply_markup:
            #     # logger.debug("Available percentage buttons:")
            #     for row_idx, row in enumerate(percentage_msg.reply_markup.inline_keyboard):
            #         for btn_idx, button in enumerate(row):
            #             logger.debug(f"Button [{row_idx}][{btn_idx}]: text='{button.text}', callback_data='{button.callback_data}'")

            # Click 100% button
            percentage_clicked = False
            if percentage_msg.reply_markup:
                for row in percentage_msg.reply_markup.inline_keyboard:
                    for button in row:
                        if "100%" in button.text:
                            try:
                                await app.request_callback_answer(
                                    chat_id=percentage_msg.chat.id,
                                    message_id=percentage_msg.id,
                                    callback_data=button.callback_data
                                )
                                logger.debug("Selected 100% to close")
                                # Wait for confirmation message
                                success, _ = await self.wait_for_message(app, CONFIRM_POSITION_MESSAGE)
                                if success:
                                    percentage_clicked = True
                                    break
                                logger.error("Did not receive confirmation message after selecting percentage")
                                return False
                            except TimeoutError:
                                # Check if we got the confirmation message despite timeout
                                success, _ = await self.wait_for_message(app, CONFIRM_POSITION_MESSAGE)
                                if success:
                                    percentage_clicked = True
                                    break
                                logger.error("Did not receive confirmation message after percentage timeout")
                                return False
                            except Exception as e:
                                logger.error(f"Error selecting percentage: {str(e)}")
                                return False
                    if percentage_clicked:
                        break

            if not percentage_clicked:
                logger.error("Could not find 100% button")
                return False

            # Wait for confirmation message no longer needed here since we already got it
            success, confirm_msg = await self.wait_for_message(app, CONFIRM_POSITION_MESSAGE)
            if not success:
                logger.error("Timeout waiting for close confirmation message")
                return False

            # Click confirm button
            confirm_clicked = False
            if confirm_msg.reply_markup:
                for row in confirm_msg.reply_markup.inline_keyboard:
                    for button in row:
                        if "confirm" in button.text.lower():
                            try:
                                await app.request_callback_answer(
                                    chat_id=confirm_msg.chat.id,
                                    message_id=confirm_msg.id,
                                    callback_data=button.callback_data
                                )
                                logger.debug("Clicked confirm button")
                                # Wait for closed position message
                                success, _ = await self.wait_for_message(app, CLOSED_POSITION_MESSAGE)
                                if success:
                                    logger.debug("Position close confirmed")
                                    confirm_clicked = True
                                else:
                                    logger.error("Did not receive position closed confirmation")
                                    return False
                            except TimeoutError:
                                # Check if we got the closed message despite timeout
                                success, _ = await self.wait_for_message(app, CLOSED_POSITION_MESSAGE)
                                if success:
                                    logger.debug("Position close confirmed after timeout")
                                    confirm_clicked = True
                                else:
                                    logger.error("Did not receive position closed confirmation after timeout")
                                    return False
                            except Exception as e:
                                logger.error(f"Error clicking confirm: {str(e)}")
                                return False
                            break
                    if confirm_clicked:
                        break

            if not confirm_clicked:
                logger.error("Could not find confirm button")
                return False

            logger.success(f"Position closed for {pair}")
            return True

        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False

    def update_instructions_file(self, trade_id: str):
        """Update the instructions file after completing a trade"""
        if not self.instructions_file:
            # Find the instructions file
            for file in os.listdir("data/instructions"):
                if file.endswith(".json"):
                    with open(f"data/instructions/{file}", "r") as f:
                        data = json.load(f)
                        if data == self.instructions:
                            self.instructions_file = f"data/instructions/{file}"
                            break

        if self.instructions_file:
            # Update the trade status
            self.instructions['trades'][trade_id]['completed'] = True
            self.instructions['total_trades_completed'] += 1
            self.instructions['last_trade_time'] = datetime.now().timestamp()

            # Save updated instructions
            with open(self.instructions_file, "w") as f:
                json.dump(self.instructions, f, indent=4)
            logger.info(f"Instructions updated for {trade_id}")
 
    async def trade(self):
        """Execute all trades in the instructions"""
        try:
            # Create clients for all sessions
            clients = {}
            for session_name in self.sessions:
                clients[session_name] = pyrogram.Client(
                    name=session_name,
                    workdir="data/sessions"
                )

            # Start all clients
            for client in clients.values():
                await client.start()

            # Execute trades sequentially
            for trade_id, trade_info in self.instructions['trades'].items():
                if trade_info.get('completed', False):
                    logger.info(f"Skipping completed trade {trade_id}")
                    continue

                logger.info(f"Executing {trade_id}")
                pair = trade_info['pair']

                # Execute long positions
                long_tasks = []
                for account in trade_info['long']['accounts']:
                    client = clients[account['telegram']]
                    task = self.execute_position(
                        app=client,
                        side="long",
                        volume=account['volume'],
                        pair=pair
                    )
                    long_tasks.append(task)

                # Execute short positions
                short_tasks = []
                for account in trade_info['short']['accounts']:
                    client = clients[account['telegram']]
                    task = self.execute_position(
                        app=client,
                        side="short",
                        volume=account['volume'],
                        pair=pair
                    )
                    short_tasks.append(task)

                # Wait for all positions to be opened
                await asyncio.gather(*long_tasks, *short_tasks)
                logger.success(f"All positions opened for {trade_id}")
                await asyncio.sleep(random.randint(TIME_RANGE[0], TIME_RANGE[1])) 

                # Close all positions
                close_tasks = []
                for session_name, client in clients.items():
                    task = self.close_position(client, pair)
                    close_tasks.append(task)

                await asyncio.gather(*close_tasks)
                logger.success(f"All positions closed for {trade_id}")

                # Update instructions file
                self.update_instructions_file(trade_id)

                # Wait before next trade
                await asyncio.sleep(10)

            # Stop all clients
            for client in clients.values():
                await client.stop()

            return True

        except Exception as e:
            logger.error(f"Error during trading: {str(e)}")
            return False
