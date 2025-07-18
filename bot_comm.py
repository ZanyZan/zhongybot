import discord
import sys
from discord.ext import tasks
from datetime import datetime, timedelta, timezone
import random
import weapons as wp
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from helper import format_timestamp, calculate_time, get_start_of_week, get_end_of_week, split_response, capi_sentence, are_dates_in_same_week, format_month_day
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("zhongybot.log"),
                        logging.StreamHandler(sys.stdout)
                    ])
# Consider moving this to a config file or environment variable
# and using it in main.py as well.
aui = [90936340002119680, 264507975568195587]
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

    # Determine current status and remaining time using a more concise approach.
    if ursus_start1_epoch_current_day < my_time < ursus_end1_epoch_next_day:
        # Ursus active (night run)
        time_difference = ursus_end1_epoch_next_day - my_time
        status_message = 'Ursus 2x meso is currently active, it will end in '
    elif ursus_start2_epoch_current_day < my_time < ursus_end2_epoch_current_day:
        # Ursus active (day run)
        time_difference = ursus_end2_epoch_current_day - my_time
        status_message = 'Ursus 2x meso is currently active, it will end in '
    elif my_time < ursus_start2_epoch_current_day:
        # Ursus inactive (before first run)
        time_difference = ursus_start2_epoch_current_day - my_time
        status_message = 'Ursus 2x meso is not active, it will start in '
    elif ursus_end2_epoch_current_day < my_time < ursus_start1_epoch_current_day:
        # Ursus inactive (between runs)
        time_difference = ursus_start1_epoch_current_day - my_time
        status_message = 'Ursus 2x meso is not active, it will start in '
    else:
        # Fallback (should not be reached under normal circumstances)
        status_message = "Unable to determine next Ursus time."
        time_difference = 0

    # Combine message based on status or use the fallback message
    if time_difference > 0:
        response = status_message + str(timedelta(seconds=time_difference))
    else:
        response = status_message  # Use fallback message directly

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
            response = f"{message.author.display_name}, you don't have any gems yet. Keep an eye out for gem drops!"  # Minor text adjustment for consistency

        embed = discord.Embed(description=response, colour=discord.Colour.purple())
        await message.channel.send(embed=embed)

    except Exception as e:
        logging.error(f"Error retrieving gem count from Firebase: {e}")
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
    response = 'Command List.\n- Use `~ursus` : to look for ursus time!.\n- Use `~servertime` : to check server\'s time (or check the clock channel!).\n- Use `~time` : if by some divine intervention you don\'t remember your own time LOL\n- You can also use `~time (+/-)(#Number)` : to check your local time in relation to server\'s reset time. eg: `~time +3` `~time -3`.\n- Use `~esfera` : if you are lazy and don\'t want to check the guides for the esfera PQ picture.\n- Use `~8ball` : to ask any yes/no questions.\n- Use `~roll` : to roll a d20 die.\n- Use `~roll d#`: to roll a d# die. eg: `~roll d40`, rolls a d40 die, etc.\n- Use `~weaponf class/weapon weapontype`: will give you the attack flame for your specified class/weapon (weapontype being Abso/Arcane/Genesis) **Except for Zero. Was lazy to implement Zero. \n- Use `~ask` to ask the bot something and get an answer. \n- Use `~deletehistory` to delete your conversation history with the bot. \n- Use `~checkgems` to see how many gems you have. \n- Use `~givegems @user <amount>` (Admin only) to give gems to a user. \n- Use `~takegems @user <amount>` (Admin only) to take gems from a user. \n- Use `~spawngem` (Admin only) to manually spawn a gem.\n- Use `~slots`: to play the slot machine!.\n- Use `~slotspayouts`: to view the slot machine payouts.\n\nCommands are not case sensitive, you can do `~UrSuS` if you want.\n \nAny issues or if you have any ideas for new commands please, let Zany know!'
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
        # Affirmative
        0: "It is certain. As certain as taxes and server maintenance.",
        1: "It is decidedly so. The RNG gods are smiling upon you.",
        2: "Without a doubt. Go for it!",
        3: "Yes, definitely. You can bet your meso on it.",
        4: "You may rely on it. It's a sure thing.",
        5: "As I see it, yes. The outlook is as good as hitting a double prime line.",
        6: "Most likely. I'd put money on it, if I had any.",
        7: "Outlook good. It's a green light from me.",
        8: "Yes. Simple as that.",
        9: "Signs point to yes, but don't quote me on that.",
        # Non-committal
        10: "Reply hazy, try again. My crystal ball is as foggy as a map full of kishin smoke.",
        11: "Ask again later. I'm in the middle of a boss fight.",
        12: "Better not tell you now... spoilers!",
        13: "Cannot predict now. I'm getting server lag on that request.",
        14: "Concentrate and ask again. Maybe sacrifice a Pitched Boss item to the RNG gods first.",
        # Negative
        15: "Don't count on it. The odds are worse than getting a pitched drop.",
        16: "My reply is a resounding NO.",
        17: "My sources (who are totally not in this room) say no.",
        18: "Outlook not so good. It's like trying to solo Black Mage with a level 10 character.",
        19: "Very doubtful. I have a better chance of understanding the lore.",
        20: "Ask Greg about it. He probably knows.", # Special
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
        # Consider extracting this channel ID to a configuration file.
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
            logging.exception(f"An error occurred during LLM interaction:")  # Use logging.exception
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
            logging.exception(f"Error deleting history from Firebase:")  # Use logging.exception
            await message.channel.send("An error occurred while trying to delete your history.")

