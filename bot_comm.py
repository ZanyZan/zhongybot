import discord
import config
from datetime import datetime, timedelta, timezone
import random
import weapons as wp
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from helper import EIGHT_BALL_ANSWERS, calculate_time, get_acquisition_multiplier, shop_items, split_response
import math
import logging
import asyncio
# Define functions for each command
async def handle_ursus(message, my_time):
    """
    Calculates and displays the time until the next Ursus 2x meso event.
    The times are based on UTC and will be displayed in the user's local time.
    """
    # All calculations are in UTC, as that's MapleStory's server time.
    now_utc = datetime.fromtimestamp(my_time, timezone.utc)

    # Define Ursus time slots for the current UTC day.
    today_0100 = now_utc.replace(hour=1, minute=0, second=0, microsecond=0)
    today_0500 = now_utc.replace(hour=5, minute=0, second=0, microsecond=0)
    today_1800 = now_utc.replace(hour=18, minute=0, second=0, microsecond=0)
    today_2200 = now_utc.replace(hour=22, minute=0, second=0, microsecond=0)

    ursus_slots = [(today_0100, today_0500), (today_1800, today_2200)]

    # Find the current or next Ursus event
    for start, end in ursus_slots:
        if start <= now_utc < end:
            status_message = f"Ursus 2x meso is currently **active** and ends {discord.utils.format_dt(end, style='R')}."
            break
    else:
        # If no active slot is found, find the next upcoming one.
        future_starts = [s for s, _ in ursus_slots if s > now_utc]
        # If all of today's slots have passed, the next one is tomorrow at 01:00 UTC.
        next_start = min(future_starts) if future_starts else (now_utc + timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
        status_message = f"Ursus 2x meso is **not active**. The next session starts {discord.utils.format_dt(next_start, style='R')}."

    # Create the schedule information string using the correct times.
    schedule_info = (f"Ursus 2x meso is active between {discord.utils.format_dt(today_0100, style='t')} - {discord.utils.format_dt(today_0500, style='t')} "
                     f"and {discord.utils.format_dt(today_1800, style='t')} - {discord.utils.format_dt(today_2200, style='t')} (UTC).")
    full_response = f"{status_message}\n\n{schedule_info}"
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
    help_text = """
    Here is a list of available commands. Commands are not case-sensitive.
    
    **General Commands**
    `~help` - Shows this help message.
    `~ursus` - Shows the daily Ursus 2x meso times.
    `~servertime` - Displays the current server time (UTC).
    `~time` - Shows your local time.
    `~time +/-<hours>` - Calculates time relative to server reset (e.g., `~time +3`).
    `~weaponf <class> <tier>` - Calculates weapon flame stats (e.g., `~weaponf hero abso`).
    `~esfera` - Displays the Esfera PQ guide image.

    **Gem & Economy Commands**
    `~daily` - Claim your daily gems.
    `~checkgems` - Check your current gem balance.
    `~leaderboard` - Shows the top gem holders.
    `~shop` - Displays the gem shop.
    `~buy <item_id>` - Buys an item from the shop.
    `~inventory` - Shows your purchased items.
    `~slots [rolls]` - Play the slot machine (e.g., `~slots 5`).
    `~slotspayouts` - Shows the slot machine payouts and odds.

    **Fun & AI Commands**
    `~roll [d#]` - Rolls a die (d20 default, e.g., `~roll d100`).
    `~8ball <question>` - Asks the magic 8-ball a question.
    `~ask <prompt>` - Asks the bot's AI a question (in #debris-botspam).
    `~deletehistory` - Deletes your conversation history with the AI.

    **Admin Commands**
    `~givegems @user <amount>`
    `~takegems @user <amount>`
    `~spawngem`
    `~wipegems`

    Any issues or ideas for new commands? Please let Zany know!
    """
    embed = discord.Embed(title="Zhongy Helps",
                          description=help_text,
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
    answer = random.choice(EIGHT_BALL_ANSWERS)
    title = f'You asked: "{question}"'
    response = f'Magic 8 ball says: {answer}'
    embed = discord.Embed(title=title,
                          description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)

async def handle_weaponf(message):
    """
    Handles the ~weaponf command to calculate weapon flame stats.
    Uses the refactored WEAPON_LOOKUP from weapons.py for a unified,
    case-insensitive search.
    """
    args = message.content.split()
    if len(args) < 3:
        await message.channel.send("Invalid format. Please use `~weaponf <class/weapon> <weapontype>` (e.g., `~weaponf hero abso`).")
        return

    weapon_class_or_alias = args[1]
    weapon_tier = args[2]

    # Normalize inputs for lookup
    lookup_key = weapon_class_or_alias.lower()
    tier_key = weapon_tier.title()  # e.g., 'abso' -> 'Abso'

    # Use the new unified lookup dictionary from weapons.py
    weapon_stats_for_class = wp.WEAPON_LOOKUP.get(lookup_key)

    if not weapon_stats_for_class or not (base_attack := weapon_stats_for_class.get(tier_key)):
        await message.channel.send(f"Could not find data for '{weapon_class_or_alias}' with tier '{weapon_tier}'. Please check the names and try again.")
        return

    response = wp.weapon_calc(base_attack, tier_key)
    title = f'{tier_key} flame tiers for {weapon_class_or_alias.title()}'
    embed = discord.Embed(title=title,
                          description=response,
                          colour=discord.Colour.purple())
    await message.channel.send(embed=embed)


async def handle_ask(message, db, model, max_history_length, discord_max_length):
    if message.channel.id == config.BOT_SPAM_CHANNEL_ID:
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
    if message.channel.id == config.BOT_SPAM_CHANNEL_ID:
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
        target_channel_id = config.FORWARD_CHANNEL_ID

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
    if message.author.id not in config.ADMIN_USER_IDS:
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
    if message.author.id not in config.ADMIN_USER_IDS:
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

# Define payout structure
payouts = {
    (config.EMOJI_DIAMOND, config.EMOJI_DIAMOND, config.EMOJI_DIAMOND): 100, # Triple Diamond
    (config.EMOJI_STAR, config.EMOJI_STAR, config.EMOJI_STAR): 75, # Triple Star
	(config.EMOJI_GRAPES, config.EMOJI_GRAPES, config.EMOJI_GRAPES): 50, # Triple Grapes
    (config.EMOJI_ORANGE, config.EMOJI_ORANGE, config.EMOJI_ORANGE): 40, # Triple Orange
	(config.EMOJI_LEMON, config.EMOJI_LEMON, config.EMOJI_LEMON): 30, # Triple Lemon
    (config.EMOJI_CHERRY, config.EMOJI_CHERRY, config.EMOJI_CHERRY): 15, # Triple Cherry
    (config.EMOJI_DIAMOND, config.EMOJI_DIAMOND, None): 40, # Two diamonds
    (config.EMOJI_STAR, config.EMOJI_STAR, None): 30, # Two stars
}

# Helper dictionary to map payout keys to symbols for display
payouts_symbols = {
    (config.EMOJI_DIAMOND, config.EMOJI_DIAMOND, config.EMOJI_DIAMOND): config.EMOJI_DIAMOND,
    (config.EMOJI_STAR, config.EMOJI_STAR, config.EMOJI_STAR): config.EMOJI_STAR,
	(config.EMOJI_GRAPES, config.EMOJI_GRAPES, config.EMOJI_GRAPES): config.EMOJI_GRAPES,
    (config.EMOJI_ORANGE, config.EMOJI_ORANGE, config.EMOJI_ORANGE): config.EMOJI_ORANGE,
	(config.EMOJI_LEMON, config.EMOJI_LEMON, config.EMOJI_LEMON): config.EMOJI_LEMON,
    (config.EMOJI_CHERRY, config.EMOJI_CHERRY, config.EMOJI_CHERRY): config.EMOJI_CHERRY,
    (config.EMOJI_DIAMOND, config.EMOJI_DIAMOND, None): config.EMOJI_DIAMOND,
    (config.EMOJI_STAR, config.EMOJI_STAR, None): config.EMOJI_STAR,
}

# Define slot machine symbols and weights
#Cherry, Lemon, Orange, Grapes, Diamond, Star
symbols = [config.EMOJI_CHERRY, config.EMOJI_LEMON, config.EMOJI_ORANGE, config.EMOJI_GRAPES, config.EMOJI_STAR, config.EMOJI_DIAMOND] # UTF-8 symbols
weights = [0.3, 0.25, 0.2, 0.15, 0.07, 0.03] # Relative weights for each symbol
slot_cost = 2
num_reels = 3
async def handle_slots(message, db):
    if message.channel.id in config.BOT_SPAM_CHANNEL_ID: # Replace with your desired channel ID
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

        # Check for rigged ticket BEFORE payment transaction
        user_doc = user_gem_counts_ref.get()
        inventory = user_doc.to_dict().get('inventory', {}) if user_doc.exists else {}
        has_rigged_ticket = inventory.get('rigged_ticket', {}).get('quantity', 0) > 0
        total_cost = slot_cost * num_rolls

        try:
            @firestore.transactional
            def play_slots_transaction(transaction, user_ref, cost):
                snapshot = user_ref.get(transaction=transaction)
                if not snapshot.exists:
                    return "no_gems", 0 # User not found in database

                current_gems = snapshot.get('gem_count') or 0 # Use .get with default value

                if current_gems < cost:
                    return "not_enough_gems", current_gems # User doesn't have enough gems
                else:
                    new_gems = current_gems - cost
                    transaction.update(user_ref, {'gem_count': new_gems})
                    return "success", current_gems # Gems deducted successfully

            transaction_result, current_gems = play_slots_transaction(db.transaction(), user_gem_counts_ref, total_cost)

            if transaction_result == "no_gems":
                await message.channel.send(f"{message.author.display_name}, you don't have any gems yet. The slot machine costs {slot_cost} gem(s) per roll.")
            elif transaction_result == "not_enough_gems":
                await message.channel.send(f"{message.author.display_name}, you need {total_cost} gem(s) to play the slot machine {num_rolls} time(s). You currently have {current_gems} gems.")
            elif transaction_result == "success":
                payment_message = f"{message.author.display_name} paid {total_cost} gem(s) to play the slot machine {num_rolls} time(s)."
                await message.channel.send(payment_message)

                ticket_consumed_this_turn = False
                # If the user has a ticket, consume it now in a separate transaction
                if has_rigged_ticket:
                    @firestore.transactional
                    def consume_ticket_transaction(transaction, user_ref):
                        snapshot = user_ref.get(transaction=transaction)
                        if not snapshot.exists:
                            return False
                        
                        inventory = snapshot.to_dict().get('inventory', {})
                        ticket_data = inventory.get('rigged_ticket')

                        if not ticket_data or ticket_data.get('quantity', 0) <= 0:
                            return False # No ticket to consume

                        # Decrement ticket quantity
                        inventory['rigged_ticket']['quantity'] -= 1
                        
                        # If quantity is 0, remove the item from inventory
                        if inventory['rigged_ticket']['quantity'] == 0:
                            del inventory['rigged_ticket']
                        
                        transaction.update(user_ref, {'inventory': inventory})
                        return True

                    ticket_consumed_this_turn = consume_ticket_transaction(db.transaction(), user_gem_counts_ref)
                    if ticket_consumed_this_turn:
                        await message.channel.send("You slyly use a Rigged Ticket for your first spin...")

                total_winnings = 0
                results_message = ""

                for i in range(num_rolls):

                    # Simulate the spin
                    result = random.choices(symbols, weights=weights, k=num_reels)

                    winnings = 0

                    # Check for winning combinations
                    # Check if this is the first roll and a ticket was successfully consumed
                    if i == 0 and ticket_consumed_this_turn:
                        # Force a random win between 15 and 50 gems.
                        # Filter payouts to get combinations in the desired range, excluding "two of a kind" for simplicity.
                        small_win_payouts = {k: v for k, v in payouts.items() if 15 <= v <= 30 and None not in k}
                        # Randomly select one of the small win combinations
                        rigged_combination = random.choice(list(small_win_payouts.keys()))
                        result = list(rigged_combination)
                        winnings = small_win_payouts[rigged_combination]
                    else:
                        # Normal random spin
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
    if message.author.id not in config.ADMIN_USER_IDS: # Assuming 'aui' is the admin user ID
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
    if message.channel.id not in config.BOT_SPAM_CHANNEL_ID:
        await message.channel.send(f"That command is restricted to <#{config.BOT_SPAM_CHANNEL_ID}>.")
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
        def buy_item_transaction(transaction, user_ref, item_id, item_details, user_display_name):
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
            if item_details.get("type") != "consumable" and inventory.get(item_id, {}).get('quantity', 0) > 0:
                 return "already_owned"

            item_cost = item_details['cost']
            if current_gems < item_cost:
                return "not_enough_gems"

            new_gems = current_gems - item_cost
            current_quantity = inventory.get(item_id, {}).get('quantity', 0) # Use .get with a default value
            item_effect = item_details.get('effect', {})
            inventory[item_id] = {'quantity': current_quantity + 1, 'effect': item_effect}
            user_data['inventory'] = inventory # Update inventory in user_data

            # Update the document with new gem count and inventory
            transaction.update(user_ref, {'gem_count': new_gems, 'inventory': user_data['inventory']})

            return {"status": "success", "new_gems": new_gems}
        
        # Pass the entire item_to_buy dictionary into the transaction
        transaction_result = buy_item_transaction(
            db.transaction(), user_doc_ref, item_id, item_to_buy, message.author.display_name
        )

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

async def handle_use(message, db):
    """Handles the ~use command for consumable items."""
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot use items.")
        return

    args = message.content.split()
    if len(args) < 2:
        await message.channel.send("Please specify the item you want to use. Usage: `~use <item_id>`")
        return

    item_id_to_use = args[1].lower()
    item_details = shop_items.get(item_id_to_use)

    if not item_details or item_details.get("type") != "consumable":
        await message.channel.send(f"Item with ID `{item_id_to_use}` is not a usable item.")
        return

    user_id = str(message.author.id)
    user_doc_ref = db.collection('user_gem_counts').document(user_id)

    # Transaction to consume the item
    @firestore.transactional
    def consume_item_transaction(transaction, user_ref, item_id):
        snapshot = user_ref.get(transaction=transaction)
        if not snapshot.exists:
            return "no_inventory"

        inventory = snapshot.to_dict().get('inventory', {})
        item_data = inventory.get(item_id)

        if not item_data or item_data.get('quantity', 0) <= 0:
            return "not_owned"

        # Decrement item quantity
        inventory[item_id]['quantity'] -= 1
        
        # If quantity is 0, remove the item from inventory
        if inventory[item_id]['quantity'] == 0:
            del inventory[item_id]
        
        transaction.update(user_ref, {'inventory': inventory})
        return "success"

    try:
        consumption_result = consume_item_transaction(db.transaction(), user_doc_ref, item_id_to_use)

        if consumption_result in ["no_inventory", "not_owned"]:
            await message.channel.send(f"You do not have a **{item_details['name']}** to use.")
            return
        
        if consumption_result == "success":
            await message.channel.send(f"{message.author.display_name} opens the **{item_details['name']}**...")
            await asyncio.sleep(1)  # A little dramatic pause

            if item_id_to_use == "suspicious_bag":
                outcomes = ["win_gems", "lose_gems", "nothing", "curse"]
                weights = [0.25, 0.15, 0.50, 0.10]  # 25% win, 15% lose, 50% nothing, 10% curse
                chosen_outcome = random.choices(outcomes, weights=weights, k=1)[0]

                if chosen_outcome == "win_gems":
                    gems_won = random.randint(25, 100)
                    user_doc_ref.update({'gem_count': firestore.Increment(gems_won)})
                    await message.channel.send(f"Jackpot! You found **{gems_won}** gems inside! {config.EMOJI_GEM}")
                elif chosen_outcome == "lose_gems":
                    gems_lost = random.randint(5, 25)
                    user_doc_ref.update({'gem_count': firestore.Increment(-gems_lost)})
                    await message.channel.send(f"Oh no! The bag had a hole... you lost **{gems_lost}** gems. {config.EMOJI_GEM}")
                elif chosen_outcome == "nothing":
                    await message.channel.send("You open the bag... it's full of dust. You got nothing.")
                elif chosen_outcome == "curse":
                    curses = ["A mysterious voice whispers, 'Your shoe is untied.' You look down. It isn't. You feel... watched.", "The bag contained a single, ominous-looking sock. You now feel a strange compulsion to find its owner.", "As you open the bag, a cloud of glitter explodes, covering you. You'll be finding it for weeks."]
                    await message.channel.send(random.choice(curses))
            # You can add more `elif item_id_to_use == "other_item":` blocks here for other consumables.
            
    except Exception as e:
        logging.error(f"Error using item for user {user_id}: {e}")
        await message.channel.send("An error occurred while trying to use the item.")
        
async def handle_daily(message, db):
    """Handles the daily gem claim command, resetting at UTC midnight."""
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot claim daily gems.")
        return

    user_id = str(message.author.id)
    user_ref = db.collection('user_gem_counts').document(user_id)

    # Define base daily reward
    base_daily_reward = 10 # Or make it random random.randint(5, 15)

    try:
        doc = user_ref.get()
        current_time_utc = datetime.now(timezone.utc)
        user_data = {} # Initialize user_data

        if doc.exists:
            user_data = doc.to_dict()
            last_claim_utc = user_data.get('last_daily_claim')

            if last_claim_utc:
                # Check if the last claim was on the same calendar day in UTC
                if last_claim_utc.date() == current_time_utc.date():
                    # Calculate time until next UTC midnight
                    tomorrow_utc = current_time_utc.date() + timedelta(days=1)
                    next_reset_utc = datetime.combine(tomorrow_utc, datetime.min.time(), tzinfo=timezone.utc)
                    time_left = next_reset_utc - current_time_utc

                    hours, remainder = divmod(time_left.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    await message.channel.send(f"You've already claimed your daily gems today. Please wait another {int(hours)} hours and {int(minutes)} minutes for the reset.")
                    return

        # Check for gem acquisition booster using the helper function
        inventory = user_data.get('inventory', {})
        acquisition_multiplier = get_acquisition_multiplier(inventory)
        if acquisition_multiplier > 1.0:
            logging.info(f"User {message.author.display_name} has gem booster for daily. Applying multiplier: {acquisition_multiplier}")

        # Calculate final gem count after applying multiplier
        final_daily_reward = math.ceil(base_daily_reward * acquisition_multiplier)

        user_ref.set({
            'username': message.author.display_name,
            'gem_count': firestore.Increment(final_daily_reward),
            'last_daily_claim': current_time_utc
        }, merge=True)

        # Construct response message
        response_message = f"You have claimed your daily {base_daily_reward} gems! {config.EMOJI_GEM}"
        if acquisition_multiplier > 1.0:
            bonus_gems = final_daily_reward - base_daily_reward
            response_message += f"\nThanks to your Gem Acquisition Booster, you received a bonus of {bonus_gems} gem(s), for a total of {final_daily_reward}!"

        await message.channel.send(response_message)
        logging.info(f"User {message.author.display_name} ({user_id}) claimed their daily {final_daily_reward} gems.")
    except Exception as e:
        logging.error(f"Error processing daily claim for user {user_id}: {e}")
        await message.channel.send("An error occurred while processing your daily claim.")

async def handle_leaderboard(message, db):
    """Displays the top 10 users with the most gems."""
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot display the leaderboard.")
        return

    try:
        # Query the top 10 users by gem_count in descending order
        users_ref = db.collection('user_gem_counts')
        query = users_ref.order_by('gem_count', direction=firestore.Query.DESCENDING).limit(10)
        docs = query.stream()

        leaderboard_entries = []
        rank = 1
        for doc in docs:
            user_data = doc.to_dict()
            # Only show users with more than 0 gems
            if user_data.get('gem_count', 0) > 0:
                username = user_data.get('username', 'Unknown User')
                gem_count = user_data.get('gem_count')
                leaderboard_entries.append(f"**#{rank}**: {username} - {gem_count} {config.EMOJI_DIAMOND}")
                rank += 1
        
        if not leaderboard_entries:
            response = "The leaderboard is currently empty. Go find some gems!"
        else:
            response = "\n".join(leaderboard_entries)

        embed = discord.Embed(title=f"{config.EMOJI_DIAMOND} Gem Leaderboard {config.EMOJI_DIAMOND}", description=response, colour=discord.Colour.gold())
        await message.channel.send(embed=embed)

    except Exception as e:
        logging.error(f"Error retrieving leaderboard from Firebase: {e}")
        await message.channel.send("An error occurred while trying to retrieve the leaderboard.")

async def handle_starforce(message, db):
    """Handles the ~starforce command for a high-risk, high-reward gamble."""
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot use this command.")
        return

    # --- Game Parameters ---
    COST = 20
    SUCCESS_PAYOUT = 30  # Total gems returned on success (20 cost + 10 profit)
    BOOM_PENALTY = 50    # Additional loss on boom
    
    # Outcomes and their respective weights
    OUTCOMES = ["success", "fail", "boom"]
    WEIGHTS = [0.60, 0.35, 0.05] # 60% success, 35% fail, 5% boom

    user_id = str(message.author.id)
    user_ref = db.collection('user_gem_counts').document(user_id)

    try:
        # --- Transaction to handle the entire gamble ---
        @firestore.transactional
        def starforce_transaction(transaction, user_ref):
            snapshot = user_ref.get(transaction=transaction)
            current_gems = snapshot.to_dict().get('gem_count', 0) if snapshot.exists else 0
            
            if current_gems < COST:
                return "not_enough_gems", None, current_gems

            # --- Determine Outcome ---
            chosen_outcome = random.choices(OUTCOMES, weights=WEIGHTS, k=1)[0]
            
            gem_change = 0
            if chosen_outcome == "success":
                gem_change = SUCCESS_PAYOUT - COST # Net gain
            elif chosen_outcome == "fail":
                gem_change = -COST
            elif chosen_outcome == "boom":
                gem_change = -COST - BOOM_PENALTY

            # If a loss would make the balance negative, just take all gems.
            if current_gems + gem_change < 0:
                gem_change = -current_gems
            
            transaction.update(user_ref, {'gem_count': firestore.Increment(gem_change)})
            return chosen_outcome, gem_change, current_gems

        # Execute the transaction
        transaction_result, gem_change, current_gems = starforce_transaction(db.transaction(), user_ref)

        if transaction_result == "not_enough_gems":
            await message.channel.send(f"{message.author.display_name}, you need {COST} gems to attempt star forcing. You currently have {current_gems} gems.")
            return

        await message.channel.send(f"{message.author.display_name} attempts to star force their equipment for {COST} gems...")
        await asyncio.sleep(2) # Dramatic pause

        new_gem_balance = current_gems + gem_change

        if transaction_result == "success":
            response = f"**SUCCESS!** {config.EMOJI_STAR} Your equipment has been enhanced! You won **{gem_change}** gems."
        elif transaction_result == "fail":
            response = f"**FAIL!** The enhancement failed. You lost **{-gem_change}** gems."
        elif transaction_result == "boom":
            response = f"**BOOM!** {config.EMOJI_SPARKLE} Your item was destroyed! You lost **{-gem_change}** gems. Ouch."
        
        response += f"\nYour new balance is {new_gem_balance} gems."
        
        embed = discord.Embed(description=response, colour=discord.Colour.purple())
        await message.channel.send(embed=embed)

    except Exception as e:
        logging.error(f"Error during starforce for user {user_id}: {e}")
        await message.channel.send("An error occurred while trying to star force.")

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
    'daily': handle_daily,
    'leaderboard': handle_leaderboard,
    'givegems': handle_givegems,
    'takegems': handle_takegems,
    'slots': handle_slots,
    'slotspayouts': handle_slotspayouts,
    'wipegems': handle_wipegems,
    'shop': handle_shop,
    'buy': handle_buy,
    'inventory': handle_inventory,  # Consider making this a property of a user class
    'use': handle_use,
    'sf': handle_starforce,
}
