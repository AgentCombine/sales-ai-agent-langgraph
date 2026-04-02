#!/usr/bin/env python3

import sys

from database.db_manager import DatabaseManager, logger


def main() -> int:
    """Set up the database and insert initial data."""
    logger.info("Starting database setup...")

    db_manager = DatabaseManager()

    if not db_manager.create_database():
        logger.error("Failed to create database")
        return 1

    if db_manager.config.products_path and not db_manager.insert_products_from_json():
        logger.error("Failed to insert products")
        return 1

    logger.info("Database setup completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
