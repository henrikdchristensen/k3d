FROM python:3

# Set the working directory
WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Environment variables
ENV KUBERNETES_MODE=in-cluster
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Copy the rest of the code
COPY . .
EXPOSE 8080

# Run the app
CMD [ "python3", "app.py", "-u"]