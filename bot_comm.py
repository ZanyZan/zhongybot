import discord
import config
import os, sys
from datetime import datetime, timedelta, timezone
import random
import weapons as wp
from db_manager import get_db, reinitialize_db
from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from helper import (with_db_error_handling, EIGHT_BALL_ANSWERS, calculate_time,
                    get_booster_multiplier, shop_items, split_response, perform_upgrade_transaction,
                    PICKAXE_UPGRADE_COSTS, MAX_PICKAXE_LEVEL, PICKAXE_LEVEL_REWARDS, perform_booster_upgrade_transaction, MAX_GEM_BOOSTER_LEVEL, GEM_BOOSTER_UPGRADE_COSTS, GEM_BOOSTER_LEVEL_MULTIPLIERS)
import re
from google.api_core import exceptions as google_exceptions
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


@with_db_error_handling
async def handle_checkgems(message):
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return

    user_id = str(message.author.id)
    user_gem_counts_ref = db.collection('user_profile').document(user_id)

    doc = user_gem_counts_ref.get()
    if doc.exists:
        gem_count = doc.to_dict().get('gem_count', 0)
        response = f"{message.author.display_name}, you have {gem_count} gem(s)."
    else:
        response = f"{message.author.display_name}, you don't have any gems yet. Keep an eye out for gem drops!"
    embed = discord.Embed(description=response, colour=discord.Colour.purple())
    await message.channel.send(embed=embed)
        
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
    `~mine` - Use your pickaxe to find gems.
    `~leaderboard` - Shows the top gem holders.
    `~shop` - Displays the gem shop.
    `~buy <item_id>` - Buys an item from the shop.
    `~inventory` - Shows your purchased items.
    `~slots [rolls]` - Play the slot machine (e.g., `~slots 5`).
    `~upgrade <item> [confirm]` - Upgrade your `pickaxe` or `booster`.

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
    `~payoutpoll <message_id_or_url> <amount> [option_number]`

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


@with_db_error_handling
async def handle_ask(message, model, max_history_length, discord_max_length):
    if message.channel.id in config.BOT_SPAM_CHANNEL_ID:
        db = get_db()
        if db is None:
            await message.channel.send("Database connection is not available. Please try again later.")
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

        response = model.generate_content(history)
        history.append({'role': 'model', 'parts': [response.text]})
        if len(history) > max_history_length:
            history = history[-max_history_length:]

        doc_ref.set({'history': history})

        response_chunks = split_response(response.text, discord_max_length)
        for chunk in response_chunks:
            await message.channel.send(chunk)

    else:
        await message.channel.send("That command is restricted to #debris-botspam.")


@with_db_error_handling
async def handle_deletehistory(message):
    if message.channel.id not in config.BOT_SPAM_CHANNEL_ID:
        db = get_db()
        if db is None:
            await message.channel.send("Database connection is not available. Please try again later.")
            return

        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        doc_ref = db.collection('conversation_history').document(channel_id).collection('users').document(user_id)

        doc = doc_ref.get()
        if doc.exists:
            doc_ref.delete()
            await message.channel.send(f"Conversation history for {message.author.display_name} in this channel has been deleted.")
        else:
            await message.channel.send(f"No conversation history found for {message.author.display_name} in this channel.")


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


@with_db_error_handling
async def handle_givegems(message):
    if message.author.id not in config.ADMIN_USER_IDS:
        await message.channel.send("You are not authorized to use this command.")
        return

    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
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

    user_gem_counts_ref = db.collection('user_profile').document(str(target_user.id))

    # Increment the user's gem count
    user_gem_counts_ref.set({
        'username': target_user.display_name,
        'gem_count': firestore.Increment(amount)
    }, merge=True)

    await message.channel.send(f"Successfully gave {amount} gem(s) to {target_user.display_name}.")
    logging.info(f"Gave {amount} gem(s) to user ID:{target_user.id}")

@with_db_error_handling
async def handle_takegems(message):
    # Check if the message author is authorized
    if message.author.id not in config.ADMIN_USER_IDS:
        await message.channel.send("You are not authorized to use this command.")
        return

    db = get_db()
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

    user_gem_counts_ref = db.collection('user_profile').document(str(target_user.id))

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

