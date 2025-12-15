import logging
import sys
# Configure logging at the very beginning, BEFORE any other modules that might use logging are imported.
# This is the most critical part of the fix.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("zhongybot.log"),
                        logging.StreamHandler(sys.stdout)
                    ])

import time
from datetime import datetime, timezone
import random
import re
import asyncio
import math
import os
import config  # Now that logging is configured, we can safely import our other modules.
import discord
from discord.ext import tasks
import google.generativeai as genai
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core import exceptions as google_exceptions
from firebase_admin.firestore import SERVER_TIMESTAMP, Increment
from firebase_admin import firestore
import db_manager
import bot_comm 

from helper import format_timestamp, calculate_time, get_start_of_week, get_end_of_week, split_response, capi_sentence, are_dates_in_same_week, format_month_day, convert, get_booster_multiplier, get_gem_charm_holders

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)

spawned_gem_message_id = 0
first_claim_timestamp = {}

db_manager.initialize_db()

try:
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
    logging.info("Gemini AI model initialized successfully.")
except Exception as e:
    model = None
    logging.critical(f"Failed to initialize Gemini AI model: {e}")

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
            
            # --- Get users with Gem Finder's Charm ---
            db = db_manager.get_db()
            charm_holders = get_gem_charm_holders(db)
            
            if is_sparkly <= 1:
                message_content = f"Wow! {config.EMOJI_SPARKLE}{config.EMOJI_GEM}{config.EMOJI_SPARKLE} A shiny gem has appeared! Go claim it!"
                logging.info("Sparkly gem spawned!")
            else:
                message_content = f"A wild {config.EMOJI_GEM} has appeared! Go claim it!"
                print("Regular gem spawned.")

            # --- Add pings if there are charm holders ---
            if charm_holders:
                ping_message = " ".join(charm_holders)
                message_content += f"\n\nYour charm is humming! {ping_message}"

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

            # --- Get users with Gem Finder's Charm ---
            db = db_manager.get_db()
            charm_holders = get_gem_charm_holders(db)

            if is_sparkly <= 1:
                message_content = f"Wow! {config.EMOJI_SPARKLE}{config.EMOJI_GEM}{config.EMOJI_SPARKLE} A shiny gem has appeared! Go claim it!"
                logging.info("Sparkly gem spawned!")
            else:
                message_content = f"A wild {config.EMOJI_GEM} has appeared! Go claim it!"
                print("Regular gem spawned.")

            # --- Add pings if there are charm holders ---
            if charm_holders:
                ping_message = " ".join(charm_holders)
                message_content += f"\n\nYour charm is humming! {ping_message}"

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

# --- Command Handlers Dictionary ---
# Note: The command handlers from bot_comm.py have been updated to not require 'db' as a parameter.
# They now get the database connection from the db_manager themselves.
command_handlers = {
    "checkgems": bot_comm.handle_checkgems,
    "gems": bot_comm.handle_checkgems,
    "ask": lambda msg: bot_comm.handle_ask(msg, model, config.MAX_HISTORY_LENGTH, config.DISCORD_MAX_LENGTH),
    "weaponf": bot_comm.handle_weaponf,
    "esfera": bot_comm.handle_esfera,
    "deletehistory": bot_comm.handle_deletehistory,
    "givegems": bot_comm.handle_givegems,
    "takegems": bot_comm.handle_takegems,
    "mine": bot_comm.handle_mine,
    "upgrade": bot_comm.handle_upgrade,
    "slots": bot_comm.handle_slots,
    "wipegems": lambda msg: bot_comm.handle_wipegems(msg, config.MEMBER_ROLE_ID),
    "buy": bot_comm.handle_buy,
    "inventory": bot_comm.handle_inventory,
    "inv": bot_comm.handle_inventory,
    "use": bot_comm.handle_use,
    "daily": bot_comm.handle_daily,
    "leaderboard": bot_comm.handle_leaderboard,
    "lb": bot_comm.handle_leaderboard,
    "starforce": bot_comm.handle_starforce,
    "sf": bot_comm.handle_starforce,
    "payoutpoll": lambda msg: bot_comm.handle_payoutpoll(msg, client),
    "help": bot_comm.handle_help,
    "shop": bot_comm.handle_shop,
    "8ball": bot_comm.handle_8ball,
    "forward": lambda msg: bot_comm.handle_forward(msg, client),
    "ursus": lambda msg: bot_comm.handle_ursus(msg, my_time),
    "servertime": lambda msg: bot_comm.handle_servertime(msg, my_time),
    "time": lambda msg: bot_comm.handle_time(msg, my_time),
    "roll": bot_comm.handle_roll,
    "togglecharm": bot_comm.handle_togglecharm,
}
command_handlers.update(bot_comm.command_handlers)

@client.event
async def on_ready():
  """
    Event triggered when the bot is ready. Starts the time update loop.
    Event triggered when the bot is ready. Starts background tasks.
  """
  update_my_time.start()
  client.loop.create_task(start_gem_spawning())  # Start the gem spawn task
  process_automine.start() # Start the automine task
  logging.info(f"Logged in as {client.user}")


