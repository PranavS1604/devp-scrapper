# Use the official Playwright image so Chromium works flawlessly
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code into the container
COPY . .

# Start the Discord bot when the container launches
CMD ["python", "bot.py"]