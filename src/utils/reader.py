from dataclasses import dataclass
from typing import List
from loguru import logger
import json
import os
import aiofiles
from aiofiles.ospath import exists
from datetime import datetime
import questionary
from questionary import Choice


@dataclass
class Account:
    phone: str
    password: str
    app_id: int
    api_hash: str
    session_name: str
    proxy: str = None

async def load_instructions():
    """Load instructions interactively from available files"""
    instructions_dir = "data/instructions"
    if not os.path.exists(instructions_dir):
        logger.error("Instructions directory not found")
        return {}
        
    instruction_files = [f for f in os.listdir(instructions_dir) if f.endswith('.json')]
    if not instruction_files:
        logger.error("No instruction files found")
        return {}

    # Sort files by creation time, newest first
    instruction_files.sort(key=lambda x: os.path.getctime(os.path.join(instructions_dir, x)), reverse=True)
    
    # Create choices list with file info
    choices = []
    for file in instruction_files:
        file_path = os.path.join(instructions_dir, file)
        creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                total_volume = data.get('total_volume', 0)
                completed = data.get('completed', False)
                trades_count = data.get('total_trades', 0)
                
                status = "✅ Completed" if completed else "⏳ In Progress"
                
                # Format the choice text with extra newlines
                choice_text = (
                    f"{file} | {status}\n"
                    f"   Created: {creation_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"   Trades: {trades_count} | Volume: {total_volume:.8f}\n"
                )
                
                choices.append(Choice(
                    title=choice_text,
                    value=file_path
                ))
        except Exception as e:
            logger.error(f"Error reading file {file}: {e}")
            continue

    if not choices:
        logger.error("No valid instruction files found")
        return {}

    # Add a cancel option
    choices.append(Choice(title="❌ Cancel", value=None))

    # Show interactive selection
    try:
        selected = await questionary.select(
            "Select instructions file:",
            choices=choices,
            qmark="📋",
            instruction="Use ↑↓ arrows to navigate, Enter to select",
            use_indicator=True,
            use_shortcuts=True,
            style=questionary.Style([
                ('separator', 'fg:#6C6C6C'),  # Style for the separator
            ])
        ).ask_async()

        if not selected:  # User selected Cancel or pressed Ctrl+C
            logger.info("Instruction selection cancelled")
            return {}

        # Load and return the selected instructions
        with open(selected, 'r') as f:
            instructions = json.load(f)
            logger.info(f"Loaded instructions from {os.path.basename(selected)}")
            return instructions

    except Exception as e:
        logger.error(f"Error during instruction selection: {e}")
        return {}

def read_accounts() -> List[Account]:
    """
    Reads account configuration from telegram_accounts.txt
    Format: phone:password:app_id:api_hash

    Returns:
        List[Account]: List of Account objects with account data
    """
    try:
        accounts = []
        with open("data/telegram_accounts.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    phone, password, app_id, api_hash = line.split(":")
                    # Convert phone to international format if needed
                    if not phone.startswith("+"):
                        phone = "+" + phone
                        
                    # Create session name from phone number
                    session_name = f"session_{phone.replace('+', '')}"
                    
                    # Debug log the API credentials
                    logger.debug(f"API ID: {app_id} (type: {type(app_id)})")
                    logger.debug(f"API Hash: {api_hash}")
                    
                    account = Account(
                        phone=phone,
                        password=None if password.lower() == "pass" else password,
                        app_id=int(app_id),  # Ensure app_id is converted to int
                        api_hash=api_hash.strip(),  # Ensure no whitespace in api_hash
                        session_name=session_name,
                        proxy=None
                    )
                    accounts.append(account)
                    logger.debug(
                        f"Loaded account: {account.phone} | {account.session_name} | "
                        f"API ID: {account.app_id} | API Hash: {account.api_hash}"
                    )
                except ValueError as e:
                    logger.error(f"Error parsing account line '{line}': {e}")
                    continue

        return accounts

    except Exception as e:
        logger.error(f"Error reading telegram_accounts.txt: {e}")
        return []


async def read_session_json_file(session_name: str, folder_path: str) -> dict:
    """Читает JSON файл сессии и возвращает словарь с настройками"""
    file_path: str = f"{folder_path}/{session_name}.json"

    try:
        if not await exists(file_path):
            logger.error(f"Файл сессии не найден: {file_path}")
            return {}

        async with aiofiles.open(file=file_path, mode="r", encoding="utf-8") as file:
            return json.loads(await file.read())

    except Exception as error:
        logger.error(f"{session_name} | Ошибка при чтении .json файла: {error}")
        return {}
