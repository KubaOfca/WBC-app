# WBC-Scan

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1. Docker Engine: [Download and Install Docker Engine](https://docs.docker.com/get-started/get-docker/)

2. Authenticator App: For Multi-Factor Authentication (MFA) functionality, you will need a Time-based One-Time Password (TOTP) authenticator app on your smartphone (e.g., Authy, Google Authenticator, Microsoft Authenticator). [Video tutorial](https://www.youtube.com/watch?v=tmnS821wCyc)

## Installation & Setup

Follow these steps to get WBC-Scan up and running on your local machine:

Start Docker Engine:
Ensure your Docker daemon is running in the background. On most systems, you can verify this by checking your Docker Desktop application or running docker info in your terminal.

### Clone the Repository (if applicable):

If you haven't already, clone the WBC-Scan repository to your local machine:

```
git clone https://github.com/KubaOfca/WBC-app
cd wbc-scan
```

### Build the Docker Container:

Navigate to the wbc-scan directory (where your docker-compose.yml file is located) and build the Docker images. This process can take a while (~15 minutes) as it downloads base images and installs application dependencies.

```
docker-compose build --no-cache
```

## Run the Containers:

Once the build is complete, you can start the application containers:

```
docker-compose up -d
```

## Usage

Access the Application:
Once the containers are running, open your web browser and navigate to:

http://localhost:5000

The WBC-Scan application should now be ready for use!

## Managing the Application

### Stopping the Application:

To stop all running services defined in your docker-compose.yml (without removing their data volumes), run:

```
docker-compose stop
```

### Stopping and Removing Containers:

To stop and remove all containers, networks, and volumes created by docker-compose up, use:

```
docker-compose down
```

## Viewing Logs:

To view the real-time logs from your running services (e.g., to debug issues):

```
docker-compose logs -f
```