@with_db_error_handling
async def handle_mine(message):
    """Handles the ~mine command for users with a pickaxe using a transaction."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return

    user_id = str(message.author.id)
    user_ref = db.collection('user_profile').document(user_id)
    
    @firestore.transactional
    def mine_transaction(transaction, user_ref):
        snapshot = user_ref.get(transaction=transaction)
        if not snapshot.exists:
            return "no_inventory", None

        user_data = snapshot.to_dict()
        inventory = user_data.get('inventory', {})
        pickaxe_data = inventory.get('pickaxe')

        # Check if user has an autominer
        if 'autominer' in inventory:
            return "has_autominer", None

        if not pickaxe_data:
            return "no_pickaxe", None

        # Check if pickaxe needs to be migrated to the new level system
        needs_inventory_update = False
        if 'level' not in pickaxe_data:
            pickaxe_data['level'] = 1
            inventory['pickaxe'] = pickaxe_data
            needs_inventory_update = True

        # Cooldown check
        last_mine_time = user_data.get('last_mine_time')
        current_time_utc = datetime.now(timezone.utc)

        if last_mine_time:
            # last_mine_time is a datetime object from Firestore.
            time_since_last_mine = current_time_utc - last_mine_time
            cooldown_seconds = config.MINE_COOLDOWN_SECONDS
            if time_since_last_mine.total_seconds() < cooldown_seconds:
                time_left = timedelta(seconds=cooldown_seconds) - time_since_last_mine
                return "cooldown", time_left

        # Mining logic
        pickaxe_level = pickaxe_data.get('level', 1) # Now guaranteed to exist
        min_gems, max_gems = PICKAXE_LEVEL_REWARDS.get(pickaxe_level, PICKAXE_LEVEL_REWARDS[1])
        gems_found = random.randint(min_gems, max_gems)

        # Calculate multipliers
        total_multiplier = 1.0
        # Generic acquisition booster
        acquisition_multiplier = get_booster_multiplier(inventory)
        total_multiplier *= acquisition_multiplier
        # Gem-finding Unicorn booster
        if 'unicorn' in inventory:
            unicorn_info = inventory.get('unicorn', {})
            unicorn_multiplier = unicorn_info.get('effect', {}).get('mining_multiplier', 1.0)
            total_multiplier *= unicorn_multiplier
        final_gems_found = math.ceil(gems_found * total_multiplier)

        # Update database within the transaction
        update_data = {
            'gem_count': firestore.Increment(final_gems_found),
            'last_mine_time': firestore.SERVER_TIMESTAMP
        }
        if needs_inventory_update:
            update_data['inventory'] = inventory
        
        transaction.update(user_ref, update_data)

        return "success", (gems_found, final_gems_found, total_multiplier)

    transaction = db.transaction()
    result, data = mine_transaction(transaction, user_ref)

    if result == "no_inventory":
        await message.channel.send("You don't have any items. You need to buy a pickaxe from the `~shop` to mine for gems!")
    elif result == "has_autominer":
        await message.channel.send(f"{message.author.display_name}, you have an Automated Mining Drill! It handles all your mining for you, so you don't need to use this command anymore.")
    elif result == "no_pickaxe":
        await message.channel.send("You need a pickaxe to mine for gems! You can buy one from the `~shop`.")
    elif result == "cooldown":
        time_left = data
        minutes, seconds = divmod(time_left.total_seconds(), 60)
        await message.channel.send(f"You're tired from your last mining session. Please wait another {int(minutes)} minute(s) and {int(seconds)} second(s).")
    elif result == "success":
        gems_found, final_gems_found, total_multiplier = data
        if total_multiplier > 1.0:
            bonus_gems = final_gems_found - gems_found
            response_message = f"{message.author.display_name}, you swing your pickaxe and find **{final_gems_found}** gem(s) ({gems_found} base + {bonus_gems} bonus)! {config.EMOJI_GEM}"
        else:
            response_message = f"{message.author.display_name}, you swing your pickaxe and find **{final_gems_found}** gem(s)! {config.EMOJI_GEM}"
        await message.channel.send(response_message)
        logging.info(f"User {message.author.display_name} ({user_id}) mined {final_gems_found} gems.")

@with_db_error_handling
async def handle_upgrade(message):
    """
    Handles viewing and performing upgrades for items like 'pickaxe' and 'booster'.
    Usage: `~upgrade <item> [confirm]`
    """
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return

    args = message.content.split()
    item_to_upgrade = args[1].lower() if len(args) > 1 else None

    # --- Map aliases to the correct inventory item_id ---
    item_id_map = {
        'booster': 'gem_booster'
    }

    # --- Configuration mapping for different upgradeable items ---
    upgrade_configs = {
        'pickaxe': {
            'name': 'Pickaxe',
            'transaction_func': perform_upgrade_transaction,
            'max_level': MAX_PICKAXE_LEVEL,
            'costs': PICKAXE_UPGRADE_COSTS,
            'rewards': PICKAXE_LEVEL_REWARDS,
            'info_embed_color': discord.Colour.purple(),
            'info_field_name': "Current Mining Rewards",
            'info_field_value_template': "{} - {} gems per `~mine`",
            'next_info_field_name': "New Mining Rewards",
            'next_info_field_value_template': "{} - {} gems",
        },
        'booster': {
            'name': 'Gem Acquisition Booster',
            'transaction_func': perform_booster_upgrade_transaction,
            'max_level': MAX_GEM_BOOSTER_LEVEL,
            'costs': GEM_BOOSTER_UPGRADE_COSTS,
            'rewards': GEM_BOOSTER_LEVEL_MULTIPLIERS,
            'info_embed_color': discord.Colour.blue(),
            'info_field_name': "Current Gem Multiplier",
            'info_field_value_template': "{}x on gem claims",
            'next_info_field_name': "New Gem Multiplier",
            'next_info_field_value_template': "{}x",
        }
    }

    if item_to_upgrade not in upgrade_configs:
        await message.channel.send("Please specify what you want to upgrade. Usage: `~upgrade <pickaxe|booster> [confirm]`")
        return

    config = upgrade_configs[item_to_upgrade]
    is_confirm = len(args) > 2 and args[2].lower() == 'confirm'
    user_id = str(message.author.id)
    user_ref = db.collection('user_profile').document(user_id)

    # --- Generic Upgrade Confirmation Logic ---
    if is_confirm:
        result, data = config['transaction_func'](db.transaction(), user_ref)

        if result in ["no_inventory", "no_pickaxe", "no_booster"]:
            await message.channel.send(f"You don't have a {config['name']} to upgrade. Buy one from the `~shop` first!")
        elif result == "max_level":
            await message.channel.send(f"Your {config['name']} is already at the maximum level ({config['max_level']})!")
        elif result == "not_enough_gems":
            cost = data
            await message.channel.send(f"You need {cost} gems to upgrade your {item_to_upgrade}.")
        elif result == "success":
            new_level, cost = data
            await message.channel.send(f"Congratulations! You spent {cost} gems and upgraded your {config['name']} to **Level {new_level}**!")
            logging.info(f"User {message.author.display_name} ({user_id}) upgraded {item_to_upgrade} to level {new_level}.")
        return

    # --- Generic Show Info Logic ---
    if not is_confirm:
        doc = user_ref.get()
        if not doc.exists:
            return

        user_data = doc.to_dict()
        inventory = user_data.get('inventory', {})
        # Use the map to get the correct item_id for the inventory lookup
        inventory_item_id = item_id_map.get(item_to_upgrade, item_to_upgrade)
        item_data = inventory.get(inventory_item_id)

        if not item_data:
            await message.channel.send(f"You don't have a {config['name']} to upgrade. Buy one from the `~shop` first!")
            return
        
        current_level = item_data.get('level', 1)
        current_reward = config['rewards'][current_level]

        embed = discord.Embed(title=f"{config['name']} Upgrade Information", colour=config['info_embed_color'])
        embed.add_field(name=f"Your Current {config['name']} Level", value=f"**Level {current_level}**", inline=False)
        
        # Format current reward based on whether it's a tuple (min, max) or a single value
        current_reward_value = config['info_field_value_template'].format(*current_reward) if isinstance(current_reward, tuple) else config['info_field_value_template'].format(current_reward)
        embed.add_field(name=config['info_field_name'], value=current_reward_value, inline=False)

        if current_level >= config['max_level']:
            embed.description = f"Your {config['name']} is at the maximum level!"
        else:
            upgrade_cost = config['costs'].get(current_level)
            next_level = current_level + 1
            next_reward = config['rewards'][next_level]
            next_reward_value = config['next_info_field_value_template'].format(*next_reward) if isinstance(next_reward, tuple) else config['next_info_field_value_template'].format(next_reward)
            
            embed.add_field(name="\u200b", value="--- **Next Level Stats** ---", inline=False)
            embed.add_field(name="Upgrade to Level", value=f"**Level {next_level}**", inline=True)
            embed.add_field(name="Upgrade Cost", value=f"{upgrade_cost} {config.EMOJI_GEM}", inline=True)
            embed.add_field(name=config['next_info_field_name'], value=next_reward_value, inline=False)
            embed.set_footer(text=f"To perform the upgrade, type `~upgrade {item_to_upgrade} confirm`")
        
        await message.channel.send(embed=embed)

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
@with_db_error_handling
async def handle_slots(message):
    if message.channel.id in config.BOT_SPAM_CHANNEL_ID: # Replace with your desired channel ID
        db = get_db()
        if db is None:
            await message.channel.send("Database connection is not available. Please try again later.")
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
        user_gem_counts_ref = db.collection('user_profile').document(user_id)

        # Check for rigged ticket BEFORE payment transaction
        user_doc = user_gem_counts_ref.get()
        inventory = user_doc.to_dict().get('inventory', {}) if user_doc.exists else {}
        has_rigged_ticket = inventory.get('rigged_ticket', {}).get('quantity', 0) > 0
        total_cost = slot_cost * num_rolls

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
                    # Create a sorted tuple of the result to check against payouts
                    sorted_result = tuple(sorted(result))

                    # Check for three of a kind first
                    if result[0] == result[1] == result[2]:
                        winnings = payouts.get(tuple(result), 0)
                    
                    # If no three-of-a-kind, check for two-of-a-kind
                    if winnings == 0:
                        # Check for pairs (e.g., A, A, B)
                        if result[0] == result[1] or result[0] == result[2] or result[1] == result[2]:
                            pair_symbol = result[0] if result.count(result[0]) == 2 else result[1]
                            winnings = payouts.get((pair_symbol, pair_symbol, None), 0)

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

    
@with_db_error_handling
async def handle_wipegems(message, target_role_id):
    if message.author.id not in config.ADMIN_USER_IDS: # Assuming 'aui' is the admin user ID
        await message.channel.send("You are not authorized to use this command.")
        return

    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
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
    user_gem_counts_ref = db.collection('user_profile')

    # Iterate through all members in the guild
    for member in guild.members:
        # Check if the member has the target role
        if target_role in member.roles:
            user_id = str(member.id)
            # Set the gem count to 0 for the user in the database. Consider batching these writes.
            user_gem_counts_ref.document(user_id).set({
                'username': member.display_name,
                'gem_count': 0
            }, merge=True) # Use merge=True to avoid overwriting other fields if they exist
            wiped_users.append(member.display_name)
            logging.info(f"Wiped gems for user ID:{user_id} ({member.display_name})")


    if wiped_users:
        response = f"Wiped gem count for the following users with role '{target_role.name}':\n" + "\n".join(wiped_users)
        await message.channel.send(response)
    else:
        await message.channel.send(f"No users with role '{target_role.name}' found in this server.")  
        
async def handle_shop(message):
    """Displays the items available in the shop, sorted by category."""
    if message.channel.id not in config.BOT_SPAM_CHANNEL_ID:
        await message.channel.send(f"That command is restricted to <#{config.BOT_SPAM_CHANNEL_ID}>.")
        return

    # Group items by category
    categorized_items = {}
    for item_id, item_info in shop_items.items():
        category = item_info.get('category', 'Uncategorized')
        if category not in categorized_items:
            categorized_items[category] = []
        categorized_items[category].append((item_id, item_info))

    embed = discord.Embed(title="Gem Shop", description="Welcome! Use `~buy <item_id>` to purchase.", colour=discord.Colour.blue())

    # Sort categories for consistent order and add them as fields to the embed
    for category in sorted(categorized_items.keys()):
        items_in_category = categorized_items[category]
        value = ""
        for item_id, item_info in items_in_category:
            value += f"**{item_info['name']}** (`{item_id}`)\n*{item_info['description']}*\nCost: {item_info['cost']} {config.EMOJI_GEM}\n\n"
        
        embed.add_field(name=f"--- {category} ---", value=value.strip(), inline=False)

    await message.channel.send(embed=embed)


@with_db_error_handling
async def handle_buy(message):
    """Handles the purchase of an item from the shop."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
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
    user_doc_ref = db.collection('user_profile').document(user_id)

    @firestore.transactional
    def buy_item_transaction(transaction, user_ref, item_id, item_details, user_display_name):
        snapshot = user_ref.get(transaction=transaction)
        user_data = snapshot.to_dict() if snapshot.exists else {}

        # Ensure user document has basic structure
        if not snapshot.exists:
            # Create initial user data if document doesn't exist
            user_data = {'username': user_display_name, 'gem_count': 0, 'inventory': {}}

        current_gems = user_data.get('gem_count', 0)
        inventory = user_data.get('inventory', {})

        # Check if the user already owns the unique item
        if item_details.get("type") != "consumable" and item_id in inventory:
             return "already_owned"

        item_cost = item_details['cost']
        if current_gems < item_cost:
            return "not_enough_gems"

        new_gems = current_gems - item_cost
        
        # Update inventory
        if item_id in inventory:
            inventory[item_id]['quantity'] += 1
        else:
            inventory[item_id] = {'quantity': 1, 'effect': item_details.get('effect', {})}
            # Special handling for pickaxe to add level on first purchase
            if item_id == 'pickaxe':
                inventory[item_id]['level'] = 1
            # Special handling for gem_booster to add level on first purchase
            if item_id == 'gem_booster':
                inventory[item_id]['level'] = 1

        # Update the document with new gem count and inventory
        transaction.set(user_ref, {'username': user_display_name, 'gem_count': new_gems, 'inventory': inventory}, merge=True)

        return {"status": "success", "new_gems": new_gems}
    
    # Pass the entire item_to_buy dictionary into the transaction
    transaction_result = buy_item_transaction(
        db.transaction(), user_doc_ref, item_id, item_to_buy, message.author.display_name
    )

    if transaction_result == "not_enough_gems":
        await message.channel.send(f"You don't have enough gems to buy **{item_to_buy['name']}**. You need {item_to_buy['cost']} gem(s).")
    elif transaction_result == "already_owned":
         await message.channel.send(f"You already own **{item_to_buy['name']}**. You can only have one of this item.")
    elif isinstance(transaction_result, dict) and transaction_result.get("status") == "success":
        new_gems = transaction_result["new_gems"]
        await message.channel.send(f"Successfully purchased **{item_to_buy['name']}** for {item_to_buy['cost']} gem(s). Your new gem balance is {new_gems}.")
        