async def handle_forward(message, client):
        # Replace with the actual server channel ID you want to forward to
        target_channel_id = 808341519714484246  # <-- **IMPORTANT: Change this to your desired channel ID**

        # Get the target channel object
        target_channel = client.get_channel(target_channel_id)

        if target_channel is None:
            logging.error(f"Error: Target channel with ID {target_channel_id} not found.") # Consider using logging.error
            return

        # Format the message to be sent to the server channel
        forwarded_message = f"{message.content[len('forward '):].strip()}"

        try:
            await target_channel.send(forwarded_message)
            await message.channel.send("Message forwarded to the server.")
        except Exception as e:
            logging.exception(f"Error forwarding message:")  # Use logging.exception
            await message.channel.send("An error occurred while trying to forward your message.")


async def handle_givegems(message, db):	
    if message.author.id not in aui:
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
        logging.info(f"Gave {amount} gem(s) to user ID:{target_user.id}")

    except Exception as e:
        logging.exception(f"Error giving gems:")  # Use logging.exception
        await message.channel.send("An error occurred while trying to give gems.")

async def handle_takegems(message, db):
    # Check if the message author is authorized
    if message.author.id not in aui:
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
        @firestore.transactional
        def update_in_transaction(transaction, user_ref, amount_to_take):
            snapshot = user_ref.get(transaction=transaction)
            if snapshot.exists:
                current_gems = snapshot.get('gem_count') or 0  # Use .get with default value
                if current_gems == 0:
                    return "no_gems"
                if amount_to_take >= current_gems:
                    new_gems = 0
                    taken = current_gems
                else:
                    new_gems = current_gems - amount_to_take
                    taken = amount_to_take
                transaction.update(user_ref, {'gem_count': new_gems})
                return {"new_gems": new_gems, "taken": taken, "had": current_gems}
            else:
                return None

        result = update_in_transaction(db.transaction(), user_gem_counts_ref, amount)

        if result == "no_gems":
            await message.channel.send(f"{target_user.display_name} has 0 gems. Cannot take more away.")
        elif result is not None:
            taken = result["taken"]
            new_gems = result["new_gems"]
            had = result["had"]
            if taken < amount:
                await message.channel.send(
                    f"{target_user.display_name} only had {had} gem(s). Took all of them. They now have 0 gem(s)."
                )
            else:
                await message.channel.send(
                    f"Successfully took {taken} gem(s) from {target_user.display_name}. They now have {new_gems} gem(s)."
                )
            logging.info(f"Took {taken} gem(s) from user ID:{target_user.id}")
        else:
            await message.channel.send(f"Could not find {target_user.display_name}'s gem count in the database.")

    except Exception as e:
        logging.exception(f"Error taking gems:")  # Use logging.exception
        await message.channel.send("An error occurred while trying to take gems.")


