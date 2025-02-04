import asyncio
from loguru import logger
import sys
from src.export_keys import ExportKeys
from src.session_manager import create_sessions, load_sessions_from_folder
from src.trade import Trade
from src.utils.reader import load_instructions
from src.utils.instractions import generate_trade_instructions
from src.check_balance import CheckBalances

    
# Logging configuration
logger.remove()

logger.add(
    sys.stdout,
    colorize=True,
    format="<light-cyan>{time:HH:mm:ss:SSS}</light-cyan> | <level>{level: <8}</level> | <white>{file}:{line}</white> | <white>{message}</white>",
)
logger.add(
    "data/logs/app.log",
    rotation="100 MB",
    format="{time:YYYY-MM-DD HH:mm:ss:SSS} | {level: <8} | {file}:{line} | {message}",
    encoding="utf-8",
)


async def main():
    user_action = int(
        input(
            "\n1. Create session"
            "\n2. Start trading"
            "\n3. Show existing sessions"
            "\n4. Generate instructions"
            "\n5. Export private keys"
            "\n6. Check balances"
            "\nSelect action: "
        )
    )

    if user_action == 1:
        await create_sessions()
        logger.success("Sessions successfully added")

    elif user_action == 2:
        instructions = await load_instructions()
        if not instructions:
            logger.error("No instructions loaded")
            return
        print(instructions)
        trade = Trade(instructions)
        if await trade.trade():
            logger.success("Trade completed successfully")
        else:
            logger.error("Trade completed with errors")

    elif user_action == 3:
        sessions = await load_sessions_from_folder("data/sessions")
        logger.info("Check sessions:")
        for session in sessions:
            user = session["user"]
            logger.info(
                f'Session: {session["session_name"]} | '
                f'User: {user["username"]} ({user["first_name"]} {user["last_name"]})'
            )

    elif user_action == 4:
        sessions = await load_sessions_from_folder("data/sessions")
        if not sessions:
            logger.error("No sessions found. Please create sessions first")
            return
        try:
            instructions = generate_trade_instructions(sessions)
            logger.success("Trade instructions generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate instructions: {e}")

    elif user_action == 5:
        sessions = await load_sessions_from_folder("data/sessions")
        if not sessions:
            logger.error("No sessions found. Please create sessions first")
            return
        export_keys = ExportKeys(sessions)
        await export_keys.export_keys()
        logger.success("Keys exported successfully")

    elif user_action == 6:
        sessions = await load_sessions_from_folder("data/sessions")
        if not sessions:
            logger.error("No sessions found. Please create sessions first")
            return
        check_balances = CheckBalances(sessions)
        await check_balances.check_balances()
        logger.success("Balances checked successfully")

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Program stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
