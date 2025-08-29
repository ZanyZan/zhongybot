from datetime import datetime, timedelta, timezone
from firebase_admin import firestore
import operator
import random

#function helper to format an epoch timestamp to a gicen timezone and format
def format_timestamp(timestamp, timezone, format):
  """
  Converts an epoch timestamp into a formatted string 
  based on the specified timezone and format.

  Args:
      timestamp (int): Epoch time in seconds.
      timezone (str): Timezone name from pytz.
      format (str): Desired datetime format.
    Returns:
      str: Formatted date-time string.
  """
  time = datetime.fromtimestamp(timestamp, tz=timezone).strftime(format)
  return time


ops = {'+': operator.add, '-': operator.sub}


#helper function to calculate new times for time command
#using operator module, it does the operation given the string for the operator it receives
def calculate_time(time1, operator, time2):
    new_time = ops[operator](time1, time2)
    return new_time

def get_start_of_week(date: datetime) -> datetime:
  """
  Calculates a new time based on the operator provided.
  
  Args:
      time1 (int): First time (epoch in seconds).
      operator (str): Operator ('+' or '-').
      time2 (int): Second time to add or subtract.
      
  Returns:
      int: Resulting time in epoch seconds.
    """
  # Calculate the start of the week (Monday)
  start_of_week = date - timedelta(days=date.weekday())
  return start_of_week


def get_end_of_week(start_of_week: datetime) -> datetime:
  """
    Calculates the end of the week (Sunday) for a given start date (Monday).
    
    Args:
        date (datetime): Input date.
    
    Returns:
        datetime: Start of the week (Monday).
  """
  # Calculate the end of the week (Sunday)
  end_of_week = start_of_week + timedelta(days=6)
  return end_of_week

#Helper function to split a large response from LLM to accomodate discord lengths
def split_response(response_text, max_length):
  """Splits a long text into chunks that fit within a max_length."""
  chunks = []
  current_chunk = ""
  # Splitting by sentences is not robust, as periods can appear in other contexts.
  # Consider a more sophisticated approach, perhaps using a dedicated sentence splitter or a character limit with a "..." cutoff.
  for sentence in response_text.split('. '): # Simple split by sentence
    if len(current_chunk) + len(sentence) + 2 <= max_length: # +2 for ". "
      current_chunk += sentence + ". "
    else:
      chunks.append(current_chunk.strip())
      current_chunk = sentence + ". "
  if current_chunk.strip():
    chunks.append(current_chunk.strip())
  return chunks

def capi_sentence(sentence: str) -> str:
    """
    Applies a capitalization pattern to a sentence where letters alternate between upper and lower case,
    but with added randomness and tracking of consecutive cases to create a "wavy" capitalization effect.

    Args:
        sentence (str): The input sentence.

    Returns:
        str: The sentence with alternating capitalization.
    """
    result = ""
    last_upper = False  # Track last capitalization

    for i, char in enumerate(sentence.lower()):
        if i < 2:  # Handle the first two characters randomly
            result += char.upper() if random.random() < 0.5 else char
            last_upper = result[-1].isupper()
        else:
            # Check for consecutive cases
            if (result[i-2].isupper() and result[i-1].isupper()) or \
               (result[i-2].islower() and result[i-1].islower()):
                # Invert capitalization if consecutive cases
                if result[i-1].isupper():
                    result += char.lower()
                    last_upper = False
                else:
                    result += char.upper()
                    last_upper = True
            else:
                # Otherwise, apply random capitalization
                if random.random() < 0.5:
                    result += char.upper()
                    last_upper = True
                else:
                    result += char.lower()
                    last_upper = False
    return result

def are_dates_in_same_week(date1: datetime, date2: datetime) -> bool:
  """
  Checks if two dates fall within the same week (Monday to Sunday).
  
  Args:
      date1 (datetime): First date.
      date2 (datetime): Second date.
  
  Returns:
      bool: True if both dates are in the same week, False otherwise.  
  """
# Get the start and end of the week for both dates
  start_of_week_date1 = get_start_of_week(date1)
  end_of_week_date1 = get_end_of_week(start_of_week_date1)

  start_of_week_date2 = get_start_of_week(date2)
  end_of_week_date2 = get_end_of_week(start_of_week_date2)

