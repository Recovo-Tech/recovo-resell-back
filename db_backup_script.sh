#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- CONFIGURATION ---
S3_BUCKET="resell-db-backups"

PROD_PROJECT="app"

# The database credentials from your GitHub Secrets
# NOTE: The script reads these from the container's perspective
# You just need the user and db names here.
PROD_DB_USER="postgres"
PROD_DB_NAME="recovo" 

# --- SCRIPT LOGIC ---
BACKUP_DIR="/root/db_backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

echo "Starting database backup process..."

# Create a temporary backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# 1. Backup Production Database
echo "Dumping production database: $PROD_DB_NAME..."
PROD_FILENAME="$BACKUP_DIR/${PROD_PROJECT}_${DATE}.sql.gz"
docker-compose -p $PROD_PROJECT exec -T db pg_dump -U $PROD_DB_USER -d $PROD_DB_NAME | gzip > $PROD_FILENAME

# 2. Upload backups to S3
echo "Uploading backups to S3 bucket: $S3_BUCKET..."
aws s3 cp $PROD_FILENAME s3://$S3_BUCKET/

# 3. Clean up local backup files
echo "Cleaning up local backup files..."
rm $PROD_FILENAME

echo "Backup process completed successfully."