@with_db_error_handling
async def handle_inventory(message):
    """Displays the user's inventory."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return

    user_id = str(message.author.id)
    user_doc_ref = db.collection('user_profile').document(user_id)

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

@with_db_error_handling
async def handle_use(message):
    """Handles the ~use command for consumable items."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
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

    if item_id_to_use == "rigged_ticket":
        await message.channel.send(f"The **{item_details['name']}** is used automatically on your next `~slots` roll. You don't need to use it manually!")
        return

    user_id = str(message.author.id)
    user_doc_ref = db.collection('user_profile').document(user_id)

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
                gems_won = random.randint(50, 100)
                user_doc_ref.update({'gem_count': firestore.Increment(gems_won)})
                await message.channel.send(f"Jackpot! You found **{gems_won}** gems inside! {config.EMOJI_GEM}")
            elif chosen_outcome == "lose_gems":
                gems_lost = random.randint(5, 25)
                user_doc_ref.update({'gem_count': firestore.Increment(-gems_lost)})
                await message.channel.send(f"Oh no! The bag contained a gem eating dragon... The dragon ate **{gems_lost}** gems. {config.EMOJI_GEM}")
            elif chosen_outcome == "nothing":
                await message.channel.send("You open the bag... it's full of dust. You got nothing.")
            elif chosen_outcome == "curse":
                curses = ["A mysterious voice whispers, 'Your shoe is untied.' You look down. It isn't. You feel... watched.", "The bag contained a single, ominous-looking sock. You now feel a strange compulsion to find its owner.", "As you open the bag, a cloud of glitter explodes, covering you. You'll be finding it for weeks."]
                await message.channel.send(random.choice(curses))
        # You can add more `elif item_id_to_use == "other_item":` blocks here for other consumables.
        
