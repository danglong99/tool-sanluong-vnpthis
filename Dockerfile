# 🐍 Use a lightweight and secure Python base image
FROM python:3.11-slim
FROM selenium/standalone-chrome:latest

USER root

# 🛠️ Step 1: Install prerequisites for adding new repositories
RUN apt-get update && \
    apt-get install -y wget curl gnupg ca-certificates

# 🔑 Step 2: Add the Google Chrome GPG key using the secure method
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg

# 📋 Step 3: Add the Google Chrome repository to APT sources
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# 🔄 Step 4: Update package lists and install Google Chrome
RUN apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 🗂️ Copy your application code
WORKDIR /app
COPY . .

# 📦 Install Python dependencies
# Assumes you have a requirements.txt file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🏃 Run the Python script
CMD ["python", "tool-day-sl.py"]