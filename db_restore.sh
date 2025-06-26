#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- SCRIPT LOGIC ---

# 1. Get backup filename from command-line argument
if [ -z "$1" ]; then
    echo "Error: No backup filename provided."
    echo "Usage: ./restore_prod.sh <filename_from_s3>"
    exit 1
fi

BACKUP_FILENAME=$1
SQL_FILENAME="${BACKUP_FILENAME%.gz}"
APP_DIR="/root/app"

# --- CONFIGURATION (Non-Secret) ---
S3_BUCKET="resell-db-backups"
DB_USER="postgres"
DB_NAME="recovo"

echo "--- Production Database Restore Utility ---"
echo "Backup file to restore: $BACKUP_FILENAME"
echo ""

# 2. Securely prompt for secrets at runtime
echo "Please enter the required secrets for the production environment:"
read -sp "Enter PostgreSQL Password: " PGPASSWORD_INPUT
echo ""
read -sp "Enter Application Secret Key: " SECRET_KEY_INPUT
echo ""

if [ -z "$PGPASSWORD_INPUT" ] || [ -z "$SECRET_KEY_INPUT" ]; then
    echo "Error: Password and Secret Key cannot be empty."
    exit 1
fi

# 3. Final Confirmation
echo ""
echo "--- WARNING ---"
echo "You are about to STOP the API, WIPE the PRODUCTION database '$DB_NAME',"
echo "and restore it from the file '$BACKUP_FILENAME'."
echo "The application will be temporarily unavailable."
echo ""
read -p "Are you absolutely sure you want to continue? Type 'YES': " CONFIRMATION

if [ "$CONFIRMATION" != "YES" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "--- Starting Production Restore ---"

# Navigate to the app directory
cd "$APP_DIR"

# A function for cleanup to ensure it always runs
cleanup() {
  echo "Cleaning up local files..."
  rm -f "$SQL_FILENAME" "$BACKUP_FILENAME" ".env"
  echo "Restarting API service..."
  # Ensure the api service is running, even if the script failed midway
  docker compose --env-file .env up -d api
}
trap cleanup EXIT

# 4. Create a temporary .env file
echo "1. Creating temporary .env file for configuration..."
cat << EOF > .env
POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${PGPASSWORD_INPUT}
SECRET_KEY=${SECRET_KEY_INPUT}
# Add other variables your docker-compose.yml expects
ALGORITHM=HS256
DOCKER_IMAGE_NAME=placeholder
DOCKER_IMAGE_TAG=placeholder
EOF

# --- NEW STEP: Stop the API to release DB connections ---
echo "2. Stopping API service to release database connections..."
docker compose --env-file .env stop api

echo "3. Downloading backup from S3..."
aws s3 cp "s3://$S3_BUCKET/$BACKUP_FILENAME" .

echo "4. Uncompressing backup file..."
gunzip "$BACKUP_FILENAME"

echo "5. Dropping and recreating the production database..."
# We now add --env-file to all docker compose commands
docker compose --env-file .env exec -T db dropdb -U "$DB_USER" --if-exists "$DB_NAME"
docker compose --env-file .env exec -T db createdb -U "$DB_USER" "$DB_NAME"

echo "6. Importing data... (This may take a while)"
cat "$SQL_FILENAME" | docker compose --env-file .env exec -T db psql -U "$DB_USER" -d "$DB_NAME"

echo ""
echo "--- Restore Completed Successfully! ---"
# The 'trap' command will automatically call the cleanup and restart the api service now