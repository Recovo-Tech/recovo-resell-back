import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("DATABASE_HOSTNAME", "localhost"),
    port=os.getenv("DATABASE_PORT", "5432"),
    database=os.getenv("DATABASE_NAME", "recovo"),
    user=os.getenv("DATABASE_USERNAME", "postgres"),
    password=os.getenv("DATABASE_PASSWORD"),
)

cursor = conn.cursor()
cursor.execute(
    """
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'second_hand_products' 
AND (column_name LIKE 'original%' OR column_name LIKE 'weight%')
ORDER BY column_name;
"""
)

result = cursor.fetchall()
print("Current columns with original/weight:")
for row in result:
    print(f"  - {row[0]}")

cursor.close()
conn.close()
