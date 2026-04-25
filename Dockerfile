FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create persistent directories
RUN mkdir -p databases chat_logs

EXPOSE 9001

CMD ["python", "main.py", "ui", "databases/agentcy.db", "roles.json", "9001"]
