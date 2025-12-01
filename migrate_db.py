import logging
import sys
import firebase_admin
from firebase_admin import credentials, firestore
import config  # Uses the same config as your bot to find credentials

# --- Configuration ---
OLD_COLLECTION_NAME = 'user_gem_counts'
NEW_COLLECTION_NAME = 'user_profile'
BATCH_SIZE = 400  # Firestore batch limit is 500, using a slightly smaller number is safe

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stdout)
                    ])

def initialize_firebase():
    """Initializes the Firebase Admin SDK."""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_CRED_PATH)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        logging.info("Firestore database client initialized successfully.")
        return db
    except Exception as e:
        logging.critical(f"Failed to initialize Firebase: {e}")
        sys.exit(1)  # Exit if we can't connect to the DB

async def migrate_subcollections(db, old_doc_ref, new_doc_ref, batch):
    """Recursively migrates subcollections for a given document."""
    subcollections = old_doc_ref.collections()
    for subcollection in subcollections:
        docs = subcollection.stream()
        for doc in docs:
            new_sub_doc_ref = new_doc_ref.collection(subcollection.id).document(doc.id)
            batch.set(new_sub_doc_ref, doc.to_dict())
            # This recursive call would handle sub-sub-collections, if they exist
            # await migrate_subcollections(db, doc.reference, new_sub_doc_ref, batch)

def migrate_collection(db):
    """Reads documents from the old collection and writes them to the new one."""
    old_collection_ref = db.collection(OLD_COLLECTION_NAME)
    new_collection_ref = db.collection(NEW_COLLECTION_NAME)

    try:
        docs = old_collection_ref.stream()
        total_docs_migrated = 0
        total_subdocs_migrated = 0
        batch = db.batch()

        logging.info(f"Starting migration from '{OLD_COLLECTION_NAME}' to '{NEW_COLLECTION_NAME}'...")

        for doc in docs:
            doc_data = doc.to_dict()
            new_doc_ref = new_collection_ref.document(doc.id)

            # Add the main document to the batch
            batch.set(new_doc_ref, doc_data)
            total_docs_migrated += 1

            # --- Handle Subcollections ---
            subcollections = doc.reference.collections()
            for subcollection in subcollections:
                sub_docs = subcollection.stream()
                for sub_doc in sub_docs:
                    new_sub_doc_ref = new_doc_ref.collection(subcollection.id).document(sub_doc.id)
                    batch.set(new_sub_doc_ref, sub_doc.to_dict())
                    total_subdocs_migrated += 1

            # Commit the batch when it's full
            # Check against total operations, not just docs
            if (total_docs_migrated + total_subdocs_migrated) % BATCH_SIZE < 20: # Heuristic to commit before full
                batch.commit()
                logging.info(f"Committed a batch. {total_docs_migrated} main docs and {total_subdocs_migrated} sub-docs migrated so far...")
                batch = db.batch() # Start a new batch

        # Commit any remaining documents in the last batch
        batch.commit()

        logging.info(f"Migration complete! A total of {total_docs_migrated} main documents and {total_subdocs_migrated} sub-documents were migrated to '{NEW_COLLECTION_NAME}'.")
        return True

    except Exception as e:
        logging.error(f"An error occurred during migration: {e}")
        return False

def delete_old_collection(db):
    """Deletes all documents from the old collection."""
    collection_ref = db.collection(OLD_COLLECTION_NAME)
    try:
        docs = collection_ref.stream()
        total_docs_deleted = 0
        batch = db.batch()

        logging.info(f"Starting deletion of old collection '{OLD_COLLECTION_NAME}'...")

        for doc in docs:
            batch.delete(doc.reference)
            total_docs_deleted += 1

            if total_docs_deleted % BATCH_SIZE == 0:
                batch.commit()
                logging.info(f"Committed a delete batch. {total_docs_deleted} documents deleted so far...")
                batch = db.batch()

        # Commit the final batch
        if total_docs_deleted % BATCH_SIZE != 0:
            batch.commit()

        logging.info(f"Successfully deleted {total_docs_deleted} documents from '{OLD_COLLECTION_NAME}'.")

    except Exception as e:
        logging.error(f"An error occurred during deletion: {e}")

if __name__ == "__main__":
    db = initialize_firebase()
    
    # --- Step 1: Migration ---
    if migrate_collection(db):
        # --- Step 2: Deletion Confirmation ---
        print("\n---")
        print(f"Migration successful. The old collection '{OLD_COLLECTION_NAME}' can now be deleted.")
        print("This action is IRREVERSIBLE.")
        
        confirm = input(f"Type 'DELETE' to confirm the deletion of the '{OLD_COLLECTION_NAME}' collection: ")
        
        if confirm == "DELETE":
            delete_old_collection(db)
        else:
            logging.warning("Deletion cancelled. Please manually delete the old collection in the Firebase console.")
    else:
        logging.error("Migration failed. The old collection will not be deleted.")