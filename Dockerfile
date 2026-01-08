# Use an official Python runtime as a parent image
FROM python:3.13

# Handles specifying the working directory within the container
WORKDIR /code

# Copy the local files to the container
COPY . /code

# Install required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Configure the Flask application to listen on port 8080
EXPOSE 8080

# Start Gunicorn with 4 worker processes
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "flaskfile:app"]