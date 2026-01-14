FROM ubuntu:20.04

RUN apt-get update && apt-get install -y cron

# Copy the cron job file
COPY cleanup.crontab /etc/cron.d/cleanup

# Copy the script to run
RUN mkdir -p /app/bin &> /dev/null
COPY cleanup_docker.sh /app/bin

# Set permissions and apply the cron job
RUN chmod 0644 /etc/cron.d/cleanup && crontab /etc/cron.d/cleanup

# Create log file
RUN touch /var/log/cron.log

# Start cron in foreground
CMD ["cron", "-f"]