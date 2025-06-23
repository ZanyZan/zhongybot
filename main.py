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
from dotenv import load_dotenv
from google.cloud.firestore_v1.base_query import FieldFilter
load_dotenv()
free_emoji_unicode = '\U0001F193'
gem_emoji_unicode = '\U0001F48E'
discord_max_length = 2000
max_history_length = 20
min_gem_spawn_interval = 21600 #6 hours
max_gem_spawn_interval = 43200 #12 hours
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
gem_spawn_channel_id = 808341519714484246
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from bot_comm import command_handlers

# Import helper functions from helpers.py (assuming you still want these)
from helper import format_timestamp, calculate_time, get_start_of_week, get_end_of_week, split_response, capi_sentence, are_dates_in_same_week, format_month_day


# Replace 'path/to/your/serviceAccountKey.json' with the actual path
try:
    cred = credentials.Certificate('/home/zanypi/env/gen-lang-client-0697881417-firebase-adminsdk-fbsvc-c6eb0253de.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully!")
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    db = None # Set db to None if initialization fails

client = discord.Client(intents=intents)
#discord bot token is saved as a secrete token in replit.
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
            # Send a message indicating the gem has spawned
            message = await channel.send(f"A wild {gem_emoji_unicode} has appeared! Go claim it!")
            # Add the gem emoji as a reaction to the message
            await message.add_reaction(gem_emoji_unicode)
            print(f"Gem spawn message sent to channel {gem_spawn_channel_id}")
        except Exception as e:
            print(f"Error sending gem spawn message: {e}")
    else:
        print(f"Channel with ID {gem_spawn_channel_id} not found.")

    # After spawning a gem, reschedule the loop with a new random interval
    seconds=random.randint(min_gem_spawn_interval, max_gem_spawn_interval)
    spawn_gem.change_interval(seconds=seconds)
    print(f"Next gem will spawn in {convert(seconds)}")
            
@client.event
async def on_ready():
  """
    Event triggered when the bot is ready. Starts the time update loop.
  """
  update_my_time.start()
  client.loop.create_task(start_gem_spawning())  # Start the gem spawn task

  print("logged in as {0.user}".format(client))


async def start_gem_spawning():
    """
    Handles the initial random delay before starting the gem spawn loop.
    """
    await client.wait_until_ready()
    # Calculate a random initial delay (using your min/max intervals)
    initial_delay = random.randint(min_gem_spawn_interval, max_gem_spawn_interval)
    print(f"Waiting for initial gem spawn delay of {convert(initial_delay)}")
    await asyncio.sleep(initial_delay)

    # Set the first interval for the loop and start it
    # You might want to set a new random interval here for the first actual spawn
    spawn_gem.change_interval(seconds=random.randint(min_gem_spawn_interval, max_gem_spawn_interval))
    spawn_gem.start()
    print("Gem spawn loop started.")

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    return "%d:%02d:%02d" % (hour, minutes, seconds)    


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
    response = f'No it isn\'t'
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
          elif command in ['deletehistory', 'checkgems', 'givegems', 'takegems']:
              await handler(message, db=db)
          elif command in ['ursus', 'servertime', 'time']:
              await handler(message, my_time=my_time) # Pass my_time here
          else: # For commands that don't need extra arguments
              await handler(message)

                
  if message.content.lower() == 'aran succ' and (875235978971861002 in list(
    role.id for role in message.author.roles)):
    response = f'Hey {message.author.display_name}, heard you play Aran. You have my condolences. You should gather everyone and go Hunter\'s Prey Changseop for this travesty'
    new = await message.reply(response)
    await new.add_reaction('<:FeelsAranMan:852726957091323934>')

  if message.author.id == 257995877367414785:
      roll = random.randint(1, 100)
      print("Ub3r rolled", roll)
      if roll <= 7:
          text = message.content.lower()
          response = capi_sentence(text) # Using capi_sentence from helpers
          await message.reply(response, mention_author=False)
  elif message.author.id == 249678251226562561:
      roll = random.randint(1,100)
      print("Harri rolled", roll)
      if roll <= 1:
          roll = random.randint(1,4)
          if roll <= 3:
              text = message.content.lower()
              response = capi_sentence(text) # Using capi_sentence from helpers
              await message.reply(response, mention_author=False)
          else: # 25% chance for the custom message using Gemini
              if model:  # Ensure the Gemini model is initialized
                  try:
                      # Define your custom Gemini prompt here
                      gemini_prompt = f"In a way that shuts him up remind the user named Harri that he has a 70 boss damage familiar card, which is extremely rare. You are the one addressing him directly and make it short"

                      response = model.generate_content([gemini_prompt])
                      # Split the response if it's too long for Discord
                      response_chunks = split_response(response.text, discord_max_length)
                      for chunk in response_chunks:
                          await message.channel.send(chunk)

                  except Exception as e:
                      print(f"An error occurred during custom Gemini interaction: {e}")
                      await message.channel.send("Sorry, I couldn't generate a response for you at this time.")
              else:
                  await message.channel.send("Gemini model is not initialized. Cannot generate a custom response.")
  if re.search(r"\bread\b", message.content):
    roll = random.randint(1,5)
    print("Read was typed. Rolled:", roll)
    if roll == 1:
      await message.channel.send("Debris can't read <:DebrisCantRead:1157773828173332550>")
                      
@client.event
async def on_reaction_add(reaction, user):
    """
    Handles reactions added to messages. Checks for reactions on gem spawn messages
    and records claims in Firebase.
    """
    # Ignore reactions from the bot itself or if Firebase is not initialized
    gem_counts = [1, 2, 3, 4, 5]
    weights = [0.5, 0.25, 0.15, 0.07, 0.03]
    if user == client.user or db is None:
        return
    # Check if the reaction is the gem emoji
    if str(reaction.emoji) == gem_emoji_unicode:
        # Check if the message was sent by the bot
        if reaction.message.author == client.user:
            # Check if the gem has already been claimed
            gem_claims_ref = db.collection('gem_claims')
            query = gem_claims_ref.where(filter=FieldFilter('message_id', '==', reaction.message.id)).limit(1)
            docs = query.stream()

            claimed = False
            for doc in docs:
                claimed = True
                break  # Gem has already been claimed

            if not claimed:
                # Check if the reaction count is 2 (bot's reaction + first user's reaction)
                # This is a simple way to ensure it's the first claim attempt
                # More robust logic might involve checking timestamps
                if reaction.count == 2:
                    channel = reaction.message.channel
                    gemcount = random.choices(gem_counts, weights=weights, k=1)[0]
                    try:
                        # Record the claim in Firebase
                        gem_claims_ref.add({
                            'message_id': reaction.message.id,
                            'user_id': user.id,
                            'username': user.display_name,
                            'timestamp': firestore.SERVER_TIMESTAMP  # Use server timestamp
                        })
                        
                                                # Update user's gem count
                        user_gem_counts_ref = db.collection('user_gem_counts').document(str(user.id))
                        user_gem_counts_ref.set({
                            'username': user.display_name,
                            'gem_count': firestore.Increment(gemcount)
                        }, merge=True) # Use merge=True to avoid overwriting other fields if they exist
                        
                        await channel.send(f"{user.display_name} has obtained {gemcount} gem(s)")
                        print(f"ID:{user.id} claimed the gem")
                    except Exception as e:
                        print(f"Error recording gem claim in Firebase: {e}")
                        await channel.send("An error occurred while trying to claim the gem.")
            else:
                print(f"This gem {reaction.message.id} has already claimed.")
client.run(my_secret)
