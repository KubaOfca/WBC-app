# Install python
FROM python:3.10-slim

# Update Debian package manager
RUN apt-get -q -y update
RUN apt-get install -y gcc

# Set environment variables
ENV USERNAME=wbc-scan
ENV WORKING_DIR=/app

WORKDIR ${WORKING_DIR}

# Copy app
COPY . .

# Install python requirements
ENV PATH "$PATH:/home/${USERNAME}/.local/bin" # pip needs this for installations
RUN pip install --upgrade pip
RUN pip install -r requirement.txt

# Setup flask app
ENV FLASK_APP=main
EXPOSE 5000

# Run
CMD ["python", "main.py"]
