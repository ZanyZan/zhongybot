import discord
import os
from discord.ext import tasks
import time
from datetime import datetime, timedelta, timezone
import pytz
import operator
import random
import weapons as wp
import re
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
free_emoji_unicode = '\U0001F193'
discord_max_length = 2000
max_history_length = 20
banana_claim_time_limit = 30
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


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


@client.event
async def on_ready():
  """
    Event triggered when the bot is ready. Starts the time update loop.
  """
  #update_clocks.start()
  update_my_time.start()
  print("logged in as {0.user}".format(client))

# Define functions for each command
async def handle_ursus(message):
    current_dt = datetime.fromtimestamp(my_time)
    day = current_dt.day
    month = current_dt.month
    year = current_dt.year

    # Define Ursus times for the current day
    ursus_start1_epoch_current_day = int(datetime(year, month, day, 20, 0, 0).timestamp())
    next_day_dt = current_dt + timedelta(days=1)
    ursus_end1_epoch_next_day = int(datetime(next_day_dt.year, next_day_dt.month, next_day_dt.day, 0, 0, 0).timestamp())
    ursus_start2_epoch_current_day = int(datetime(year, month, day, 13, 0, 0).timestamp())
    ursus_end2_epoch_current_day = int(datetime(year, month, day, 17, 0, 0).timestamp())

    # Define the start of the first Ursus run on the next day
    next_day_ursus_start1_epoch = int(datetime(next_day_dt.year, next_day_dt.month, next_day_dt.day, 20, 0, 0).timestamp())

    response = "" # Initialize response string
    time_difference = 0 # Initialize time difference

    # Check if currently in the first Ursus run (spans across midnight)
    if (ursus_start1_epoch_current_day < my_time < ursus_end1_epoch_next_day):
        time_difference = ursus_end1_epoch_next_day - my_time
        response = 'Ursus 2x meso is currently active, it will end in ' + str(timedelta(seconds=time_difference))

    # Check if currently in the second Ursus run (within the current day)
    elif (ursus_start2_epoch_current_day < my_time < ursus_end2_epoch_current_day):
        time_difference = ursus_end2_epoch_current_day - my_time
        response = 'Ursus 2x meso is currently active, it will end in ' + str(timedelta(seconds=time_difference))

    # Check if between the end of the second run (current day) and the start of the first run (current day)
    elif (ursus_end2_epoch_current_day < my_time < ursus_start1_epoch_current_day):
        time_difference = ursus_start1_epoch_current_day - my_time
        response = 'Ursus 2x meso is not active, it will start in ' + str(timedelta(seconds=time_difference))

    # Check if before the start of the second run (current day)
    elif (my_time < ursus_start2_epoch_current_day):
         time_difference = ursus_start2_epoch_current_day - my_time
         response = 'Ursus 2x meso is not active, it will start in ' + str(timedelta(seconds=time_difference))

    # If none of the above, this case shouldn't ideally be reached with the current Ursus times, but as a fallback:
    else:
        response = "Unable to determine next Ursus time."

    # Construct the full response including all Ursus times
    full_response = (
        'Ursus 2x meso is active between <t:' + str(ursus_start1_epoch_current_day) + ':t> and <t:' + str(ursus_end1_epoch_next_day) + ':t> '
        'and between <t:' + str(ursus_start2_epoch_current_day) + ':t> and <t:' + str(ursus_end2_epoch_current_day) + ':t>\n' + response
    )

    embed = discord.Embed(description=full_response, colour=discord.Colour.purple())
    await message.channel.send(embed=embed)

async def handle_servertime(message):
    UTC_time = datetime.fromtimestamp(my_time, timezone.utc).strftime('%H:%M %p')
    response = 'The server time right now is: ' + UTC_time + ' \n > Maplestory GMS uses UTC as default server time'
    embed = discord.Embed(description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)


async def handle_time(message):
    splitted_command = message.content.split('time')
    arguments = splitted_command[1][1:]
    if not splitted_command[1]:
        response = 'Your time right now is: <t:' + str(my_time) + ':t>'
        embed = discord.Embed(description=response,
                              colour=discord.Colour.purple())
        await message.channel.send(embed=embed)
    elif (arguments[0] == '+' or arguments[0] == '-'):
        day = datetime.fromtimestamp(my_time).day
        month = datetime.fromtimestamp(my_time).month
        year = datetime.fromtimestamp(my_time).year
        server_reset_time = int(datetime(year, month, day, 19, 0, 0).timestamp())
        operator = arguments[0]
        addends = arguments[1:]
        new_time = int(calculate_time(server_reset_time, operator, float(addends) * 3600))
        response = arguments + ' is: <t:' + str(new_time) + ':t>'
        embed = discord.Embed(title="Time Converter",
                              description=response,
                              colour=discord.Colour.purple())
        await message.channel.send(embed=embed)
    else:
        response = 'Try again noob..'
        embed = discord.Embed(title="Time Converter",
                              description=response,
                              colour=discord.Colour.purple())
        await message.channel.send(embed=embed)