@tasks.loop(minutes=5)
async def process_automine():
    """
    Periodically checks for users with an autominer whose mining cooldown
    has expired and automatically mines for them.
    """
    await client.wait_until_ready()
    db = db_manager.get_db()
    if db is None:
        logging.warning("Automine: Database not available, skipping run.")
        return

    logging.info("Starting automine process...")
    # Query for all users that have an autominer.
    users_ref = db.collection('user_profile')
    query = users_ref.where(filter=FieldFilter('inventory.autominer', '!=', None))

    try:
        docs = query.stream()
        processed_count = 0
        current_time_utc = datetime.now(timezone.utc)
        cooldown_seconds = config.MINE_COOLDOWN_SECONDS

        for doc in docs:
            # Use a transaction for each user to ensure data consistency
            @firestore.transactional
            def automine_transaction(transaction, user_ref):
                snapshot = user_ref.get(transaction=transaction)
                if not snapshot.exists:
                    return None

                user_data = snapshot.to_dict()
                inventory = user_data.get('inventory', {})
                
                # Double-check for autominer and pickaxe
                if 'autominer' not in inventory or 'pickaxe' not in inventory:
                    return None

                last_mine_time = user_data.get('last_mine_time')
                if last_mine_time:
                    time_since_last_mine = current_time_utc - last_mine_time
                    if time_since_last_mine.total_seconds() < cooldown_seconds:
                        return None # Still on cooldown

                # --- Replicate mining logic from handle_mine ---
                pickaxe_data = inventory.get('pickaxe', {})
                pickaxe_level = pickaxe_data.get('level', 1)
                min_gems, max_gems = bot_comm.PICKAXE_LEVEL_REWARDS.get(pickaxe_level, bot_comm.PICKAXE_LEVEL_REWARDS[1])
                gems_found = random.randint(min_gems, max_gems)

                total_multiplier = 1.0
                acquisition_multiplier = get_booster_multiplier(inventory)
                total_multiplier *= acquisition_multiplier
                if 'unicorn' in inventory:
                    unicorn_info = inventory.get('unicorn', {})
                    unicorn_multiplier = unicorn_info.get('effect', {}).get('mining_multiplier', 1.0)
                    total_multiplier *= unicorn_multiplier
                
                final_gems_found = math.ceil(gems_found * total_multiplier)

                transaction.update(user_ref, {
                    'gem_count': Increment(final_gems_found),
                    'last_mine_time': SERVER_TIMESTAMP
                })
                return final_gems_found

            # Execute the transaction for the user
            gems_mined = automine_transaction(db.transaction(), doc.reference)
            if gems_mined is not None:
                processed_count += 1
                logging.info(f"Automined {gems_mined} gems for user {doc.id}.")

        if processed_count > 0:
            logging.info(f"Automine process complete. Mined for {processed_count} users.")
        else:
            logging.info("Automine process complete. No users were ready for mining.")

    except Exception as e:
        logging.error(f"An unexpected error occurred during automine process: {e}")


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
    if re.search(r"\b(read|reading)\b", message.content.lower()):
        roll = random.randint(1, 5)
        logging.info(f"Read was typed, rolled {roll}")
        if roll == 1:
            response = "Debris can't read <:DebrisCantRead:1157773828173332550>"
            await message.channel.send(response)
        return
    # Harri special responses
    if message.author.id == config.HARRI_USER_ID:
        roll = random.randint(1, 1000)
        logging.info(f"Harri rolled {roll}")
        if roll <= 3:  # 0.3% chance for a special response
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
        message (discord.Message): The message object received.
    """
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Handle DMs
    if isinstance(message.channel, discord.DMChannel):
        if message.content.lower().startswith('~forward'):
            await command_handlers['forward'](message)
        else:
            await message.channel.send("To forward a message to the server, please start your message with `~forward` followed by the message you want to send.")
        return

    # Handle server messages
    if not message.content.startswith(config.PREFIX):
        await handle_passive_responses(message)
        return

    command_body = message.content[len(config.PREFIX):]
    parts = command_body.split()
    if not parts:
        return
    command = parts[0].lower()

    # Special admin command
    if command == 'spawngem':
        if message.author.id in config.ADMIN_USER_IDS:
            await manual_gem_spawn()
        else:
            await message.channel.send("You are not authorized to use this command.")
        return

    # General command handling
    handler = command_handlers.get(command)
    if handler:
        try:
            await handler(message)
        except Exception as e:
            logging.exception(f"An error occurred while executing command '{command}'")
            await message.channel.send("An unexpected error occurred. Please try again later.")

async def _delete_message_after_delay(message: discord.Message, delay: int):
    """
    Waits for a specified delay, deletes the message, and cleans up corresponding
    database entries for gem claims.
    """
    db = db_manager.get_db()
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
        except google_exceptions.Unavailable:
            # Trigger a reconnect on persistent failure
            db_manager.handle_db_error(e, f"during gem claim cleanup for message ID {message_id}")
        except Exception as e:
            logging.error(f"An error occurred while cleaning up gem claims for message ID {message_id}: {e}")

@client.event
async def on_reaction_add(reaction, user):
    """
    Handles reactions added to messages. Checks for reactions on gem spawn messages
    and records claims in Firebase.
    """
    db = db_manager.get_db()
    gem_counts = [6, 7, 8, 9, 10] # Increased base gems by +2
    weights = [0.5, 0.25, 0.15, 0.07, 0.03] # Weights remain the same for the new values

    if user == client.user:
        return
    elif db is None:
        logging.warning("Database not available for on_reaction_add.")
        return

    # Check if the reaction is the gem emoji and on the current spawned gem message
    if str(reaction.emoji) == config.EMOJI_GEM and reaction.message.author == client.user and reaction.message.id == spawned_gem_message_id:
        message_id = reaction.message.id
        channel = reaction.message.channel

        # Check if the user has already claimed this specific gem
        gem_claims_ref = db.collection('gem_claims')
        query = gem_claims_ref.where(filter=FieldFilter('message_id', '==', message_id)).where(filter=FieldFilter('user_id', '==', user.id)).limit(1)
        
        # any() is a more efficient way to check for existence
        claimed_by_user = any(query.stream())

        if not claimed_by_user:
            current_time = datetime.now(timezone.utc)

            # Get the timestamp of the first claim.
            first_claim_time = first_claim_timestamp.get(message_id)

            # Helper function to process the claim, avoiding code duplication.
            async def process_gem_claim(user, is_sparkly_claim):
                # Determine base gem count
                if is_sparkly_claim:
                    base_gem_count = random.randint(12, 20)
                    logging.info(f"Sparkly gem claimed! User {user.display_name} gets {base_gem_count} base gems.")
                else:
                    base_gem_count = random.choices(gem_counts, weights=weights, k=1)[0]
                    logging.info(f"Regular gem claimed! User {user.display_name} gets {base_gem_count} base gems.")

                # Check for booster using the helper function
                user_doc_ref = db.collection('user_profile').document(str(user.id))
                user_doc = user_doc_ref.get()
                inventory = user_doc.to_dict().get('inventory', {}) if user_doc.exists else {}
                acquisition_multiplier = get_booster_multiplier(inventory)
                if acquisition_multiplier > 1.0:
                    logging.info(f"User {user.display_name} has gem booster. Applying multiplier: {acquisition_multiplier}")

                # Calculate final gem count
                gemcount = math.ceil(base_gem_count * acquisition_multiplier)
                logging.info(f"Final gem count after multiplier: {gemcount}")
                
                # Record the claim in Firebase
                gem_claims_ref.add({
                    'message_id': message_id,
                    'user_id': user.id,
                    'username': user.display_name,
                    'timestamp': SERVER_TIMESTAMP
                })

                # Update user's gem count and ensure inventory is not overwritten
                update_data = {
                    'username': user.display_name,
                    'gem_count': Increment(gemcount)
                }
                if not user_doc.exists or 'inventory' not in user_doc.to_dict():
                    update_data['inventory'] = {}  # Initialize inventory only if missing
                user_doc_ref.set(update_data, merge=True)

                if acquisition_multiplier > 1.0:
                    bonus_gems = gemcount - base_gem_count
                    await channel.send(f"{user.display_name} has obtained {gemcount} gem(s) ({base_gem_count} base + {bonus_gems} bonus)!")
                else:
                    await channel.send(f"{user.display_name} has obtained {gemcount} gem(s)!")
                logging.info(f"ID:{user.id} claimed the gem")

            # Determine if it was a sparkly gem based on the message content
            is_sparkly_claim = f"{config.EMOJI_SPARKLE}{config.EMOJI_GEM}{config.EMOJI_SPARKLE}" in reaction.message.content

            if first_claim_time is None:  # This is the first claim.
                first_claim_timestamp[message_id] = current_time
                logging.info(f"First claim on gem message {message_id} at {current_time}")
                try:
                    await process_gem_claim(user, is_sparkly_claim)
                except (google_exceptions.Unavailable, google_exceptions.DeadlineExceeded) as e:
                    logging.error(f"DB error on first gem claim for {user.display_name}: {e}")
                    await channel.send(f"Sorry {user.mention}, there was a database connection issue. Please try reacting again!")
                    # Reset first claim time to allow another user to be "first"
                    first_claim_timestamp[message_id] = None 
                    return # Exit to prevent scheduling deletion
                client.loop.create_task(_delete_message_after_delay(reaction.message, 45))  # Schedule deletion after 45 seconds

            elif (current_time - first_claim_time).total_seconds() <= 45: # Not the first claim, but within the 45-second window.
                try:
                    await process_gem_claim(user, is_sparkly_claim)
                except (google_exceptions.Unavailable, google_exceptions.DeadlineExceeded) as e:
                    logging.error(f"DB error on subsequent gem claim for {user.display_name}: {e}")
                    # Don't need to send a message here as the user can just try again.
                    # The error is logged for debugging.
                    pass

            else:
                logging.info(f"Reaction on gem message {message_id} by {user.display_name} was outside the 45-second window.")

        else:
            logging.info(f"User {user.display_name} has already claimed gem {message_id}.")

client.run(config.DISCORD_TOKEN)
