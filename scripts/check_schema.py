"""
Script to check the second_hand_products table schema
"""

import os
import sys

import psycopg2

# Database connection parameters
db_user = os.getenv("DATABASE_USERNAME", "postgres")
db_password = os.getenv("DATABASE_PASSWORD")
db_host = os.getenv("DATABASE_HOSTNAME", "localhost")
db_port = os.getenv("DATABASE_PORT", "5432")
db_name = os.getenv("DATABASE_NAME", "recovo")


def check_second_hand_products_schema():
    """Check the schema of second_hand_products table"""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
        )

        cursor = conn.cursor()

        # Get table columns
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'second_hand_products'
            ORDER BY ordinal_position;
        """
        )

        columns = cursor.fetchall()
        print("second_hand_products table schema:")
        for column in columns:
            print(f"  - {column[0]} ({column[1]}) - Nullable: {column[2]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error checking schema: {e}")


if __name__ == "__main__":
    check_second_hand_products_schema()
