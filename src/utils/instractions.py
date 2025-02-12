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
    VOLUME_RANGE,
    AMOUNT_MULTIPLIER_RANGE,
    TRADES_COUNT_RANGE,
    DISPERSION_RANGE_PERCENT,
    TICKERS,
    ACCOUNT_DISTRIBUTION_IMBALANCE,
    MIN_VOLUME_PER_ACCOUNT,
)



def generate_trade_volume() -> float:
    """Generate a random trade volume within the configured range with random precision"""
    volume = random.uniform(VOLUME_RANGE[0], VOLUME_RANGE[1])
    precision = random.randint(2, 8)  # Random precision between 2 and 8 decimal places
    return round(volume, precision)


def calculate_counter_volume(volume: float) -> float:
    """Calculate counter trade volume with dispersion and random precision"""
    dispersion = random.uniform(DISPERSION_RANGE_PERCENT[0], DISPERSION_RANGE_PERCENT[1])
    counter_volume = volume * (1 + dispersion)
    precision = random.randint(2, 8)  # Random precision between 2 and 8 decimal places
    return round(counter_volume, precision)


def generate_trade_instructions(accounts: List[Dict]) -> Dict:
    """Generate trade instructions based on configuration, using all accounts for each trade"""
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
    total_accounts = len(accounts)
    
    for i in range(trades_count):
        # Generate base volume for this trade
        base_volume = generate_trade_volume()
        counter_volume = calculate_counter_volume(base_volume)
        
        # Calculate random split within configured imbalance range
        mid_point = total_accounts // 2
        max_deviation = int(total_accounts * ACCOUNT_DISTRIBUTION_IMBALANCE / 2)
        if max_deviation < 1:
            max_deviation = 1
            
        deviation = random.randint(-max_deviation, max_deviation)
        long_count = mid_point + deviation
        
        # Ensure we always have at least one account on each side
        long_count = max(1, min(long_count, total_accounts - 1))
        short_count = total_accounts - long_count
        
        # Randomly assign accounts to sides
        all_accounts = accounts.copy()
        random.shuffle(all_accounts)
        long_accounts = all_accounts[:long_count]
        short_accounts = all_accounts[long_count:]
        
        # Distribute volumes among accounts on each side
        long_volumes = distribute_volume(base_volume, len(long_accounts))
        short_volumes = distribute_volume(counter_volume, len(short_accounts))
        
        trade = {
            "pair": random.choice(TICKERS),
            "completed": False,
            "long": {
                "accounts": [
                    {
                        "telegram": account["session_name"],
                        "volume": volume
                    } for account, volume in zip(long_accounts, long_volumes)
                ],
                "total_long_side_volume": base_volume
            },
            "short": {
                "accounts": [
                    {
                        "telegram": account["session_name"],
                        "volume": volume
                    } for account, volume in zip(short_accounts, short_volumes)
                ],
                "total_short_side_volume": counter_volume
            },
            "total_volume": base_volume + counter_volume
        }
        
        instructions["trades"][f"trade{i+1}"] = trade
        total_volume += trade["total_volume"]

    instructions["total_volume"] = round(total_volume, 8)

    # Save instructions to file with modified filename format
    filename = current_time.strftime("%d-%m-%Y_%H-%M-%S") + ".json"
    os.makedirs("data/instructions", exist_ok=True)
    
    file_path = os.path.join("data/instructions", filename)
    with open(file_path, "w") as f:
        json.dump(instructions, f, indent=2)
    
    logger.info(f"Generated trade instructions saved to {file_path}")
    return instructions

def distribute_volume(total_volume: float, num_parts: int) -> List[float]:
    """
    Distribute a total volume into random parts that sum up to the total.
    Raises ValueError if any account would receive less than MIN_VOLUME_PER_ACCOUNT
    """
    if num_parts <= 0:
        return []
    
    # Check if even distribution would be below minimum
    if total_volume / num_parts < MIN_VOLUME_PER_ACCOUNT:
        raise ValueError(
            f"Volume {total_volume} is too low for {num_parts} accounts. "
            f"Please increase VOLUME_RANGE to ensure each account gets at least {MIN_VOLUME_PER_ACCOUNT}"
        )
    
    # Generate random weights
    weights = [random.random() for _ in range(num_parts)]
    weight_sum = sum(weights)
    
    # Distribute volume according to weights with random precision
    volumes = []
    remaining_volume = total_volume
    
    for i, w in enumerate(weights[:-1]):  # Process all except last weight
        precision = random.randint(2, 8)
        volume = round((w / weight_sum) * total_volume, precision)
        volumes.append(volume)
        remaining_volume -= volume
    
    # Last volume gets remaining amount to ensure total adds up exactly
    precision = random.randint(2, 8)
    volumes.append(round(remaining_volume, precision))
    
    return volumes