# Define UTF-8 symbols as variables for slot machine
cherry = '\U0001F352'
lemon = '\U0001F34B'
orange = '\U0001F34A'
grapes = '\U0001F347'
diamond = '\U0001F48E'
star = '\U00002B50'


# Define payout structure
payouts = {
    (diamond, diamond, diamond): 100, # Triple Diamond
    (star, star, star): 75, # Triple Star
	(grapes, grapes, grapes): 50, # Triple Grapes
    (orange, orange, orange): 40, # Triple Orange
	(lemon, lemon, lemon): 30, # Triple Lemon
    (cherry, cherry, cherry): 15, # Triple Cherry
    (diamond, diamond, None): 40, # Two diamonds
    (star, star, None): 30, # Two stars
}

# Helper dictionary to map payout keys to symbols for display
payouts_symbols = {
    (diamond, diamond, diamond): diamond,
    (star, star, star): star,
	(grapes, grapes, grapes): grapes,
    (orange, orange, orange): orange,
	(lemon, lemon, lemon): lemon,
    (cherry, cherry, cherry): cherry,
    (diamond, diamond, None): diamond,
    (star, star, None): star,
}

# Define slot machine symbols and weights
#Cherry, Lemon, Orange, Grapes, Diamond, Star
symbols = [cherry, lemon, orange, grapes, star, diamond] # UTF-8 symbols
weights = [0.3, 0.25, 0.2, 0.15, 0.07, 0.03] # Relative weights for each symbol
slot_cost = 2
num_reels = 3
async def handle_slots(message, db):
    if message.channel.id == 971245167254331422: # Replace with your desired channel ID
        if db is None:  # Consider using an assertion here if db should always be initialized
            await message.channel.send("Firebase is not initialized. Cannot use the slots command.")
            return

        parts = message.content.split()
        num_rolls = 1  # Default number of rolls

        if len(parts) > 1:
            try:
                num_rolls = int(parts[1])
                if num_rolls <= 0:
                    await message.channel.send("Please provide a positive number of rolls.")
                    return
                if num_rolls > 20: # Set a reasonable limit for multi-rolls
                    await message.channel.send("You can roll at most 20 times at once.")
                    return
            except ValueError:
                await message.channel.send("Invalid number of rolls specified. Please provide a number after the command.")
                return


        user_id = str(message.author.id)
        user_gem_counts_ref = db.collection('user_gem_counts').document(user_id)

        total_cost = slot_cost * num_rolls

        try:
            @firestore.transactional
            def play_slots_transaction(transaction, user_ref, cost):
                snapshot = user_ref.get(transaction=transaction)
                if not snapshot.exists:
                    return "no_gems" # User not found in database

                current_gems = snapshot.get('gem_count') or 0 # Use .get with default value

                if current_gems < cost:
                    return "not_enough_gems" # User doesn't have enough gems
                else:
                    new_gems = current_gems - cost
                    transaction.update(user_ref, {'gem_count': new_gems})
                    return "success" # Gems deducted successfully

            transaction_result = play_slots_transaction(db.transaction(), user_gem_counts_ref, total_cost)

            if transaction_result == "no_gems":
                await message.channel.send(f"{message.author.display_name}, you don't have any gems yet. The slot machine costs {slot_cost} gem(s) per roll.")
            elif transaction_result == "not_enough_gems":
                await message.channel.send(f"{message.author.display_name}, you need {total_cost} gem(s) to play the slot machine {num_rolls} time(s). You currently have {user_gem_counts_ref.get(field_paths=[FieldPath(['gem_count'])]).to_dict().get('gem_count', 0)} gems.") # Fetch updated count for message
            elif transaction_result == "success":
                await message.channel.send(f"{message.author.display_name} paid {total_cost} gem(s) to play the slot machine {num_rolls} time(s).")

                total_winnings = 0
                results_message = ""

                for _ in range(num_rolls):

                    # Simulate the spin
                    result = random.choices(symbols, weights=weights, k=num_reels)

                    winnings = 0

                    # Check for winning combinations
                    # Check for three of a kind
                    if result[0] == result[1] == result[2]:
                        combination = (result[0], result[1], result[2])
                        if combination in payouts:
                            winnings = payouts[combination]
                    # Check for two of a kind (first two symbols)
                    elif result[0] == result[1]:
                         combination = (result[0], result[1], None)
                         if combination in payouts:
                             winnings = payouts[combination]
                    # Check for two of a kind (last two symbols)
                    elif result[1] == result[2]:
                         combination = (result[1], result[2], None)
                         if combination in payouts:
                             winnings = payouts[combination]
                    # Check for two of a kind (first and last symbols)
                    elif result[0] == result[2]:
                         combination = (result[0], result[2], None)
                         if combination in payouts:
                             winnings = payouts[combination]

                    total_winnings += winnings
                    results_message += f"Spin result: {' | '.join(result)}"
                    if winnings > 0:
                        results_message += f" - Won {winnings} gem(s)!\n"
                    else:
                        results_message += " - No win.\n"

                # If the user wins, add the total winnings to their gem count
                if total_winnings > 0:
                    @firestore.transactional
                    def add_winnings_transaction(transaction, user_ref, winnings):
                        transaction.update(user_ref, {'gem_count': firestore.Increment(winnings)})
                        return "success"  # Indicate successful transaction

                    add_winnings_transaction(db.transaction(), user_gem_counts_ref, total_winnings)

                updated_doc = user_gem_counts_ref.get()
                updated_gem_count = updated_doc.to_dict().get('gem_count', 0) if updated_doc.exists else 0

                 # Construct and send the final message
                final_message = results_message
                if total_winnings > 0:
                     final_message += f"\nTotal winnings: {total_winnings} gem(s)."
                else:
                     final_message += "\nNo total winnings this time."

                final_message += f"\nYour new gem balance is: {updated_gem_count}"

                await message.channel.send(final_message)


        except Exception as e:
            logging.exception(f"Error playing slots:")  # Use logging.exception
            await message.channel.send("An error occurred while trying to play the slot machine.")
    else:
        await message.channel.send("That command is restricted to <#debris-botspam>.")

