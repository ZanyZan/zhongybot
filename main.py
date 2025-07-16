import discord
import os
from discord.ext import tasks
import time
from datetime import datetime, timedelta, timezone
import pytz
import operator
import random
import re
import google.generativeai as genai
import asyncio
import math
import sys
from dotenv import load_dotenv
from google.cloud.firestore_v1.base_query import FieldFilter
aui = [90936340002119680, 264507975568195587]
load_dotenv()
free_emoji_unicode = '\U0001F193'
gem_emoji_unicode = '\U0001F48E'
sparkle_emoji_unicode = '\U00002728'
discord_max_length = 2000
max_history_length = 20
min_gem_spawn_interval = 21600 #6 hours
max_gem_spawn_interval = 43200 #12 hours
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
gem_spawn_channel_id = 808341519714484246
spawned_gem_message_id = 0
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from bot_comm import command_handlers, shop_items
import logging
from helper import format_timestamp, calculate_time, get_start_of_week, get_end_of_week, split_response, capi_sentence, are_dates_in_same_week, format_month_day, convert
first_claim_timestamp = {}

try:
    cred = credentials.Certificate('/home/zanypi/env/gen-lang-client-0697881417-firebase-adminsdk-fbsvc-c6eb0253de.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.info("Firebase initialized successfully!")
except Exception as e:
    logging.error(f"Error initializing Firebase: {e}")
    db = None # Set db to None if initialization fails

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("zhongybot.log"),
                        logging.StreamHandler(sys.stdout)
                    ])

client = discord.Client(intents=intents)
my_secret = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash-preview-05-20')
#get the time in epoch and transform to an int to use
my_time = int(time.time())

#I need to update my time to get more precise time...
@tasks.loop(seconds=15)
async def update_my_time():
  """
  Updates the global variable 'my_time' every 15 seconds with the current epoch time.
  """
  global my_time
  my_time = int(time.time())

@tasks.loop()
async def spawn_gem():
    """
    Randomly spawns a gem emoji in a specified channel for users to claim by reacting.
    """    
    await client.wait_until_ready()

    channel = client.get_channel(gem_spawn_channel_id)
    if channel:
        try:
            is_sparkly = random.randint(1,5)
            if is_sparkly <= 1:
                message_content = f"Wow! {sparkle_emoji_unicode}{gem_emoji_unicode}{sparkle_emoji_unicode} A shiny gem has appeared! Go claim it!"
                logging.info("Sparkly gem spawned!")
            else:
                message_content = f"A wild {gem_emoji_unicode} has appeared! Go claim it!"
                print("Regular gem spawned.")
            # Add the gem emoji as a reaction to the message
            message = await channel.send(message_content)
            await message.add_reaction(gem_emoji_unicode)
            global spawned_gem_message_id # Use global to modify the global variable
            spawned_gem_message_id = message.id
            first_claim_timestamp[spawned_gem_message_id] = None
            logging.info(f"Gem spawn message sent with ID {spawned_gem_message_id}")
        except Exception as e:
            logging.error(f"Error sending gem spawn message: {e}")
    else:
        logging.warning(f"Channel with ID {gem_spawn_channel_id} not found.")

    # After spawning a gem, reschedule the loop with a new random interval
    seconds = random.randint(min_gem_spawn_interval, max_gem_spawn_interval)
    spawn_gem.change_interval(seconds=seconds)
    print(f"Next gem will spawn in {convert(seconds)}")


async def manual_gem_spawn():
    """Manually spawn a gem (triggered by admin command)."""
    channel = client.get_channel(gem_spawn_channel_id)
    if channel:
        try:
            is_sparkly = random.randint(1,5)
            if is_sparkly <= 1:
                message_content = f"Wow! {sparkle_emoji_unicode}{gem_emoji_unicode}{sparkle_emoji_unicode} A shiny gem has appeared! Go claim it!"
                logging.info("Sparkly gem spawned!")
            else:
                message_content = f"A wild {gem_emoji_unicode} has appeared! Go claim it!"
                print("Regular gem spawned.")
            # Add the gem emoji as a reaction to the message
            message = await channel.send(message_content)
            await message.add_reaction(gem_emoji_unicode)
            global spawned_gem_message_id # Use global to modify the global variable
            spawned_gem_message_id = message.id
            first_claim_timestamp[spawned_gem_message_id] = None
            logging.info(f"Gem spawn message sent with ID {spawned_gem_message_id}")
        except Exception as e:
            logging.error(f"Error sending gem spawn message: {e}")

