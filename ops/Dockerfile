FROM python:3.12-slim

WORKDIR /app

# Set AWS region
ENV AWS_DEFAULT_REGION=us-east-1

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy script
COPY *.py .

CMD ["python", "monitor_weights.py"] 