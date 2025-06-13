# Use the official Python image from Docker Hub
FROM python:3.12-slim
# Set the working directory
WORKDIR /app
# Copy the requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the bot files (including the .env file)
COPY . /app/
# Run the bot
CMD ["python", "dino.py"]