@client.event
async def on_ready():
  """
    Event triggered when the bot is ready. Starts the time update loop.
  """
  update_my_time.start()
  client.loop.create_task(start_gem_spawning())  # Start the gem spawn task

  logging.info("logged in as {0.user}".format(client))


async def start_gem_spawning():
    """
    Handles the initial random delay before starting the gem spawn loop.
    """
    await client.wait_until_ready()
    # Calculate a random initial delay (using your min/max intervals)
    initial_delay = random.randint(min_gem_spawn_interval, max_gem_spawn_interval)
    logging.info(f"Waiting for initial gem spawn delay of {convert(initial_delay)}")
    await asyncio.sleep(initial_delay)

    # Set the first interval for the loop and start it
    # You might want to set a new random interval here for the first actual spawn
    spawn_gem.change_interval(seconds=random.randint(min_gem_spawn_interval, max_gem_spawn_interval))
    spawn_gem.start()
    logging.info("Gem spawn loop started.")


@client.event
async def on_message(message):
  """
  Event triggered when a message is received. Processes the message to handle various commands.

  Args:
      message (discord.Message): The message object received from the channel.
  """
  #if message is from bot, ignore
  if (message.author == client.user):
    return
  elif re.search(r'dex.*?(?:is )?(free|{})'.format(re.escape(free_emoji_unicode)), message.content.lower(), re.DOTALL):
    response = 'No it isn\'t'
    new = await message.reply(response)

  # Check if the message is a private message
  if isinstance(message.channel, discord.DMChannel):
      # Process the command if it starts with '~forward'
      if message.content.lower().startswith('~forward'):
          # Extract the command
          command = message.content[1:].lower().split()[0]
          handler = command_handlers.get(command)

          if handler:
              await handler(message, client=client)
      else:
          # Optionally, send a message back to the user if the private message doesn't use the forward command
          await message.channel.send("To forward a message to the server, please start your message with `~forward` followed by the message you want to send.")
  elif message.content.startswith('~'):
      command = message.content[1:].lower().split()[0]
      handler = command_handlers.get(command)
      if handler:
          # Pass necessary arguments based on the command
          if command in ['ask']:
              await handler(message, db=db, model=model, max_history_length=max_history_length, discord_max_length=discord_max_length)
          elif command in ['deletehistory', 'checkgems', 'givegems', 'takegems', 'slots', 'buy', 'inventory']:
              await handler(message, db=db)
          elif command in ['ursus', 'servertime', 'time']:
              await handler(message, my_time=my_time) # Pass my_time here
          elif command in ['wipegems']:
              await handler(message, db, 808729400920899635) #Member role id for debris
          else: # For commands that don't need extra arguments
              await handler(message)
      elif command == 'spawngem':
            if message.author.id not in aui:
                await message.channel.send("You are not authorized to use this command.")
                return
            else:
                await manual_gem_spawn()


  if message.content.lower() == 'aran succ' and (875235978971861002 in list(
    role.id for role in message.author.roles)):
    response = f"Hey {message.author.display_name}, heard you play Aran. You have my condolences. You should gather everyone and go Hunter's Prey Changseop for this travesty"
    new = await message.reply(response)
    await new.add_reaction('<:FeelsAranMan:852726957091323934>')

  if message.author.id == 257995877367414785:
      roll = random.randint(1, 100)
      logging.info(f"Ub3r rolled {roll}")
      if roll <= 7:
          text = message.content.lower()
          response = capi_sentence(text) # Using capi_sentence from helpers
          await message.reply(response, mention_author=False)
  elif message.author.id == 249678251226562561:
      roll = random.randint(1,100)
      print("Harri rolled", roll)
      if roll <= 3:
          roll = random.randint(1,4)
          if roll <= 3:
              text = message.content.lower()
              response = capi_sentence(text) # Using capi_sentence from helpers
              await message.reply(response, mention_author=False)
          else: # 25% chance for the custom message using Gemini
              if model:  # Ensure the Gemini model is initialized
                  try:
                      # Define your custom Gemini prompt here
                      gemini_prompt = "In a way that shuts him up remind the user named Harri that he has a 70 boss damage familiar card, which is extremely rare. You are the one addressing him directly and make it short"

                      response = model.generate_content([gemini_prompt])
                      # Split the response if it's too long for Discord
                      response_chunks = split_response(response.text, discord_max_length)
                      for chunk in response_chunks:
                          await message.channel.send(chunk)

                  except Exception as e:
                      logging.error(f"An error occurred during custom Gemini interaction: {e}")
                      await message.channel.send("Sorry, I couldn't generate a response for you at this time.")
 
