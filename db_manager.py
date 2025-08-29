import firebase_admin
from firebase_admin import credentials, firestore
import logging
import config
import threading

_db_client = None
# Use a re-entrant lock (RLock) to prevent deadlocks.
# This is crucial because reinitialize_db() calls initialize_db() while holding the lock.
_db_lock = threading.RLock()
def initialize_db():
    """
    Initializes the connection to Firestore.
    This should be called once when the bot starts.
    """
    global _db_client
    with _db_lock:
        if _db_client is not None:
            logging.warning("Database is already initialized.")
            return

        try:
            if not firebase_admin._apps:
                # Using FIREBASE_CRED_PATH to match your config file
                cred = credentials.Certificate(config.FIREBASE_CRED_PATH)
                firebase_admin.initialize_app(cred)
            _db_client = firestore.client()
            logging.info("Firestore database client initialized successfully.")
        except Exception as e:
            logging.critical(f"Failed to initialize Firebase: {e}")
            _db_client = None

def get_db():
    """
    Returns the global Firestore client instance.
    If the client is not initialized, it will attempt to do so.
    This function is thread-safe.
    """
    # First check without a lock for performance
    if _db_client is None:
        # If it's None, acquire the lock and check again
        with _db_lock:
            if _db_client is None:
                initialize_db()
    return _db_client

def reinitialize_db():
    """
    Forces re-initialization of the database connection. This can be called
    if the connection is detected to be stale or has failed.
    """
    global _db_client
    with _db_lock:
        logging.warning("Forcing re-initialization of Firestore connection.")
        if firebase_admin._apps:
            try:
                firebase_admin.delete_app(firebase_admin.get_app())
            except Exception as e:
                logging.error(f"Failed to delete existing Firebase app during re-initialization: {e}")
        
        _db_client = None # Clear the old client
        # This call is now safe because we are using an RLock
        initialize_db()
    return get_db()