# Check if the weeks overlap
  return start_of_week_date1 <= end_of_week_date2 and start_of_week_date2 <= end_of_week_date1


def format_month_day(date_str: str, year: int = None) -> datetime:
  """
  Converts a month-day string into a datetime object.
  
  Args:
      date_str (str): Date string in 'Mon-DD' format.
      year (int, optional): Year to append. Defaults to the current year.
  
  Returns:
      datetime: Formatted date object.
    
    Raises:
        ValueError: If the date string is not in 'Mon-DD' format.
    """
  # Set the default year to the current year if not provided
  if year is None:
    year = datetime.now().year

  # Parse the month and day from the string
  try:
    month_day = datetime.strptime(date_str, '%b-%d')
  except ValueError:
    raise ValueError("Date string must be in 'Mon-DD' format")

  # Create a new datetime object with the provided year, and parsed month and day
  formatted_date = datetime(year, month_day.month, month_day.day)
  return formatted_date

def convert(seconds: int) -> str:
    """
    Converts a number of seconds into a human-readable string in HH:MM:SS format.
    
    Args:
        seconds (int): The number of seconds to convert.
    
    Returns:
        str: Formatted time string in HH:MM:SS.
    """
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)


def get_acquisition_multiplier(inventory: dict) -> float:
    """
    Checks a user's inventory for a gem booster and returns the corresponding
    acquisition multiplier from the inventory data.

    This function relies on the item's 'effect' dictionary being stored
    in the user's inventory document in Firebase upon purchase.

    Args:
        inventory: The user's inventory dictionary from Firebase.

    Returns:
        The acquisition multiplier (defaults to 1.0 if no booster is found).
    """
    if not inventory:
        return 1.0

    # Check for the specific booster item in the user's inventory
    gem_booster_item = inventory.get("gem_booster")
    if gem_booster_item and gem_booster_item.get("quantity", 0) > 0:
        # The effect is stored directly with the item in the user's inventory
        booster_effect = gem_booster_item.get("effect", {})
        # Get the multiplier from the effect, defaulting to 1.0 if not found
        return booster_effect.get("acquisition_multiplier", 1.0)
    
    return 1.0




EIGHT_BALL_ANSWERS = [
    # Affirmative
    "It is certain. As certain as taxes and server maintenance.",
    "It is decidedly so. The RNG gods are smiling upon you.",
    "Without a doubt. Go for it!",
    "Yes, definitely. You can bet your meso on it.",
    "You may rely on it. It's a sure thing.",
    "As I see it, yes. The outlook is as good as hitting a double prime line.",
    "Most likely. I'd put money on it, if I had any.",
    "Outlook good. It's a green light from me.",
    "Yes. Simple as that.",
    "Signs point to yes, but don't quote me on that.",
    # Non-committal
    "Reply hazy, try again. My crystal ball is as foggy as a map full of kishin smoke.",
    "Ask again later. I'm in the middle of a boss fight.",
    "Better not tell you now... spoilers!",
    "Cannot predict now. I'm getting server lag on that request.",
    "Concentrate and ask again. Maybe sacrifice a Pitched Boss item to the RNG gods first.",
    # Negative
    "Don't count on it. The odds are worse than getting a pitched drop.",
    "My reply is a resounding NO.",
    "My sources (who are totally not in this room) say no.",
    "Outlook not so good. It's like trying to solo Black Mage with a level 10 character.",
    "Very doubtful. I have a better chance of understanding the lore.",
    "Ask Greg about it. He probably knows.", # Special
]

