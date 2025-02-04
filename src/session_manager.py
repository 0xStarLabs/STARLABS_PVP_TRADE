import pyrogram
from loguru import logger
import os
import json
import aiofiles
from aiofiles.ospath import exists
from src.utils.reader import read_accounts, Account, read_session_json_file


def get_value(file_json: dict, *keys) -> str | None:
    """Получает значение из словаря по нескольким возможным ключам"""
    for key in keys:
        if key in file_json:
            return file_json[key]
    return None


async def create_sessions() -> None:
    """Creates new Telegram sessions from config"""
    # Create sessions directory if it doesn't exist
    session_folder = "data/sessions"
    if not os.path.exists(session_folder):
        os.makedirs(session_folder)

    # Read accounts from config
    accounts = read_accounts()
    if not accounts:
        logger.error("No accounts found in config")
        return

    for account in accounts:
        try:
            # Check if session already exists
            session_file = f"{session_folder}/{account.session_name}.session"
            json_file = f"{session_folder}/{account.session_name}.json"
            
            if os.path.exists(session_file) and os.path.exists(json_file):
                logger.info(f"Session {account.session_name} already exists, skipping")
                continue

            # Log account information before creating session
            logger.info(f"Creating session for account:")
            logger.info(f"Phone: {account.phone}")
            logger.info(f"Session name: {account.session_name}")
            logger.info(f"API ID: {account.app_id}")

            # Create client with config settings
            session = pyrogram.Client(
                api_id=account.app_id,
                api_hash=account.api_hash,
                name=account.session_name,
                workdir=session_folder,
                phone_number=account.phone,
                password=account.password
            )

            # Connect and get user information
            try:
                async with session:
                    user_data = await session.get_me()
            except pyrogram.errors.PasswordHashInvalid:
                logger.error(f"Invalid password for account {account.phone}")
                continue
            except pyrogram.errors.PhoneCodeInvalid:
                logger.error(f"Invalid phone code for account {account.phone}")
                continue

            # Verify that .session file was created
            if not os.path.exists(session_file):
                logger.error(f"Session file was not created at {session_file}")
                continue

            # Save session information to JSON
            session_info = {
                "session_name": account.session_name,
                "phone": account.phone,
                "user": {
                    "id": user_data.id,
                    "username": user_data.username,
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                },
                "api_id": account.app_id,
                "api_hash": account.api_hash,
                "device_model": "Desktop",
                "system_version": "Windows 10",
                "app_version": "1.0",
                "lang_code": "en",
                "system_lang_code": "en",
                "proxy": account.proxy,
            }

            # Save information to JSON file
            async with aiofiles.open(json_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(session_info, indent=4, ensure_ascii=False))

            logger.success(
                f"Successfully added session {user_data.username} | {user_data.first_name} {user_data.last_name}"
            )
            logger.debug(f"Session files created: {session_file} and {json_file}")

        except Exception as e:
            logger.error(f"Error creating session {account.session_name}: {str(e)}")
            continue


async def load_sessions(session_name: str, folder_path: str) -> dict:
    """Загружает информацию о сессии"""
    try:
        session_info = await read_session_json_file(session_name, folder_path)
        if not session_info:
            logger.error(f"Не удалось загрузить информацию о сессии: {session_name}")
            return {}
        return session_info
    except Exception as e:
        logger.error(f"Ошибка при загрузке сессии {session_name}: {str(e)}")
        return {}


async def load_sessions_from_folder(folder_path: str) -> list:
    """Загружает сессии из указанной папки"""
    try:
        if not os.path.exists(folder_path):
            logger.error(f"Папка {folder_path} не существует")
            return []

        sessions = []
        for file in os.listdir(folder_path):
            if file.endswith(".json"):
                session_name = file.replace(".json", "")
                session_info = await load_sessions(session_name, folder_path)
                if session_info:
                    sessions.append(session_info)
        return sessions
    except Exception as e:
        logger.error(f"Ошибка при загрузке сессий из {folder_path}: {str(e)}")
        return []
