import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file.
# This should be one of the first things to run.
load_dotenv()

def _get_env_var(key: str, default=None, required: bool = True, var_type=str):
    """Helper to get and type-cast an environment variable."""
    value = os.getenv(key, default)
    if required and value is None:
        logging.critical(f"Missing required environment variable: {key}")
        raise ValueError(f"Missing required environment variable: {key}")
    if value is None:
        return None
    try:
        if var_type == bool:
            return value.lower() in ('true', '1', 't', 'y', 'yes')
        if var_type == list_int:
            return [int(i.strip()) for i in value.split(',')]
        return var_type(value)
    except (ValueError, TypeError) as e:
        logging.critical(f"Invalid type for environment variable {key}: {e}")
        raise

# Custom type for list of ints
def list_int(s):
    return [int(i.strip()) for i in s.split(',')]

# --- Bot Tokens and API Keys ---
DISCORD_TOKEN = _get_env_var("DISCORD_TOKEN")
GEMINI_API_KEY = _get_env_var("GEMINI_API_KEY")
FIREBASE_CRED_PATH = _get_env_var("FIREBASE_CRED_PATH")

# --- Model Configuration ---
GEMINI_MODEL_NAME = _get_env_var("GEMINI_MODEL_NAME", default="models/gemini-2.5-flash-preview-05-20", required=False)

# --- Discord IDs ---
ADMIN_USER_IDS = _get_env_var("ADMIN_USER_IDS", var_type=list_int)
GEM_SPAWN_CHANNEL_ID = _get_env_var("GEM_SPAWN_CHANNEL_ID", var_type=int)
BOT_SPAM_CHANNEL_ID = _get_env_var("BOT_SPAM_CHANNEL_ID", var_type=list_int)
FORWARD_CHANNEL_ID = _get_env_var("FORWARD_CHANNEL_ID", var_type=int)
MEMBER_ROLE_ID = _get_env_var("MEMBER_ROLE_ID", var_type=int)
GEM_FINDER_ROLE_ID = 1450020666337263676
HARRI_USER_ID = _get_env_var("HARRI_USER_ID", var_type=int)

# --- Bot Behavior Settings ---
DISCORD_MAX_LENGTH = _get_env_var("DISCORD_MAX_LENGTH", default=2000, var_type=int, required=False)
MAX_HISTORY_LENGTH = _get_env_var("MAX_HISTORY_LENGTH", default=20, var_type=int, required=False)
MIN_GEM_SPAWN_INTERVAL = _get_env_var("MIN_GEM_SPAWN_INTERVAL", default=36000, var_type=int, required=False)
MAX_GEM_SPAWN_INTERVAL = _get_env_var("MAX_GEM_SPAWN_INTERVAL", default=64800, var_type=int, required=False)
MINE_COOLDOWN_SECONDS = _get_env_var("MINE_COOLDOWN_SECONDS", default=7200, var_type=int, required=False)
PREFIX = '~'

# --- Emojis ---
EMOJI_FREE = '\U0001F193'
EMOJI_GEM = '\U0001F48E'
EMOJI_SPARKLE = '\U00002728'

# Slot Machine Emojis
EMOJI_CHERRY = '\U0001F352'
EMOJI_LEMON = '\U0001F34B'
EMOJI_ORANGE = '\U0001F34A'
EMOJI_GRAPES = '\U0001F347'
EMOJI_DIAMOND = EMOJI_GEM  # Re-use gem emoji for diamond
EMOJI_STAR = '\U00002B50'

logging.info("Configuration loaded successfully.")