import json
import random
from datetime import datetime
import os
from typing import Dict, List
import sys
from loguru import logger
import questionary
from questionary import Choice

# Import configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import (
    TIME_RANGE,
    VOLUME_RANGE,
    AMOUNT_MULTIPLIER_RANGE,
    TRADES_COUNT_RANGE,
    DISPERSION_RANGE_PERCENT,
    TICKERS,
)



def generate_trade_volume() -> float:
    """Generate a random trade volume within the configured range"""
    return round(random.uniform(VOLUME_RANGE[0], VOLUME_RANGE[1]), 8)


def calculate_counter_volume(volume: float) -> float:
    """Calculate counter trade volume with dispersion"""
    dispersion = random.uniform(DISPERSION_RANGE_PERCENT[0], DISPERSION_RANGE_PERCENT[1])
    counter_volume = volume * (1 + dispersion)
    return round(counter_volume, 8)


def generate_trade_instructions(accounts: List[Dict]) -> Dict:
    """Generate trade instructions based on configuration"""
    if len(accounts) < 2:
        raise ValueError("Need at least 2 accounts for trading")

    current_time = datetime.now()
    trades_count = random.randint(TRADES_COUNT_RANGE[0], TRADES_COUNT_RANGE[1])
    
    instructions = {
        "total_trades": trades_count,
        "total_trades_completed": 0,
        "total_volume": 0,
        "total_volume_completed": 0,
        "last_trade_time": 0,
        "start_time": current_time.isoformat(),
        "completed": False,
        "trades": {}
    }

    total_volume = 0
    
    for i in range(trades_count):
        # Generate base volume for this trade
        base_volume = generate_trade_volume()
        counter_volume = calculate_counter_volume(base_volume)
        
        # Randomly select accounts for long and short positions
        long_account = random.choice(accounts)
        short_account = random.choice([acc for acc in accounts if acc != long_account])
        
        trade = {
            "pair": random.choice(TICKERS),
            "completed": False,
            "long": {
                "accounts": [
                    {
                        "telegram": long_account["session_name"],
                        "volume": base_volume
                    }
                ],
                "total_long_side_volume": base_volume
            },
            "short": {
                "accounts": [
                    {
                        "telegram": short_account["session_name"],
                        "volume": counter_volume
                    }
                ],
                "total_short_side_volume": counter_volume
            },
            "total_volume": base_volume + counter_volume  # Total volume for both sides
        }
        
        instructions["trades"][f"trade{i+1}"] = trade
        total_volume += trade["total_volume"]

    instructions["total_volume"] = round(total_volume, 8)

    # Save instructions to file with modified filename format
    filename = current_time.strftime("%d-%m-%Y_%H-%M-%S") + ".json"  # Changed : to - and added _
    os.makedirs("data/instructions", exist_ok=True)
    
    file_path = os.path.join("data/instructions", filename)
    with open(file_path, "w") as f:
        json.dump(instructions, f, indent=2)
    
    logger.info(f"Generated trade instructions saved to {file_path}")
    return instructions