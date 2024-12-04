FROM python:3

# Set the working directory
WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Environment variables
ARG KUBERNETES_MODE=in-cluster
ENV KUBERNETES_MODE=${KUBERNETES_MODE}
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Copy the rest of the code
COPY . .

# Run the app
CMD ["python3", "app.py"]