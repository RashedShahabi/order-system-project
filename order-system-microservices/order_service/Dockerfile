# Use an official Python 3.11 slim runtime as a parent image
FROM python:3.11-slim

# Set the working directory to /app inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install the Python dependencies specified in the requirements file
# --no-cache-dir keeps the image size smaller by not storing the pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code into the container
COPY . .

# Define the command to run the application when the container starts
# It launches the Uvicorn server, making the app available on port 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
