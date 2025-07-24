# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy all files from the current directory to the container's working directory
COPY . .

# Install any Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 to the outside world
EXPOSE 8080

# Run app.py when the container launches
CMD ["python", "app.py"]