@with_db_error_handling
async def handle_daily(message):
    """Handles the daily gem claim command, resetting at UTC midnight."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return
    
    user_id = str(message.author.id)
    user_ref = db.collection('user_profile').document(user_id)
    
    # Define base daily reward
    base_daily_reward = 10
    
    doc = user_ref.get()
    current_time_utc = datetime.now(timezone.utc)
    user_data = {}
    
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
    
    # --- Streak Logic ---
    current_streak = user_data.get('daily_streak', 0)
    last_claim_date = user_data.get('last_daily_claim', None)
    
    if last_claim_date and (current_time_utc.date() == last_claim_date.date() + timedelta(days=1)):
        # User claimed yesterday, continue the streak
        current_streak += 1
    else:
        # User missed a day or it's their first claim, reset streak to 1
        current_streak = 1
        
    # Calculate streak bonus (e.g., 1 extra gem per day, capped at 7)
    streak_bonus = min(current_streak, 7)
    
    # Check for gem acquisition booster using the helper function
    inventory = user_data.get('inventory', {})
    acquisition_multiplier = get_booster_multiplier(inventory)
    if acquisition_multiplier > 1.0:
        logging.info(f"User {message.author.display_name} has gem booster for daily. Applying multiplier: {acquisition_multiplier}")
        
    # Calculate final gem count after applying multiplier
    total_base_reward = base_daily_reward + streak_bonus
    final_daily_reward = math.ceil(total_base_reward * acquisition_multiplier)
    
    user_ref.set({
        'username': message.author.display_name,
        'gem_count': firestore.Increment(final_daily_reward),
        'last_daily_claim': current_time_utc,
        'daily_streak': current_streak
    }, merge=True)
    
    # Construct response message
    response_message = f"You have claimed your daily **{base_daily_reward}** gems! {config.EMOJI_GEM}"
    if streak_bonus > 0:
        response_message += f"\nYour **{current_streak}-day streak** grants you a bonus of **{streak_bonus}** gem(s)!"
        
    if acquisition_multiplier > 1.0:
        booster_bonus = final_daily_reward - total_base_reward
        response_message += f"\nYour Gem Acquisition Booster added **{booster_bonus}** gem(s), for a total of **{final_daily_reward}**!"
        
    await message.channel.send(response_message)
    logging.info(f"User {message.author.display_name} ({user_id}) claimed their daily {final_daily_reward} gems.")

@with_db_error_handling
async def handle_leaderboard(message):
    """Displays the top 10 users with the most gems."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return

    # Query the top 10 users by gem_count in descending order
    users_ref = db.collection('user_profile')
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

