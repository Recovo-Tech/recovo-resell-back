#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- CONFIGURATION (Production Specific) ---
S3_BUCKET="resell-db-backups"
DB_USER="postgres"
DB_NAME="recovo" 

# --- SCRIPT LOGIC ---

# Check if a filename was provided as an argument
if [ -z "$1" ]; then
    echo "Error: No backup filename provided."
    echo "Usage: ./restore_db.sh <filename_from_s3>"
    exit 1
fi

BACKUP_FILENAME=$1
SQL_FILENAME="${BACKUP_FILENAME%.gz}" # Removes .gz from the end

echo "--- Production Database Restore Utility ---"
echo ""
echo "--- WARNING ---"
echo "You are about to completely WIPE the PRODUCTION database '$DB_NAME'"
echo "and restore it from the file '$BACKUP_FILENAME'."
echo "This action is irreversible and will affect the live application."
echo ""
read -p "Are you absolutely sure you want to continue? Type 'YES': " CONFIRMATION

if [ "$CONFIRMATION" != "YES" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "--- Starting Production Restore ---"

# Navigate to the app directory where docker compose.yml is located
# This ensures docker compose commands work without the -p flag
cd /root/app # Use the path for your production app

echo "1. Downloading backup from S3..."
aws s3 cp "s3://$S3_BUCKET/$BACKUP_FILENAME" .
if [ ! -f "$BACKUP_FILENAME" ]; then
    echo "Error: Download failed. Check the filename and S3 bucket."
    exit 1
fi

echo "2. Uncompressing backup file..."
gunzip "$BACKUP_FILENAME"

echo "3. Dropping and recreating the production database..."
docker compose exec -T db dropdb -U "$DB_USER" --if-exists "$DB_NAME"
docker compose exec -T db createdb -U "$DB_USER" "$DB_NAME"

echo "4. Importing data... (This may take a while)"
cat "$SQL_FILENAME" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"

echo "5. Cleaning up local files..."
rm "$SQL_FILENAME"

echo ""
echo "--- Production DB Restore Completed Successfully! ---"