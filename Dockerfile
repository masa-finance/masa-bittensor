# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -vvv bittensor==7.2.0
RUN pip install bittensor[torch]
RUN python setup.py build install

# Make port 8000 available to the world outside this container ( SEEMS TO NOT TO BE WORKING )
EXPOSE 8000
ENV VALIDATOR_API_HOST=127.0.0.1


RUN chmod +x run.sh
CMD ["./run.sh"]