@with_db_error_handling
async def handle_starforce(message):
    """Handles the ~starforce command for a high-risk, high-reward gamble."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return

    # --- Game Parameters ---
    COST = 20
    SUCCESS_PAYOUT = 30  # Total gems returned on success (20 cost + 10 profit)
    BOOM_PENALTY = 50    # Additional loss on boom
    
    # Outcomes and their respective weights
    OUTCOMES = ["success", "fail", "boom"]
    WEIGHTS = [0.60, 0.35, 0.05] # 60% success, 35% fail, 5% boom

    user_id = str(message.author.id)
    user_ref = db.collection('user_profile').document(user_id)

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

@with_db_error_handling
async def handle_payoutpoll(message, client):
    """Handles paying out gems to users who voted on a winning poll option."""
    if message.author.id not in config.ADMIN_USER_IDS:
        await message.channel.send("You are not authorized to use this command.")
        return

    db = get_db()
    if db is None:
        await message.channel.send("Firebase is not initialized. Cannot use this command.")
        return

    args = message.content.split()
    if len(args) < 3:
        await message.channel.send("Usage: `~payoutpoll <message_id_or_url> <amount> [option_number]`")
        return

    message_arg = args[1]
    try:
        amount = int(args[2])
        if amount <= 0:
            await message.channel.send("Please provide a positive amount of gems.")
            return
    except ValueError:
        await message.channel.send("Invalid amount specified. Please provide a number.")
        return

    winning_option_index = None
    if len(args) > 3:
        try:
            # User provides 1-based index, we convert to 0-based
            winning_option_index = int(args[3]) - 1
            if winning_option_index < 0:
                await message.channel.send("Option number must be 1 or greater.")
                return
        except ValueError:
            await message.channel.send("Invalid option number. Please provide a number.")
            return

    try:
        # Logic from discord.py's PartialMessageConverter
        id_regex = re.compile(r'(?:(?P<channel_id>[0-9]{15,20})-)?(?P<message_id>[0-9]{15,20})$')
        link_regex = re.compile(
            r'https?://(?:(ptb|canary|www)\.)?discord(?:app)?\.com/channels/'
            r'(?P<guild_id>[0-9]{15,20}|@me)'
            r'/(?P<channel_id>[0-9]{15,20})/(?P<message_id>[0-9]{15,20})/?$'
        )
        match = id_regex.match(message_arg) or link_regex.match(message_arg)
        if not match:
            await message.channel.send(f"Invalid message ID or URL format: `{message_arg}`")
            return
        
        data = match.groupdict()
        channel_id = discord.utils._get_as_snowflake(data, 'channel_id') or message.channel.id
        message_id = int(data['message_id'])
        
        target_channel = client.get_channel(channel_id)
        if not target_channel or not isinstance(target_channel, discord.abc.Messageable):
            await message.channel.send(f"Could not find the channel.")
            return

        poll_message = await target_channel.fetch_message(message_id)

    except discord.NotFound:
        await message.channel.send("The message or channel could not be found.")
        return
    except discord.Forbidden:
        await message.channel.send("I don't have permissions to read that message or channel.")
        return
    except Exception as e:
        logging.error(f"Error fetching poll message: {e}")
        await message.channel.send("An error occurred while fetching the poll message.")
        return

    if not poll_message.poll:
        await message.channel.send("The specified message does not contain a poll.")
        return

    # Find winning answer(s)
    winning_answers = []
    if winning_option_index is not None:
        if winning_option_index >= len(poll_message.poll.answers):
            await message.channel.send(f"Invalid option number. This poll only has {len(poll_message.poll.answers)} options (1 to {len(poll_message.poll.answers)}).")
            return
        winning_answers.append(poll_message.poll.answers[winning_option_index])
    else:
        # Automatic winner detection based on votes
        if not poll_message.poll.results:
            await message.channel.send("The poll results are not available. The poll might need to be closed first. Alternatively, specify the winning option number.")
            return

        max_votes = -1
        for answer in poll_message.poll.answers:
            answer_result = discord.utils.get(poll_message.poll.results.answer_counts, id=answer.id)
            if not answer_result:
                continue
            
            vote_count = answer_result.count
            if vote_count > max_votes:
                max_votes = vote_count
                winning_answers = [answer]
            elif vote_count == max_votes:
                winning_answers.append(answer)

        if max_votes <= 0:
            await message.channel.send("The poll has no votes. No one will be paid out.")
            return

    if not winning_answers:
        await message.channel.send("Could not determine a winning answer. Please specify one or ensure the poll has votes.")
        return
        
    # Get all voters for winning answers
    winning_voters = set()
    for answer in winning_answers:
        try:
            after_id = None
            while True:
                voter_data = await client.http.get_poll_answer_voters(
                    poll_message.channel.id, 
                    poll_message.id, 
                    answer.id,
                    limit=100,
                    after=after_id
                )
                
                users_on_page = [discord.User(state=client._connection, data=u) for u in voter_data['users']]
                if not users_on_page:
                    break
                
                for user in users_on_page:
                    winning_voters.add(user)
                
                after_id = users_on_page[-1].id

        except discord.HTTPException as e:
            logging.error(f"Failed to get voters for answer {answer.id}: {e}")
            await message.channel.send(f"An error occurred while fetching voters. Payout aborted.")
            return

    if not winning_voters:
        await message.channel.send("Found winning option(s), but could not fetch any voters. No one will be paid out.")
        return

    # Award gems
    batch = db.batch()
    user_gem_counts_ref = db.collection('user_profile')
    for user in winning_voters:
        user_ref = user_gem_counts_ref.document(str(user.id))
        batch.set(user_ref, {
            'username': user.display_name,
            'gem_count': firestore.Increment(amount)
        }, merge=True)

    batch.commit()
    
    winner_mentions = [user.mention for user in winning_voters]
    winning_answer_text = " / ".join([f"'{a.text}'" for a in winning_answers])
    
    response_start = (f"Successfully paid out **{amount}** {config.EMOJI_GEM} to **{len(winning_voters)}** voters "
                      f"for the winning poll option(s): {winning_answer_text}.\n\nWinners:\n")
    
    response_chunks = split_response(response_start + ", ".join(winner_mentions), 2000)
    
    for chunk in response_chunks:
        await message.channel.send(chunk)
        
    logging.info(f"Paid out {amount} gems to {len(winning_voters)} users for poll {poll_message.id}.")

@with_db_error_handling
async def handle_profile(message):
    """Displays a user's profile, including gems, inventory, and daily streak."""
    db = get_db()
    if db is None:
        await message.channel.send("Database connection is not available. Please try again later.")
        return

    # Determine the target user (either the author or a mentioned user)
    target_user = message.mentions[0] if message.mentions else message.author
    user_id = str(target_user.id)
    user_doc_ref = db.collection('user_profile').document(user_id)

    doc = user_doc_ref.get()

    if not doc.exists:
        await message.channel.send(f"{target_user.display_name} doesn't have a profile yet. Try participating in some activities!")
        return

    user_data = doc.to_dict()
    gem_count = user_data.get('gem_count', 0)
    daily_streak = user_data.get('daily_streak', 0)
    inventory = user_data.get('inventory', {})

    # --- Build the Embed ---
    embed = discord.Embed(
        title=f"{target_user.display_name}'s Profile",
        color=discord.Colour.purple()
    )
    if target_user.avatar:
        embed.set_thumbnail(url=target_user.avatar.url)

    # --- Add Stats ---
    embed.add_field(name=f"{config.EMOJI_GEM} Gems", value=f"**{gem_count}**", inline=True)
    embed.add_field(name=f"{config.EMOJI_STAR} Daily Streak", value=f"**{daily_streak}** day(s)", inline=True)

    # --- Format and Add Inventory ---
    if not inventory:
        inventory_text = "Your inventory is empty."
    else:
        inventory_list = []
        for item_id, item_info in sorted(inventory.items()):
            item_name = shop_items.get(item_id, {}).get('name', item_id.replace('_', ' ').title())
            quantity = item_info.get('quantity', 1)
            inventory_list.append(f"• {item_name} (x{quantity})")
        inventory_text = "\n".join(inventory_list)
    
    embed.add_field(name="🎒 Inventory", value=inventory_text, inline=False)

    await message.channel.send(embed=embed)

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
    'daily': handle_daily,
    'leaderboard': handle_leaderboard,
    'givegems': handle_givegems,
    'takegems': handle_takegems,
    'slots': handle_slots,
    'slotspayouts': handle_slotspayouts,
    'inv': handle_inventory,
    'wipegems': handle_wipegems,
    'shop': handle_shop,
    'buy': handle_buy,
    'inventory': handle_inventory,
    'use': handle_use,
    'sf': handle_starforce,
    'starforce': handle_starforce,
    'upgrade': handle_upgrade,
    'mine': handle_mine,
    'payoutpoll': handle_payoutpoll,
    'profile': handle_profile,
}