@client.event
async def on_reaction_add(reaction, user):
    """
    Handles reactions added to messages. Checks for reactions on gem spawn messages
    and records claims in Firebase.
    """
    # Ignore reactions from the bot itself or if Firebase is not initialized
    gem_counts = [2, 3, 4, 5, 6]
    weights = [0.5, 0.25, 0.15, 0.07, 0.03]

    if user == client.user or db is None:
        return

    # Check if the reaction is the gem emoji and on the current spawned gem message
    if str(reaction.emoji) == gem_emoji_unicode and reaction.message.author == client.user and reaction.message.id == spawned_gem_message_id:
        message_id = reaction.message.id
        channel = reaction.message.channel

        # Check if the user has already claimed this specific gem
        gem_claims_ref = db.collection('gem_claims')
        query = gem_claims_ref.where(filter=FieldFilter('message_id', '==', message_id)).where(filter=FieldFilter('user_id', '==', user.id)).limit(1)
        docs = query.stream()

        claimed_by_user = False
        for doc in docs:
            claimed_by_user = True
            break  # User has already claimed this gem

        if not claimed_by_user:
            current_time = datetime.now(timezone.utc)

            # Get the timestamp of the first claim, if any.
            first_claim_time = first_claim_timestamp.get(message_id)

            if first_claim_time is None:  # This means it's the first claim.
                # Record the timestamp for this first claim.
                first_claim_timestamp[message_id] = current_time
                logging.info(f"First claim on gem message {message_id} at {current_time}")
                is_sparkly_claim = f"{sparkle_emoji_unicode}{gem_emoji_unicode}{sparkle_emoji_unicode}" in reaction.message.content  # Determine if it's a sparkly gem.

                # Determine base gem count
                if is_sparkly_claim:
                    base_gem_count = random.randint(6, 10) # Example: sparkly gems give 6-10 gems
                    logging.info(f"Sparkly gem claimed! User {user.display_name} gets {base_gem_count} base gems.")
                else:
                    base_gem_count = random.choices(gem_counts, weights=weights, k=1)[0]
                    logging.info(f"Regular gem claimed! User {user.display_name} gets {base_gem_count} base gems.")


                # Check user's inventory for gem acquisition booster
                user_doc_ref = db.collection('user_gem_counts').document(str(user.id))
                user_doc = user_doc_ref.get()
                acquisition_multiplier = 1.0 # Default multiplier
                if user_doc.exists:
                    inventory = user_doc.to_dict().get('inventory', {})
                    gem_booster_item = inventory.get("gem_booster")
                    if gem_booster_item and gem_booster_item.get("quantity", 0) > 0:
                         booster_effect = shop_items.get("gem_booster", {}).get("effect", {})
                         acquisition_multiplier = booster_effect.get("acquisition_multiplier", 1.0) # Default multiplier
                         logging.info(f"User {user.display_name} has gem booster. Applying multiplier: {acquisition_multiplier}")


                # Calculate final gem count after applying multiplier using ceiling formula
                gemcount = math.ceil(base_gem_count * acquisition_multiplier)
                logging.info(f"Final gem count after multiplier: {gemcount}")


                try:
                    # Record the claim in Firebase
                    gem_claims_ref.add({
                        'message_id': message_id,
                        'user_id': user.id,
                        'username': user.display_name,
                        'timestamp': firestore.SERVER_TIMESTAMP  # Use server timestamp
                    })

                    # Update user's gem count and ensure inventory is not overwritten
                    user_gem_counts_ref = db.collection('user_gem_counts').document(str(user.id))
                    # Only set inventory if it doesn't exist
                    user_doc = user_gem_counts_ref.get()
                    update_data = {
                        'username': user.display_name,
                        'gem_count': firestore.Increment(gemcount)
                    }
                    if not user_doc.exists or 'inventory' not in user_doc.to_dict():
                        update_data['inventory'] = {}  # Initialize inventory only if missing
                    user_gem_counts_ref.set(update_data, merge=True)

                    await channel.send(f"{user.display_name} has obtained {gemcount} gem(s)")
                    logging.info(f"ID:{user.id} claimed the gem")
                except Exception as e:
                    logging.error(f"Error recording gem claim in Firebase: {e}")
                    await channel.send("A server error occurred while trying to claim the gem.")

            elif (current_time - first_claim_time).total_seconds() <= 30: # Not the first claim, check if within 30 seconds.
                    # Determine if it was a sparkly gem based on the message content
                is_sparkly_claim = f"{sparkle_emoji_unicode}{gem_emoji_unicode}{sparkle_emoji_unicode}" in reaction.message.content

                # Determine base gem count
                if is_sparkly_claim:
                    base_gem_count = random.randint(6, 10) # Example: sparkly gems give 6-10 gems
                    logging.info(f"Sparkly gem claimed! User {user.display_name} gets {base_gem_count} base gems.")
                else:
                    base_gem_count = random.choices(gem_counts, weights=weights, k=1)[0]
                    logging.info(f"Regular gem claimed! User {user.display_name} gets {base_gem_count} base gems.")


                # Check user's inventory for gem acquisition booster
                user_doc_ref = db.collection('user_gem_counts').document(str(user.id))
                user_doc = user_doc_ref.get()
                acquisition_multiplier = 1.0 # Default multiplier
                if user_doc.exists:
                    inventory = user_doc.to_dict().get('inventory', {})
                    gem_booster_item = inventory.get("gem_booster")
                    if gem_booster_item and gem_booster_item.get("quantity", 0) > 0:
                            booster_effect = shop_items.get("gem_booster", {}).get("effect", {})
                            acquisition_multiplier = booster_effect.get("acquisition_multiplier", 1.0) # Default multiplier
                            logging.info(f"User {user.display_name} has gem booster. Applying multiplier: {acquisition_multiplier}")

                # Calculate final gem count after applying multiplier using ceiling formula
                gemcount = math.ceil(base_gem_count * acquisition_multiplier) 
                print(f"Final gem count after multiplier: {gemcount}")

                try:
                    # Record the claim in Firebase
                    gem_claims_ref.add({
                        'message_id': message_id,
                        'user_id': user.id,
                        'username': user.display_name,
                        'timestamp': firestore.SERVER_TIMESTAMP  # Use server timestamp
                    })

                    # Update user's gem count and ensure inventory is present
                    user_gem_counts_ref = db.collection('user_gem_counts').document(str(user.id))
                    user_gem_counts_ref.set({
                        'username': user.display_name,
                        'gem_count': firestore.Increment(gemcount)
                        # Inventory is not explicitly added here as it should be initialized on the first claim
                        # and merge=True will preserve existing inventory data
                    }, merge=True) # Use merge=True to avoid overwriting other fields if they exist

                    await channel.send(f"{user.display_name} has obtained {gemcount} gem(s)")
                    logging.info(f"ID:{user.id} claimed the gem")
                except Exception as e:
                    logging.error(f"Error recording gem claim in Firebase: {e}")
                    await channel.send("A server error occurred while trying to claim the gem.")
                else:
                    logging.info(f"Reaction on gem message {message_id} by {user.display_name} was outside the 30-second window based on the first claim.")

        else:
            logging.info(f"User {user.display_name} has already claimed gem {message_id}.")
client.run(my_secret)