async def handle_slotspayouts(message):
    """
    Handles the ~slotspayouts command to display the slot machine payout structure and probabilities.
    """
    payouts_message = "Slot Machine Payouts:\n"
    payouts_message += f"Cost to play: {slot_cost} gems per roll\n\n"
    payouts_message += "Winning Combinations:\n"

    # Calculate total weight
    total_weight = sum(weights)
    # Calculate probabilities for single symbols
    symbol_probabilities = {symbol: weight / total_weight for symbol, weight in zip(symbols, weights)}

    # Iterate through the payouts dictionary to display the information and probabilities
    for combination, payout_amount in payouts.items():
        symbol = combination[0]
        count = 3 if combination[2] is not None else 2

        if count == 3:
            # Probability for three of a kind (assuming independent spins)
            probability = symbol_probabilities.get(symbol, 0) ** 3 * 100
            payouts_message += f"{count} x {symbol}: {payout_amount} gems ({probability:.4f}%)\n"
        elif count == 2:
            # Probability of getting at least two of a symbol in 3 spins:
            # (Prob of S, S, not S) + (Prob of S, not S, S) + (Prob of not S, S, S) + (Prob of S, S, S)
            # = 3 * (prob_symbol * prob_symbol * prob_not_symbol) + (prob_symbol * prob_symbol * prob_symbol)
            prob_symbol = symbol_probabilities.get(symbol, 0)
            prob_not_symbol = 1 - prob_symbol
            probability = (3 * (prob_symbol ** 2) * prob_not_symbol + (prob_symbol ** 3)) * 100


            payouts_message += f"2+ x {symbol}: {payout_amount} gems ({probability:.4f}%)\n"


    embed = discord.Embed(title="Slot Machine Payouts", description=payouts_message, colour=discord.Colour.purple())
    await message.channel.send(embed=embed)

    
