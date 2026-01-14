#!/bin/bash

# Cleanup script for Docker-based installations
# This runs INSIDE the container or on the host where volumes are mounted

# Delete files older than N days (default: 1 day)
DAYS_OLD=${1:-1}

echo "=========================================="
echo "PDF Tagger Cleanup (Docker) - $(date)"
echo "=========================================="
echo "Deleting files older than ${DAYS_OLD} day(s)"
echo ""

# Directories (container paths)
UPLOAD_DIR="/app/uploads"
OUTPUT_DIR="/app/outputs"
TMP_DIR="/app/tmp"

# Function to clean a directory
clean_directory() {
    local dir=$1
    local name=$2

    if [ -d "$dir" ]; then
        echo "Cleaning ${name}..."
        file_count=$(find "$dir" -type f -name "*.pdf" -mtime +${DAYS_OLD} 2>/dev/null | wc -l)

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

# For Docker Installation
# ========================

# Option 1: Run cleanup from host (recommended)
# ----------------------------------------------
# The Docker volumes are mounted on the host, so you can clean them directly

# 1. Find where Docker mounts the volumes:
#    docker volume inspect pdf-tagger_uploads
#    # Look for "Mountpoint" path

# 2. Create cleanup script on host with those paths:
#    #!/bin/bash
#    DAYS_OLD=1
#    find /var/lib/docker/volumes/pdf-tagger_uploads/_data -type f -name "*.pdf" -mtime +${DAYS_OLD} -delete
#    find /var/lib/docker/volumes/pdf-tagger_outputs/_data -type f -name "*.pdf" -mtime +${DAYS_OLD} -delete
#    find /var/lib/docker/volumes/pdf-tagger_tmp/_data -type f -name "*.pdf" -mtime +${DAYS_OLD} -delete

# 3. Or if using bind mounts (like in docker-compose.yml), clean the local directories:
#    #!/bin/bash
#    DAYS_OLD=1
#    find /path/to/pdf-tagger/uploads -type f -name "*.pdf" -mtime +${DAYS_OLD} -delete
#    find /path/to/pdf-tagger/outputs -type f -name "*.pdf" -mtime +${DAYS_OLD} -delete
#    find /path/to/pdf-tagger/tmp -type f -name "*.pdf" -mtime +${DAYS_OLD} -delete

# 4. Add to host crontab:
#    0 2 * * * /path/to/cleanup-docker-volumes.sh >> /var/log/pdf-tagger-cleanup.log 2>&1


# Option 2: Run cleanup inside container
# ---------------------------------------

# 1. Copy cleanup script into container or add to image

# 2. Use docker exec with cron on host:
#    0 2 * * * docker exec pdf-tagger /app/cleanup_docker.sh 1 >> /var/log/pdf-tagger-cleanup.log 2>&1

# 3. Or add cron to the Docker container itself (more complex, not recommended)


# Kubernetes/Cloud Deployments
# =============================

# For Kubernetes, create a CronJob:
#
# apiVersion: batch/v1
# kind: CronJob
# metadata:
#   name: pdf-tagger-cleanup
# spec:
#   schedule: "0 2 * * *"  # Daily at 2 AM
#   jobTemplate:
#     spec:
#       template:
#         spec:
#           containers:
#           - name: cleanup
#             image: registry.gitlab.com/kgleason/fix-my-pdfs:latest
#             command: ["/bin/bash", "-c"]
#             args:
#               - |
#                 find /app/uploads -type f -name "*.pdf" -mtime +1 -delete
#                 find /app/outputs -type f -name "*.pdf" -mtime +1 -delete
#                 find /app/tmp -type f -name "*.pdf" -mtime +1 -delete
#             volumeMounts:
#             - name: uploads
#               mountPath: /app/uploads
#             - name: outputs
#               mountPath: /app/outputs
#             - name: tmp
#               mountPath: /app/tmp
#           volumes:
#           - name: uploads
#             persistentVolumeClaim:
#               claimName: pdf-tagger-uploads
#           - name: outputs
#             persistentVolumeClaim:
#               claimName: pdf-tagger-outputs
#           - name: tmp
#             persistentVolumeClaim:
#               claimName: pdf-tagger-tmp
#           restartPolicy: OnFailure