import discord
import os
import time
from datetime import datetime, timedelta, timezone
import pytz
import operator
import random
import weapons as wp
import re
import asyncio
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from helper import format_timestamp, calculate_time, get_start_of_week, get_end_of_week, split_response, capi_sentence, are_dates_in_same_week, format_month_day
aui = 90936340002119680
# Define functions for each command
async def handle_ursus(message, my_time):
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


async def handle_checkgems(message, db):
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot check gem count.")
        return

    user_id = str(message.author.id)
    user_gem_counts_ref = db.collection('user_gem_counts').document(user_id)

    try:
        doc = user_gem_counts_ref.get()
        if doc.exists:
            gem_count = doc.to_dict().get('gem_count', 0)
            response = f"{message.author.display_name}, you have {gem_count} gem(s)."
        else:
            response = f"{message.author.display_name}, you don't have any gems yet. Keep an eye out for gem drops!"

        embed = discord.Embed(description=response, colour=discord.Colour.purple())
        await message.channel.send(embed=embed)

    except Exception as e:
        print(f"Error retrieving gem count from Firebase: {e}")
        await message.channel.send("An error occurred while trying to retrieve your gem count.")
        
async def handle_servertime(message, my_time):
    UTC_time = datetime.fromtimestamp(my_time, timezone.utc).strftime('%H:%M %p')
    response = 'The server time right now is: ' + UTC_time + ' \n > Maplestory GMS uses UTC as default server time'
    embed = discord.Embed(description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)


async def handle_time(message, my_time):
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
    split_message = message.content.split('roll')
    arguments = split_message[1][1:]
    if not split_message[1]:
        dice_num = 20
        rolled_dice = random.randint(1, dice_num)
    elif split_message[1]:
        dice_num = int(arguments[1:])
        rolled_dice = random.randint(1, dice_num)
    response = f'{message.author.display_name} rolled a d{dice_num} and got {rolled_dice} '
    embed = discord.Embed(description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)


async def handle_8ball(message):
    split_message = message.content.split('8ball')
    question = split_message[1]
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


async def handle_ask(message, db, model, max_history_length, discord_max_length):
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


async def handle_deletehistory(message, db):
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

async def handle_forward(message, client):
        # Replace with the actual server channel ID you want to forward to
        target_channel_id = 808341519714484246  # <-- **IMPORTANT: Change this to your desired channel ID**

        # Get the target channel object
        target_channel = client.get_channel(target_channel_id)

        if target_channel is None:
            print(f"Error: Target channel with ID {target_channel_id} not found.")
            return

        # Format the message to be sent to the server channel
        forwarded_message = f"{message.content[len('forward '):].strip()}"

        try:
            await target_channel.send(forwarded_message)
            await message.channel.send("Message forwarded to the server.")
        except Exception as e:
            print(f"Error forwarding message: {e}")
            await message.channel.send("An error occurred while trying to forward your message.")


async def handle_givegems(message, db):	
    if message.author.id != aui:
        await message.channel.send("You are not authorized to use this command.")
        return

    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot use the ~givegems command.")
        return

    # Check if the message has mentions and arguments
    if not message.mentions or len(message.content.split()) < 3:
        await message.channel.send("Please mention a user and specify the amount of gems to give. Usage: `~givegems @user <amount>`")
        return

    # Get the mentioned user
    target_user = message.mentions[0]

    # Get the amount of gems from the message content
    try:
        amount = int(message.content.split()[2])
        if amount <= 0:
            await message.channel.send("Please provide a positive amount of gems to give.")
            return
    except ValueError:
        await message.channel.send("Invalid amount specified. Please provide a number.")
        return

    user_gem_counts_ref = db.collection('user_gem_counts').document(str(target_user.id))

    try:
        # Increment the user's gem count
        user_gem_counts_ref.set({
            'username': target_user.display_name,
            'gem_count': firestore.Increment(amount)
        }, merge=True)

        await message.channel.send(f"Successfully gave {amount} gem(s) to {target_user.display_name}.")
        print(f"Gave {amount} gem(s) to user ID:{target_user.id}")

    except Exception as e:
        print(f"Error giving gems: {e}")
        await message.channel.send("An error occurred while trying to give gems.")

async def handle_takegems(message, db):
    # Check if the message author is authorized
    if message.author.id != aui:
        await message.channel.send("You are not authorized to use this command.")
        return

    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot use the ~takegems command.")
        return

    # Check if the message has mentions and arguments
    if not message.mentions or len(message.content.split()) < 3:
        await message.channel.send("Please mention a user and specify the amount of gems to take. Usage: `~takegems @user <amount>`")
        return

    # Get the mentioned user
    target_user = message.mentions[0]

    # Get the amount of gems from the message content
    try:
        amount = int(message.content.split()[2])
        if amount <= 0:
            await message.channel.send("Please provide a positive amount of gems to take.")
            return
    except ValueError:
        await message.channel.send("Invalid amount specified. Please provide a number.")
        return

    user_gem_counts_ref = db.collection('user_gem_counts').document(str(target_user.id))

    try:
        # Use a transaction to ensure atomic update.
        @firestore.transactional
        def update_in_transaction(transaction, user_ref, amount_to_take):
            snapshot = user_ref.get(transaction=transaction) # Get within the transaction
            if snapshot.exists:
                current_gems = snapshot.get('gem_count') or 0
                new_gems = max(0, current_gems - amount_to_take) # Ensure gem count doesn't go below zero
                transaction.update(user_ref, {'gem_count': new_gems})
                return new_gems
            else:
                # If the user doesn't exist in the database, we can't take gems
                return None

        # Simply call the decorated function to run the transaction
        new_gem_count = update_in_transaction(db.transaction(), user_gem_counts_ref, amount)


        if new_gem_count is not None:
            await message.channel.send(f"Successfully took {amount} gem(s) from {target_user.display_name}. They now have {new_gem_count} gem(s).")
            print(f"Took {amount} gem(s) from user ID:{target_user.id}")
        else:
            await message.channel.send(f"Could not find {target_user.display_name}'s gem count in the database.")


    except Exception as e:
        print(f"Error taking gems: {e}")
        await message.channel.send("An error occurred while trying to take gems.")

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
    'forward': handle_forward,
    'checkgems': handle_checkgems,
    'givegems': handle_givegems,
    'takegems': handle_takegems,
}
