# Use an official Python 3.9 runtime as a parent image
FROM python:3.9

# Set the working directory to /code inside the container
WORKDIR /code

# Copy the requirements file into the container at /code/
COPY ./requirements.txt /code/requirements.txt

# Install any needed packages specified in requirements.txt
# --no-cache-dir prevents storing the downloaded packages, reducing image size
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the local 'app' directory to '/code/app' in the container
COPY ./app /code/app

# Define the command to run the application when the container launches
# It starts the Uvicorn server, making the app available on port 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
