#!/bin/bash
### ------------ IF YOU NEVER RUN THIS SCRIPT BEFORE, PLEASE READ THE COMMENTS BELOW CAREFULLY! ------------ ###
# Step 1: Create the .pgpass File on Your Server
# SSH into your production server.
# Create and open the special credentials file. The name and location are important.
# Bash

# nano ~/.pgpass
# (The ~ is a shortcut for your user's home directory, which is /root.)

# Add one line to this file in the following specific format:
# hostname:port:database:username:password

# For your Docker setup, the hostname is the name of your database service, which is db. So, the line you need to add is:

# db:5432:recovo:postgres:your_real_production_db_password

# chmod +x /root/backup_script.sh
# chmod 600 ~/.pgpass

# Save and exit (Ctrl + X, Y, Enter).
#--------------------------------------------------------

# Exit immediately if a command exits with a non-zero status.
set -e

# --- CONFIGURATION ---
S3_BUCKET="resell-db-backups"
PROD_PROJECT="app"
PROD_DB_USER="postgres"
PROD_DB_NAME="recovo"

# --- SCRIPT LOGIC ---
BACKUP_DIR="/root/db_backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

echo "Starting database backup process..."

mkdir -p $BACKUP_DIR

# 1. Backup Production Database
echo "Dumping production database: $PROD_DB_NAME..."
PROD_FILENAME="$BACKUP_DIR/${PROD_PROJECT}_${DATE}.sql.gz"

# NO password is needed here. pg_dump will find it in ~/.pgpass
docker compose -p $PROD_PROJECT exec -T db pg_dump -U $PROD_DB_USER -d $PROD_DB_NAME | gzip > $PROD_FILENAME

# 2. Upload backups to S3
echo "Uploading backups to S3 bucket: $S3_BUCKET..."
aws s3 cp $PROD_FILENAME s3://$S3_BUCKET/

# 3. Clean up local backup files
echo "Cleaning up local backup files..."
rm $PROD_FILENAME

echo "Backup process completed successfully."