async def handle_wipegems(message, db, target_role_id):
    if message.author.id not in aui: # Assuming 'aui' is the admin user ID
        await message.channel.send("You are not authorized to use this command.")
        return

    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot wipe gems.")
        return

    # Get the guild (server) the message was sent from
    guild = message.guild
    if guild is None:
        await message.channel.send("This command can only be used in a server.")
        return

    # Get the target role
    target_role = guild.get_role(target_role_id)
    if target_role is None:
        await message.channel.send(f"Role with ID {target_role_id} not found in this server.")
        return

    wiped_users = []
    user_gem_counts_ref = db.collection('user_gem_counts')

    # Iterate through all members in the guild
    for member in guild.members:
        # Check if the member has the target role
        if target_role in member.roles:
            user_id = str(member.id)
            # Set the gem count to 0 for the user in the database. Consider batching these writes.
            try:
                user_gem_counts_ref.document(user_id).set({
                    'username': member.display_name,
                    'gem_count': 0
                }, merge=True) # Use merge=True to avoid overwriting other fields if they exist
                wiped_users.append(member.display_name)
                logging.info(f"Wiped gems for user ID:{user_id} ({member.display_name})")
            except Exception as e: # Catch all exceptions and log them, consider handling specific exceptions for better error handling
                logging.error(f"Error wiping gems for user {member.display_name} ({user_id}): {e}")


    if wiped_users:
        response = f"Wiped gem count for the following users with role '{target_role.name}':\n" + "\n".join(wiped_users)
        await message.channel.send(response)
    else:
        await message.channel.send(f"No users with role '{target_role.name}' found in this server.")  
        
async def handle_shop(message):
    """Displays the items available in the shop."""
    if message.channel.id != 971245167254331422:
        await message.channel.send("That command is restricted to debris-botspam.")
        return

    shop_message = "Welcome to the Gem Shop!\n\nAvailable Items:\n"
    for item_id, item_info in shop_items.items():
        shop_message += f"- **{item_info['name']}** (`{item_id}`): {item_info['description']} - Cost: {item_info['cost']} gem(s)\n"

    embed = discord.Embed(title="Gem Shop", description=shop_message, colour=discord.Colour.blue())
    await message.channel.send(embed=embed)


async def handle_buy(message, db):
    """Handles the purchase of an item from the shop."""
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot purchase items.")
        return

    args = message.content.split()
    if len(args) < 2:
        await message.channel.send("Please specify the item you want to buy. Usage: `~buy <item_id>`")
        return

    item_id = args[1].lower()
    item_to_buy = shop_items.get(item_id)

    if not item_to_buy:
        await message.channel.send(f"Item with ID `{item_id}` not found in the shop.")
        return

    user_id = str(message.author.id)
    user_doc_ref = db.collection('user_gem_counts').document(user_id)

    try:
        @firestore.transactional
        def buy_item_transaction(transaction, user_ref, item, item_cost, user_display_name):
            snapshot = user_ref.get(transaction=transaction)
            user_data = snapshot.to_dict() if snapshot.exists else None

            if user_data is None:
                # Create initial user data if document doesn't exist
                user_data = {'username': user_display_name, 'gem_count': 0, 'inventory': {}}
                transaction.set(user_ref, user_data)
            elif 'inventory' not in user_data:
                # Add inventory field if missing
                user_data['inventory'] = {}
                transaction.update(user_ref, {'inventory': user_data['inventory']})

            current_gems = user_data.get('gem_count', 0)
            inventory = user_data.get('inventory', {}) # Use .get with a default value

            # Check if the user already owns the unique item
            if item_to_buy.get("type") != "consumable" and inventory.get(item, {}).get('quantity', 0) > 0:
                 return "already_owned"


            if current_gems < item_cost:
                return "not_enough_gems"

            new_gems = current_gems - item_cost
            current_quantity = inventory.get(item, {}).get('quantity', 0) # Use .get with a default value
            inventory[item] = {'quantity': current_quantity + 1}
            user_data['inventory'] = inventory # Update inventory in user_data

            # Update the document with new gem count and inventory
            transaction.update(user_ref, {'gem_count': new_gems, 'inventory': user_data['inventory']})

            return {"status": "success", "new_gems": new_gems}


        transaction_result = buy_item_transaction(db.transaction(), user_doc_ref, item_id, item_to_buy['cost'], message.author.display_name)

        if transaction_result == "not_enough_gems":
            await message.channel.send(f"You don't have enough gems to buy **{item_to_buy['name']}**. You need {item_to_buy['cost']} gem(s).")
        elif transaction_result == "already_owned":
             await message.channel.send(f"You already own **{item_to_buy['name']}**. You can only have one of this item.")
        elif transaction_result.get("status") == "success":
            new_gems = transaction_result["new_gems"]
            await message.channel.send(f"Successfully purchased **{item_to_buy['name']}** for {item_to_buy['cost']} gem(s). Your new gem balance is {new_gems}.")


    except Exception as e:
        logging.error(f"Error during purchase transaction for user {user_id}: {e}")
        await message.channel.send("An error occurred while trying to process your purchase.")    
        