async def handle_esfera(message):
    embed = discord.Embed(title='Esfera PQ', colour=discord.Colour.purple())
    embed.set_image(
        url=
        "https://media.discordapp.net/attachments/991018662133657741/995399795306938448/7cfl8wyemec81.png"
    )
    await message.channel.send(embed=embed)

async def handle_help(message):
    response = 'Command List.\n- Use `~ursus` : to look for ursus time!.\n- Use `~servertime` : to check server\'s time (or check the clock channel!).\n- Use `~time` : if by some divine intervention you don\'t remember your own time LOL\n- You can also use `~time (+/-)(#Number)` : to check your local time in relation to server\'s reset time. eg: `~time +3` `~time -3`.\n- Use `~esfera` : if you are lazy and don\'t want to check the guides for the esfera PQ picture.\n- Use `~8ball` : to ask any yes/no questions.\n- Use `~roll` : to roll a d20 die.\n- Use `~roll d#`: to roll a d# die. eg: `~roll d40`, rolls a d40 die, etc.\n- Use `~weaponf class/weapon weapontype`: will give you the attack flame for your specified class/weapon (weapontype being Abso/Arcane/Genesis) **Except for Zero. Was lazy to implement Zero. \n- Use `~ask` to ask the bot something and get an answer. \n- Use `~deletehistory` to delete your conversation history with the bot. \n\nCommands are not case sensitive, you can do `~UrSuS` if you want.\n \nAny issues or if you have any ideas for new commands please, let Zany know!'
    embed = discord.Embed(title="Zhongy Helps",
                          description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)


async def handle_roll(message):
    split_command = command.split('roll')
    arguments = split_command[1][1:]
    if not split_command[1]:
        dice_num = 20
        rolled_dice = random.randint(1, dice_num)
    elif split_command[1]:
        dice_num = int(arguments[1:])
        rolled_dice = random.randint(1, dice_num)
    response = f'{message.author.display_name} rolled a d{dice_num} and got {rolled_dice} '
    embed = discord.Embed(description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)


async def handle_8ball(message):
    split_command = command.split('8ball')
    question = split_command[1]
    answer_dict = {
        0: "It is certain",
        1: "It is decidedly so",
        2: "Without a doubt",
        3: "Yes - definitely",
        4: "You may rely on it",
        5: "As I see it, yes",
        6: "Most likely",
        7: "Outlook good",
        8: "Yes",
        9: "Signs point to yes",
        10: "Reply hazy, try again",
        11: "Ask again later",
        12: "Better not tell you now",
        13: "Cannot predict now",
        14: "Concentrate and ask again",
        15: "Don't count on it",
        16: "My reply is no",
        17: "My sources say no",
        18: "Outlook not so good",
        19: "Very doubtful",
        20: "Ask Greg about it",
    }
    roll = random.randint(0, 20)
    answer = answer_dict[roll]
    title = f'You asked: "{question}"'
    response = f'Magic 8 ball says: {answer}'
    embed = discord.Embed(title=title,
                          description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)

async def handle_weaponf(message):
    weapon_class, weapon_tier = message.content.split()[1:]
    weapon_tier = weapon_tier.title()
    if weapon_class in wp.weapon_stats:
        attack = wp.weapon_stats[weapon_class][weapon_tier]
    elif weapon_class in wp.weapon_alias:
        attack = wp.weapon_alias[weapon_class][weapon_tier]

    response = wp.weapon_calc(attack, weapon_tier)

    title = f'{weapon_tier} flame tiers for {weapon_class}'
    embed = discord.Embed(title=title,
                          description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)


async def handle_ask(message):
    if message.channel.id == 971245167254331422:
        if db is None:
            await message.channel.send("Firebase is not initialized. Cannot use the ~ask command.")
            return

        prompt = message.content[len('ask '):].strip()
        if not prompt:
            await message.channel.send("Please provide a prompt after ~ask.")
            return

        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        doc_ref = db.collection('conversation_history').document(channel_id).collection('users').document(user_id)

        doc = doc_ref.get()
        if doc.exists:
            history = doc.to_dict().get('history', [])
        else:
            history = []

        history.append({'role': 'user', 'parts': [prompt]})

        try:
            response = model.generate_content(history)
            history.append({'role': 'model', 'parts': [response.text]})
            if len(history) > max_history_length:
                history = history[-max_history_length:]

            doc_ref.set({'history': history})

            response_chunks = split_response(response.text, discord_max_length)
            for chunk in response_chunks:
                await message.channel.send(chunk)

        except Exception as e:
            print(f"An error occurred during LLM interaction: {e}")
            await message.channel.send("Sorry, I couldn't process your request at this time.")
    else:
        await message.channel.send("That command is restricted to #debris-botspam.")


