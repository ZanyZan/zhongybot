import time
from datetime import datetime, timedelta, timezone
import pytz
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

def get_acquisition_multiplier(inventory, shop_items):
    """
    Checks a user's inventory for a gem booster and returns the corresponding
    acquisition multiplier.
    
    This could be improved by using a more generic approach that allows for
    multiple boosters or different types of effects.
    
    Returns:
        float: The acquisition multiplier (defaults to 1.0 if no booster is found).
               Should consider raising an exception or logging an error if an invalid
               multiplier is encountered"""
    acquisition_multiplier = 1.0  # Default multiplier
    if not inventory:
        return acquisition_multiplier

    gem_booster_item = inventory.get("gem_booster")
    if gem_booster_item and gem_booster_item.get("quantity", 0) > 0:
        booster_effect = shop_items.get("gem_booster", {}).get("effect", {})
        acquisition_multiplier = booster_effect.get("acquisition_multiplier", 1.3)
    
    return acquisition_multiplier