# Define the shop items
shop_items = {
    "gem_booster": {
        "name": "Gem Acquisition Booster",
        "description": "Passively increases your gem acquisition rate. (Does not apply to slots)",
        "cost": 500, # Example cost
        "type": "passive", # Indicate it's a passive item
        "effect": {"acquisition_multiplier": 1.3}
    },
    "curse_ward": {
        "name": "Curse Ward",
        "description": "Supposedly improves your odds and makes you more resistant to misfortune.",
        "cost": 750,
        "type": "passive",
        "effect": {}
    },
    "luck_charm": {
        "name": "Luck Charm",
        "description": "Supposedly boosts your item drop rate in other games. (Such as MapleStory)",
        "cost": 1000,
        "type": "passive",
        "effect": {}
    },
    "golden_maple_leaf": {
        "name": "Golden Maple Leaf",
        "description": "A perfectly preserved, gilded maple leaf. A true collector's item for the distinguished Mapler.",
        "cost": 5000,
        "type": "passive",
        "effect": {}
    },
    "pitched_fragment": {
        "name": "Pitched Boss Fragment",
        "description": "A fragment of a mythical boss item. It hums with untold power... or maybe it's just a shiny rock. A true status symbol.",
        "cost": 10000,
        "type": "passive",
        "effect": {}
    },
    "zhongys_blessing": {
        "name": "Zhongy's Blessing",
        "description": "A small, carved charm that looks suspiciously like the bot. It offers no real benefits, but it feels nice to have.",
        "cost": 2500,
        "type": "passive",
        "effect": {}
    },
    "zyn_ban_hammer": {
        "name": "The Zyn Ban Hammer",
        "description": "For the low, low price of 99999 gems, you can ban Zyn. Or can you?",
        "cost": 99999,
        "type": "passive",
        "effect": {}
    },
    "pickaxe": {
        "name": "Sturdy Pickaxe",
        "description": "Allows you to use the `~mine` command to find gems. A must-have for any serious gem collector.",
        "cost": 500,
        "type": "passive",
        "effect": {}
    },
    "suspicious_bag": {
        "name": "Suspicious-Looking Bag",
        "description": "What's inside? Could be gems, could be nothing, or it could be a curse that makes the bot mock you for an hour. High risk, high reward!",
        "cost": 50,
        "type": "consumable",
        "effect": {}
    },
    "rigged_ticket": {
        "name": "Slot Machine Rigged Ticket",
        "description": "Guarantees a small win on your next slot machine pull. One-time use. Don't tell Zany.",
        "cost": 25,
        "type": "consumable",
        "effect": {"guaranteed_slot_win": "small"}
    },
        'unicorn': {
        'name': 'Gem-finding Unicorn',
        'description': 'A fabulous and magical unicorn that helps you find 20% more gems when mining. "Leave everything to me, darling!"',
        'cost': 2500,
        'type': 'unique',
        'effect': {'mining_multiplier': 1.20}
    },
}
# Pickaxe upgrade costs and max level

PICKAXE_UPGRADE_COSTS = {
    1: 750,   # To level 2
    2: 1200,  # To level 3
    3: 2000,  # To level 4
    4: 5000,  # To level 5
}
MAX_PICKAXE_LEVEL = 5
PICKAXE_LEVEL_REWARDS = {
    1: (1, 5), 2: (3, 7), 3: (5, 10), 4: (7, 15), 5: (10, 20),
}

@firestore.transactional
def perform_upgrade_transaction(transaction, user_ref):
    """
    Performs the pickaxe upgrade within a Firestore transaction.
    This function can be called from the main command handler.
    """
    snapshot = user_ref.get(transaction=transaction)
    if not snapshot.exists:
        return "no_inventory", None

    user_data = snapshot.to_dict()
    inventory = user_data.get('inventory', {})
    pickaxe_data = inventory.get('pickaxe')

    if not pickaxe_data:
        return "no_pickaxe", None

    current_level = pickaxe_data.get('level', 1)
    if current_level >= MAX_PICKAXE_LEVEL:
        return "max_level", None

    upgrade_cost = PICKAXE_UPGRADE_COSTS.get(current_level)
    if not upgrade_cost:
        # This case handles if the level is somehow out of bounds of the cost dictionary
        return "max_level", None

    current_gems = user_data.get('gem_count', 0)
    if current_gems < upgrade_cost:
        return "not_enough_gems", upgrade_cost

    # Deduct cost and upgrade pickaxe
    inventory['pickaxe']['level'] = current_level + 1
    
    transaction.update(user_ref, {
        'gem_count': firestore.Increment(-upgrade_cost),
        'inventory': inventory
    })

    return "success", (current_level + 1, upgrade_cost)
