"""
Migration script to convert ChromaDB publish_date from string to epoch timestamp
"""
import logging
from datetime import datetime
from app.config.chroma_config import get_chroma_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_date_to_epoch(date_str: str) -> int:
    """
    Convert date string to epoch timestamp

    Args:
        date_str: Date string (e.g., "2025-11-04 12:30:00")

    Returns:
        Epoch timestamp (int)
    """
    try:
        # Parse various date formats
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return int(dt.timestamp())
            except ValueError:
                continue

        # If no format matches, return 0
        logger.warning(f"Could not parse date: {date_str}")
        return 0
    except Exception as e:
        logger.error(f"Error converting date {date_str}: {e}")
        return 0


def migrate_chromadb_dates():
    """
    Migrate all documents in ChromaDB to add epoch timestamp field
    """
    logger.info("Starting ChromaDB date migration...")

    try:
        # Get ChromaDB client and collection
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection("coin_news")

        # Get all documents
        logger.info("Fetching all documents from ChromaDB...")
        results = collection.get(include=["metadatas", "documents", "embeddings"])

        total_docs = len(results['ids'])
        logger.info(f"Found {total_docs} documents to migrate")

        if total_docs == 0:
            logger.warning("No documents found in collection")
            return

        # Prepare updated metadata
        updated_metadatas = []
        for i, metadata in enumerate(results['metadatas']):
            publish_date_str = metadata.get('publish_date', '')

            # Convert to epoch timestamp
            epoch_time = convert_date_to_epoch(publish_date_str)

            # Add epoch timestamp field
            updated_metadata = {**metadata, 'publish_date_epoch': epoch_time}
            updated_metadatas.append(updated_metadata)

            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{total_docs} documents")

        # Update all documents with new metadata
        logger.info("Updating ChromaDB with epoch timestamps...")
        collection.update(
            ids=results['ids'],
            metadatas=updated_metadatas
        )

        logger.info(f"✅ Successfully migrated {total_docs} documents!")
        logger.info("Added 'publish_date_epoch' field to all documents")

        # Verify migration
        sample = collection.get(limit=1, include=["metadatas"])
        if sample['metadatas']:
            logger.info(f"Sample metadata: {sample['metadatas'][0]}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate_chromadb_dates()


