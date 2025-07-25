import logging
import sys
import time
from datetime import datetime, timezone
import random
import re
import asyncio
import math

# Configure logging at the very beginning, BEFORE any other modules that might use logging are imported.
# This is the most critical part of the fix.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("zhongybot.log"),
                        logging.StreamHandler(sys.stdout)
                    ])

import config  # Now that logging is configured, we can safely import our other modules.
import discord
from discord.ext import tasks
import google.generativeai as genai
from google.cloud.firestore_v1.base_query import FieldFilter

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
spawned_gem_message_id = 0
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from bot_comm import command_handlers

from helper import format_timestamp, calculate_time, get_start_of_week, get_end_of_week, split_response, capi_sentence, are_dates_in_same_week, format_month_day, convert, get_acquisition_multiplier
first_claim_timestamp = {}

try:
    cred = credentials.Certificate(config.FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.info("Firebase initialized successfully!")
except Exception as e:
    logging.error(f"Error initializing Firebase: {e}")
    db = None # Set db to None if initialization fails

client = discord.Client(intents=intents)
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
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

    channel = client.get_channel(config.GEM_SPAWN_CHANNEL_ID)
    if channel:
        try:
            is_sparkly = random.randint(1,5)
            if is_sparkly <= 1:
                message_content = f"Wow! {config.EMOJI_SPARKLE}{config.EMOJI_GEM}{config.EMOJI_SPARKLE} A shiny gem has appeared! Go claim it!"
                logging.info("Sparkly gem spawned!")
            else:
                message_content = f"A wild {config.EMOJI_GEM} has appeared! Go claim it!"
                print("Regular gem spawned.")
            # Add the gem emoji as a reaction to the message
            message = await channel.send(message_content)
            await message.add_reaction(config.EMOJI_GEM)
            global spawned_gem_message_id # Use global to modify the global variable
            spawned_gem_message_id = message.id
            first_claim_timestamp.clear()  # Clear old entries before adding a new one
            first_claim_timestamp[spawned_gem_message_id] = None
            logging.info(f"Gem spawn message sent with ID {spawned_gem_message_id}")
        except Exception as e:
            logging.error(f"Error sending gem spawn message: {e}")
    else:
        logging.warning(f"Channel with ID {config.GEM_SPAWN_CHANNEL_ID} not found.")

    # After spawning a gem, reschedule the loop with a new random interval
    seconds = random.randint(config.MIN_GEM_SPAWN_INTERVAL, config.MAX_GEM_SPAWN_INTERVAL)
    spawn_gem.change_interval(seconds=seconds)
    print(f"Next gem will spawn in {convert(seconds)}")


async def manual_gem_spawn():
    """Manually spawn a gem (triggered by admin command)."""
    channel = client.get_channel(config.GEM_SPAWN_CHANNEL_ID)
    if channel:
        try:
            is_sparkly = random.randint(1,5)
            if is_sparkly <= 1:
                message_content = f"Wow! {config.EMOJI_SPARKLE}{config.EMOJI_GEM}{config.EMOJI_SPARKLE} A shiny gem has appeared! Go claim it!"
                logging.info("Sparkly gem spawned!")
            else:
                message_content = f"A wild {config.EMOJI_GEM} has appeared! Go claim it!"
                print("Regular gem spawned.")
            # Add the gem emoji as a reaction to the message
            message = await channel.send(message_content)
            await message.add_reaction(config.EMOJI_GEM)
            global spawned_gem_message_id # Use global to modify the global variable
            spawned_gem_message_id = message.id
            first_claim_timestamp.clear()  # Clear old entries before adding a new one
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
    initial_delay = random.randint(config.MIN_GEM_SPAWN_INTERVAL, config.MAX_GEM_SPAWN_INTERVAL)
    logging.info(f"Waiting for initial gem spawn delay of {convert(initial_delay)}")
    await asyncio.sleep(initial_delay)

    # Set the first interval for the loop and start it
    # You might want to set a new random interval here for the first actual spawn
    spawn_gem.change_interval(seconds=random.randint(config.MIN_GEM_SPAWN_INTERVAL, config.MAX_GEM_SPAWN_INTERVAL))
    spawn_gem.start()
    logging.info("Gem spawn loop started.")

async def handle_command(message):
    """
    Processes a message that is identified as a command.
    Handles messages starting with '~' in servers and all messages in DMs.
    """
    # Handle DMs, which are always treated as potential commands
    if isinstance(message.channel, discord.DMChannel):
        if message.content.lower().startswith('~forward'):
            handler = command_handlers.get('forward')
            if handler:
                await handler(message, client=client)
        else:
            await message.channel.send("To forward a message to the server, please start your message with `~forward` followed by the message you want to send.")
        return

    # Handle server commands
    command = message.content[1:].lower().split()[0]
    handler = command_handlers.get(command)

    if handler:
        # This structure simplifies passing arguments to handlers
        kwargs = {}
        if command in ['ask']:
            kwargs = {'db': db, 'model': model, 'max_history_length': config.MAX_HISTORY_LENGTH, 'discord_max_length': config.DISCORD_MAX_LENGTH}
        elif command in ['deletehistory', 'checkgems', 'givegems', 'takegems', 'slots', 'buy', 'sf', 'use', 'inventory', 'daily', 'leaderboard']:
            kwargs = {'db': db}
        elif command in ['ursus', 'servertime', 'time']:
            kwargs = {'my_time': my_time}
        elif command in ['wipegems']:
            kwargs = {'db': db, 'target_role_id': config.MEMBER_ROLE_ID}
        
        await handler(message, **kwargs)

    # Special case for admin-only commands not in the main handler dict
    elif command == 'spawngem':
        if message.author.id in config.ADMIN_USER_IDS:
            await manual_gem_spawn()
        else:
            await message.channel.send("You are not authorized to use this command.")

async def handle_passive_responses(message):
    """
    Handles non-command-based responses, like memes or user-specific triggers.
    """
    # Dex free meme
    # This robust pattern checks for keywords like "dex" in proximity to words
    # implying low cost, and includes common "leetspeak" number substitutions.
    # This catches a wide variety of creative and verbose phrasings.
    dex_keywords = r"\b(d[e3]x|d[e3]xt[e3]r[i1]ty)\b"
    cost_keywords = r"\b(fr[e3][e3]|{emoji}|ch[e3][a4]p([e3]r)?|l[o0]w([e3]r)?\s*c[o0]st|c[o0]sts?\s*l[e3]ss|l[e3]ss\s*[e3]xp[e3]ns[i1]v[e3]|n[o0]\s*c[o0]st|[e3][a4]s(y|[i1][e3]r))\b".format(emoji=re.escape(config.EMOJI_FREE))
    dex_free_pattern = r"({dex}{filler}{cost}|{cost}{filler}{dex})".format(dex=dex_keywords, cost=cost_keywords, filler=r"[\s\w,'.?!]{1,40}")
    if re.search(dex_free_pattern, message.content.lower()):
        response = 'No it isn\'t'
        await message.reply(response)
        return

    # User-specific triggers
    if message.author.id == config.UBER_USER_ID:
        roll = random.randint(1, 100)
        logging.info(f"Ub3r rolled {roll}")
        if roll <= 7:
            text = message.content.lower()
            response = capi_sentence(text)
            await message.reply(response, mention_author=False)
            return
    elif message.author.id == config.HARRI_USER_ID:
        roll = random.randint(1, 1000)
        logging.info(f"Harri rolled {roll}")
        if roll <= 8:
            roll = random.randint(1, 4)
            if roll <= 3:
                text = message.content.lower()
                response = capi_sentence(text)
                await message.reply(response, mention_author=False)
            else:  # 25% chance for the custom message using Gemini
                if model:
                    try:
                        gemini_prompt = "In a way that shuts him up remind the user named Harri that he has a 70 boss damage familiar card, which is extremely rare. You are the one addressing him directly and make it short"
                        response = model.generate_content([gemini_prompt])
                        response_chunks = split_response(response.text, config.DISCORD_MAX_LENGTH)
                        for chunk in response_chunks:
                            await message.channel.send(chunk)
                    except Exception as e:
                        logging.error(f"An error occurred during custom Gemini interaction: {e}")
                        await message.channel.send("Sorry, I couldn't generate a response for you at this time.")
            return

@client.event
async def on_message(message):
    """
    Event triggered when a message is received. Processes the message to handle various commands.

    Args:
        message (discord.Message): The message object received from the channel.
    """
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Check if the message is a command and route it to the command handler
    if message.content.startswith('~') or isinstance(message.channel, discord.DMChannel):
        await handle_command(message)
    # Otherwise, check for passive responses
    else:
        await handle_passive_responses(message)
 
@client.event
async def _delete_message_after_delay(message: discord.Message, delay: int, db):
    """
    Waits for a specified delay, deletes the message, and cleans up corresponding
    database entries for gem claims.
    """
    await asyncio.sleep(delay)
    message_id = message.id
    try:
        await message.delete()
        logging.info(f"Deleted gem spawn message {message_id} after claim window closed.")
    except discord.NotFound:
        # If message is already gone, we should still try to clean up the DB
        logging.warning(f"Attempted to delete gem message {message_id}, but it was already deleted.")
    except discord.Forbidden:
        logging.error(f"Lacking permissions to delete gem message {message_id}. Cannot clean up DB entries.")
        return # Can't do anything further
    except Exception as e:
        logging.error(f"An unexpected error occurred while deleting message {message_id}: {e}")

    # Clean up the database entries for this message_id using a batch delete
    if db:
        try:
            claims_ref = db.collection('gem_claims')
            docs_to_delete = claims_ref.where(filter=FieldFilter('message_id', '==', message_id)).stream()

            batch = db.batch()
            deleted_count = 0
            for doc in docs_to_delete:
                batch.delete(doc.reference)
                deleted_count += 1
            
            if deleted_count > 0:
                batch.commit()
                logging.info(f"Cleaned up {deleted_count} claim(s) from database for message ID {message_id}.")
        except Exception as e:
            logging.error(f"An error occurred while cleaning up gem claims for message ID {message_id}: {e}")

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
    if str(reaction.emoji) == config.EMOJI_GEM and reaction.message.author == client.user and reaction.message.id == spawned_gem_message_id:
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

            # Get the timestamp of the first claim.
            first_claim_time = first_claim_timestamp.get(message_id)

            # Helper function to process the claim, avoiding code duplication.
            async def process_gem_claim(user, is_sparkly):
                # Determine base gem count
                if is_sparkly:
                    base_gem_count = random.randint(6, 10)
                    logging.info(f"Sparkly gem claimed! User {user.display_name} gets {base_gem_count} base gems.")
                else:
                    base_gem_count = random.choices(gem_counts, weights=weights, k=1)[0]
                    logging.info(f"Regular gem claimed! User {user.display_name} gets {base_gem_count} base gems.")

                # Check for booster using the helper function
                user_doc_ref = db.collection('user_gem_counts').document(str(user.id))
                user_doc = user_doc_ref.get()
                inventory = user_doc.to_dict().get('inventory', {}) if user_doc.exists else {}
                acquisition_multiplier = get_acquisition_multiplier(inventory)
                if acquisition_multiplier > 1.0:
                    logging.info(f"User {user.display_name} has gem booster. Applying multiplier: {acquisition_multiplier}")

                # Calculate final gem count
                gemcount = math.ceil(base_gem_count * acquisition_multiplier)
                logging.info(f"Final gem count after multiplier: {gemcount}")

                try:
                    # Record the claim in Firebase
                    gem_claims_ref.add({
                        'message_id': message_id,
                        'user_id': user.id,
                        'username': user.display_name,
                        'timestamp': firestore.SERVER_TIMESTAMP
                    })

                    # Update user's gem count and ensure inventory is not overwritten
                    update_data = {
                        'username': user.display_name,
                        'gem_count': firestore.Increment(gemcount)
                    }
                    if not user_doc.exists or 'inventory' not in user_doc.to_dict():
                        update_data['inventory'] = {}  # Initialize inventory only if missing
                    user_doc_ref.set(update_data, merge=True)

                    await channel.send(f"{user.display_name} has obtained {gemcount} gem(s)")
                    logging.info(f"ID:{user.id} claimed the gem")
                except Exception as e:
                    logging.error(f"Error recording gem claim in Firebase for {user.display_name}: {e}")
                    await channel.send("A server error occurred while trying to claim the gem.")

            # Determine if it was a sparkly gem based on the message content
            is_sparkly_claim = f"{config.EMOJI_SPARKLE}{config.EMOJI_GEM}{config.EMOJI_SPARKLE}" in reaction.message.content

            if first_claim_time is None:  # This is the first claim.
                first_claim_timestamp[message_id] = current_time
                logging.info(f"First claim on gem message {message_id} at {current_time}")
                await process_gem_claim(user, is_sparkly_claim)
                # Schedule the message for deletion after the 30-second window
                client.loop.create_task(_delete_message_after_delay(reaction.message, 30, db))

            elif (current_time - first_claim_time).total_seconds() <= 30: # Not the first claim, but within the 30-second window.
                await process_gem_claim(user, is_sparkly_claim)

            else:
                logging.info(f"Reaction on gem message {message_id} by {user.display_name} was outside the 30-second window.")

        else:
            logging.info(f"User {user.display_name} has already claimed gem {message_id}.")
client.run(config.DISCORD_TOKEN)
