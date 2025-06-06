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

def get_start_of_week(date):
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


def get_end_of_week(start_of_week):
  """
    Calculates the start of the week (Monday) for a given date.
    
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
  for sentence in response_text.split('. '): # Simple split by sentence
    if len(current_chunk) + len(sentence) + 2 <= max_length: # +2 for ". "
      current_chunk += sentence + ". "
    else:
      chunks.append(current_chunk.strip())
      current_chunk = sentence + ". "
  if current_chunk.strip():
    chunks.append(current_chunk.strip())
  return chunks

def capi_sentence(sentence):
    new_sentence = ""
    number = 0 #Dummy number for tracking

    for letter in sentence.lower():
        if len(new_sentence)<2: #Creates the first two letter
            random_number = random.randint(0,1) #This randomly decides if the letter should be upper or lowercase
            if random_number==0:
                new_sentence += letter.upper()
            else:
                new_sentence += letter
        else:
            if (new_sentence[number-2].isupper() and new_sentence[number-1].isupper() or new_sentence[number-2].islower() and new_sentence[number-1].islower())==True:
                #Checks if the two letters before are both upper or lowercase
                if new_sentence[number-1].isupper(): #Makes the next letter the opposite of the letter before
                    new_sentence += letter.lower()
                else:
                    new_sentence += letter.upper()
            else:
                random_number = random.randint(0,1)
                if random_number==0:
                    new_sentence += letter.upper()
                else:
                    new_sentence += letter
                
        number += 1 #Add one more to the tracking
     
    return(new_sentence)
    
def are_dates_in_same_week(date1, date2):
  """
    Checks if two dates fall within the same week.
    
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


def format_month_day(date_str, year=None):
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