async def handle_deletehistory(message):
    if message.channel.id == 971245167254331422:
        if db is None:
            await message.channel.send("Firebase is not initialized. Cannot delete history.")
            return

        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        doc_ref = db.collection('conversation_history').document(channel_id).collection('users').document(user_id)

        try:
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.delete()
                await message.channel.send(f"Conversation history for {message.author.display_name} in this channel has been deleted.")
            else:
                await message.channel.send(f"No conversation history found for {message.author.display_name} in this channel.")
        except Exception as e:
            print(f"Error deleting history from Firebase: {e}")
            await message.channel.send("An error occurred while trying to delete your history.")

# Create a dictionary to map commands to their respective handler functions
command_handlers = {
    'ursus': handle_ursus,
    'servertime': handle_servertime,
    'time': handle_time,
    'esfera': handle_esfera,
    'help': handle_help,
    'roll': handle_roll,
    '8ball': handle_8ball,
    'weaponf': handle_weaponf,
    'ask': handle_ask,
    'deletehistory': handle_deletehistory,
}

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
    
  if message.content.startswith('~'):
    command = message.content[1:].lower().split()[0]  # Get the base command
    handler = command_handlers.get(command)
    if handler:
        await handler(message)
        
  if message.content.lower() == 'aran succ' and (875235978971861002 in list(
    role.id for role in message.author.roles)):
    response = f'Hey {message.author.display_name}, heard you play Aran. You have my condolences. You should gather everyone and go Hunter\'s Prey Changseop for this travesty'
    new = await message.reply(response)
    await new.add_reaction('<:FeelsAranMan:852726957091323934>')

  if message.author.id == 257995877367414785:
    roll = random.randint(1, 11)
    print("Ub3r rolled", roll)
    if roll == 1:
      text = message.content.lower()
      response = capi_sentence(text) # Using capi_sentence from helpers
      await message.reply(response)
  if re.search(r"\bread\b", message.content):
    roll = random.randint(1,5)
    print("Read was typed. Rolled:", roll)
    if roll == 1:
      await message.channel.send("Debris can't read <:DebrisCantRead:1157773828173332550>")
  if message.author.id == 181446303782404096:
      roll = random.randint(1,20)
      print("Zyn rolled: ", roll)
      if roll == 1:
          banana_message = await message.channel.send("A :banana: has spawned! Go claim it!")
          # Add the banana reaction to the message
          await banana_message.add_reaction('\U0001F34C')
          # Store the message ID in the database, indicating it's a banana message
          if db is not None:
              try:
                  doc_ref = db.collection('banana_spawns').document(str(banana_message.id))
                  # Only store 'claimed_by' initially
                  doc_ref.set({
                      'claimed_by': None
                  })
                  print(f"Banana spawn message {banana_message.id} recorded in database.")
              except Exception as e:
                  print(f"Error writing banana spawn to database: {e}")
                  
@client.event
async def on_reaction_add(reaction, user):
    # Ignore reactions from the bot itself
    if user == client.user:
        return

    # Check if the reaction is a banana emoji
    if str(reaction.emoji) == '\U0001F34C':
        message = reaction.message
        message_id = str(message.id)

        if db is not None:
            try:
                doc_ref = db.collection('banana_spawns').document(message_id)
                doc = doc_ref.get()

                if doc.exists:
                    banana_data = doc.to_dict()
                    claimed_by = banana_data.get('claimed_by')

                    # Check if the banana has already been claimed
                    if claimed_by is None:
                        # Claim the banana
                        user_id = str(user.id)
                        doc_ref.update({'claimed_by': user_id})

                        # Update user's total claims
                        user_claims_ref = db.collection('user_banana_claims').document(user_id)
                        user_claims_doc = user_claims_ref.get()

                        if user_claims_doc.exists:
                            current_claims = user_claims_doc.to_dict().get('total_claims', 0)
                        else:
                            current_claims = 0 # Initialize to 0 if the document doesn't exist

                        user_claims_ref.set({'total_claims': current_claims + 1})

                        # Send a channel message indicating who claimed the banana
                        claimed_message = f":banana: has been claimed by {user.display_name}! Total claims: {current_claims + 1}"
                        await message.channel.send(claimed_message)

                        print(f"User {user.display_name} claimed banana on message {message_id}. Total claims updated.")
                    else:
                        print(f"Banana on message {message_id} already claimed by user {claimed_by}.")

            except Exception as e:
                print(f"Error handling banana reaction: {e}")
                
client.run(my_secret)
