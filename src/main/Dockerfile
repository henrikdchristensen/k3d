# Base image with Python installed
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the tests and requirements into the container
COPY tests /app/tests
COPY tests/requirements.txt /app/requirements.txt

# Install test dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Set the default command to execute tests
CMD ["pytest", "-v", "--durations=10", "--junitxml=/app/test-results.xml", "/app/tests"]