async def handle_inventory(message, db):
    """Displays the user's inventory."""
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot check inventory.")
        return

    user_id = str(message.author.id)
    user_doc_ref = db.collection('user_gem_counts').document(user_id)

    try:
        doc = user_doc_ref.get()
        if doc.exists:
            inventory = doc.to_dict().get('inventory', {})
            if not inventory:
                response = f"{message.author.display_name}, your inventory is empty."
            else:
                response = f"{message.author.display_name}'s Inventory:\n"
                for item_id, item_info in inventory.items():
                    # Get item name from shop_items for better display
                    item_name = shop_items.get(item_id, {}).get('name', item_id)
                    quantity = item_info.get('quantity', 0) # Use .get with a default value
                    response += f"- {item_name}: {quantity}\n"
        else:
            response = f"{message.author.display_name}, you don't have an inventory yet. Try purchasing an item from the shop!"

        embed = discord.Embed(title="Inventory", description=response, colour=discord.Colour.green())
        await message.channel.send(embed=embed)

    except Exception as e:
        logging.error(f"Error retrieving inventory from Firebase: {e}")
        await message.channel.send("An error occurred while trying to retrieve your inventory.")

         
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
        "description": "Supposedly improves your odds and makes you immune to misfortune.",
        "cost": 750, # Example cost
        "type": "passive", # Indicate it's a passive item (for narrative effect)
        "effect": {} # No direct effect on bot mechanics, purely for flavor/narrative
    },
    "luck_charm": {
        "name": "Luck Charm",
        "description": "Supposedly boosts your item drop rate in other games.",
        "cost": 1000, # Example cost
        "type": "passive", # Indicate it's a passive item (for narrative effect)
        "effect": {} # No direct effect on bot mechanics, purely for flavor/narrative
    }
}
command_handlers = {
    'ursus': handle_ursus,  # Consider using a more descriptive name, like 'handle_ursus_command'
    'servertime': handle_servertime,  # Same here
    'time': handle_time,  # And so on...
    'esfera': handle_esfera,  # Add docstrings to each function explaining its purpose
    'help': handle_help,  # This improves readability and maintainability
    'roll': handle_roll,
    '8ball': handle_8ball,
    'weaponf': handle_weaponf,
    'ask': handle_ask,
    'deletehistory': handle_deletehistory,
    'forward': handle_forward,
    'checkgems': handle_checkgems,
    'givegems': handle_givegems,
    'takegems': handle_takegems,
    'slots': handle_slots,
    'payout': handle_slotspayouts,
    'wipegems': handle_wipegems,
    'shop': handle_shop,
    'buy': handle_buy,
    'inventory': handle_inventory,  # Consider making this a property of a user class
}

#  Consider using a class to encapsulate user-related data and operations (gems, inventory, etc.)
# This would improve code organization and make it easier to manage user data.
