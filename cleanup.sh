# ============================================================================
# cleanup.sh - Cleanup Script for Cron
# ============================================================================
#!/bin/bash

# Cleanup script to delete old PDF files
# Run this with cron to keep disk space under control

# Set the base directory (adjust for your installation)
BASE_DIR="/path/to/pdf-tagger"

# Directories to clean
UPLOAD_DIR="${BASE_DIR}/uploads"
OUTPUT_DIR="${BASE_DIR}/outputs"
TMP_DIR="${BASE_DIR}/tmp"

# Delete files older than N days (default: 1 day)
DAYS_OLD=${1:-1}

echo "=========================================="
echo "PDF Tagger Cleanup - $(date)"
echo "=========================================="
echo "Deleting files older than ${DAYS_OLD} day(s)"
echo ""

# Function to clean a directory
clean_directory() {
    local dir=$1
    local name=$2
    
    if [ -d "$dir" ]; then
        echo "Cleaning ${name}..."
        file_count=$(find "$dir" -type f -name "*.pdf" -mtime +${DAYS_OLD} | wc -l)
        
        if [ $file_count -gt 0 ]; then
            find "$dir" -type f -name "*.pdf" -mtime +${DAYS_OLD} -delete
            echo "  ✓ Deleted ${file_count} file(s)"
        else
            echo "  ℹ No files to delete"
        fi
    else
        echo "  ⚠ Directory not found: ${dir}"
    fi
    echo ""
}

# Clean each directory
clean_directory "$UPLOAD_DIR" "Uploads"
clean_directory "$OUTPUT_DIR" "Outputs"
clean_directory "$TMP_DIR" "Temporary files"

# Show disk usage
echo "Current disk usage:"
du -sh "$UPLOAD_DIR" "$OUTPUT_DIR" "$TMP_DIR" 2>/dev/null || echo "Could not get disk usage"

echo "=========================================="
echo "Cleanup complete - $(date)"
echo "=========================================="

# ============================================================================
# CRON Configuration Instructions
# ============================================================================

# For Traditional Installation (non-Docker)
# ==========================================

# 1. Make the cleanup script executable:
#    chmod +x /path/to/pdf-tagger/cleanup.sh

# 2. Edit the script to set the correct BASE_DIR path

# 3. Test the script manually:
#    /path/to/pdf-tagger/cleanup.sh 1

# 4. Add to crontab (run daily at 2 AM, delete files older than 1 day):
#    crontab -e
#
#    Add this line:
#    0 2 * * * /path/to/pdf-tagger/cleanup.sh 1 >> /var/log/pdf-tagger-cleanup.log 2>&1

# 5. Alternative schedules:
#    # Every 6 hours, delete files older than 6 hours (0.25 days)
#    0 */6 * * * /path/to/pdf-tagger/cleanup.sh 0.25 >> /var/log/pdf-tagger-cleanup.log 2>&1
#
#    # Daily at 3 AM, delete files older than 7 days
#    0 3 * * * /path/to/pdf-tagger/cleanup.sh 7 >> /var/log/pdf-tagger-cleanup.log 2>&1
#
#    # Twice daily (2 AM and 2 PM), delete files older than 1 day
#    0 2,14 * * * /path/to/pdf-tagger/cleanup.sh 1 >> /var/log/pdf-tagger-cleanup.log 2>&1

