# Note: I removed the original version of the caddy setup, in favor of what used to be caddy2. The original Caddy is still in caddy-orig.

This is a collection of docker-compose files for VPS.

## Services

- n8n
- searxng
- karakeep
- openwebui
- postgres
- redis
- caddy
- watchtower
- qdrant
- neo4j / graphiti

## Goals

I want to have a VPS that is self-hosted and runs on docker. I want to be able to access all of the services from the internet. But I don't want to let anyone access them...just me. n8n will be publicly accessible, but require authentication. The main thing that allows for this is Tailscale, which has a free plan that will let us do all we need.

## Video

[![Zero to MCP](http://img.youtube.com/vi/OmWJPJ1CR7M/0.jpg)](http://www.youtube.com/watch?v=OmWJPJ1CR7M "Zero to MCP")

## Initial Server Setup

This section guides you through preparing your VPS, creating a secure user, and configuring your environment.

### 1. Clone the Repository

First, log into your new VPS as `root` and clone this repository:

```bash
git clone https://github.com/patbhakta/vps.git
```

### 2. Run the Preparation Script

Navigate into the cloned directory and run the `prep.sh` script. This script will automate the setup process.

```bash
cd vps
./prep.sh
```

The script will prompt you for the following information:

1.  **New Username:** A username for the non-root user you will use to manage the server.
2.  **Password:** A password for this new user.
3.  **Domain Name:** The domain name you own and will use for your services (e.g., `example.com`).
4.  **Tailscale Auth Key:** A [Tailscale Auth Key](https://tailscale.com/kb/1085/auth-keys/) to automatically add your services to your tailnet. Make sure to generate a **reusable** key.

After the script finishes, it will move the `vps` directory to `/home/<your-new-username>/vps`.

### 3. Reconnect as the New User

Log out of the `root` account and log back in as the new user you just created. For easier access, you can add an entry to your local `~/.ssh/config` file:

```
Host myvps
    HostName <your-vps-ip-address>
    User <your-new-username>
    IdentityFile ~/.ssh/your_ssh_key
```

### 4. Configure Firewall

It is highly recommended to configure a firewall. If you are using Hostinger, follow these steps:

1.  Go to the [Hostinger HPanel](https://hpanel.hostinger.com) and manage your VPS.
2.  Click **Firewall** and create a new firewall configuration.
3.  Add rules to **ACCEPT** traffic for `SSH` and `HTTPS` from any source.
4.  Add a final rule to **DROP** all other incoming traffic.
5.  Ensure the firewall is enabled.

### 5. Install Tailscale on the Server

To complete the Tailscale setup, run the following command on your VPS:

```bash
sudo tailscale up
```

## Starting the Services

All services are managed with Docker Compose. After completing the initial setup, you can start them from the `~/vps` directory.

### Caddy (Reverse Proxy)

Caddy manages SSL and routes traffic to your services. Before starting it, you need to add your Cloudflare API token to its configuration.

1.  **Get a Cloudflare API Token:**
    *   Log in to the Cloudflare dashboard.
    *   Go to **My Profile > API Tokens** and create a new token.
    *   Use the **Edit zone DNS** template.
    *   Set the **Zone Resources** to include the domain you are using.
    *   Copy the generated token.

2.  **Configure Caddy:**
    *   Open the Caddy `.env` file: `nano ~/vps/caddy/.env`
    *   Paste your Cloudflare API token into the `CLOUDFLARE_API_TOKEN` field.

3.  **Start Caddy:**
    *   Navigate to the Caddy directory: `cd ~/vps/caddy`
    *   Run `docker compose up -d`. The first run will take some time as it builds a custom Caddy image with the Cloudflare DNS provider.

### n8n (Automation)

1.  Navigate to the n8n directory: `cd ~/vps/n8n`
2.  Review the `.env` file and adjust the `GENERIC_TIMEZONE` to your local timezone.
3.  Start the n8n container: `docker compose up -d`

### Other Services

All other services (`searxng`, `karakeep`, `openwebui`, etc.) can be started by navigating to their respective directories within `~/vps` and running `docker compose up -d`.

## Watchtower

This will update all the containers to the latest version every day at 4am

1. Navigate into the watchtower directory: `cd ~/vps/watchtower`
2. Edit the .env file and change the `TZ` to where ever you are. 
3. Start the watchtower container: `docker compose up -d`

## Karakeep

Hopefully you have added the Tailscale app to your local machine, or wherever you have Ollama installed. You will need to edit ~/vps/karakeep/.env` and change OLLAMA_BASE_URL to that machine with port 11434. Then make sure you have gemma3:12b, llava, and embeddinggemma:latest models pulled. 

Then run `docker compose up -d`

## Troubleshooting and Verification

After setting up the services, it's important to verify that everything is running correctly. Here are some steps to help you troubleshoot and test the deployment:

### 1. Check Container Status

To ensure all Docker containers are running, you can list them with the following command:

```bash
docker ps -a
```

Look for the `STATUS` column to see if the containers are `Up` or have exited. If a container is not running, you can check its logs for errors.

### 2. Inspect Container Logs

To view the logs for a specific service, use the `docker logs` command. For example, to check the logs for the `n8n` container, you would run:

```bash
docker logs n8n
```

Replace `n8n` with the name of the container you want to inspect. This is useful for debugging any issues with a specific service.

### 3. Verify Network Connectivity

All services are connected to a shared Docker network called `vps-network`. This allows them to communicate with each other. To verify that the network is set up correctly, you can inspect it with the following command:

```bash
docker network inspect vps-network
```

This will show you a list of all containers connected to the network. You should see Caddy and the other services you have started.

### 4. Test Service Communication

You can test if services can communicate with each other by executing a `ping` command from within a container. For example, to test if Caddy can reach `n8n`, you can run the following:

```bash
docker exec caddy ping n8n -c 4
```

If the ping is successful, it means the services can communicate over the shared network.

### 5. Check Caddy's Configuration

Caddy acts as a reverse proxy for the other services. You can check its logs to see if it's correctly routing traffic:

```bash
docker logs caddy
```

Look for any error messages related to your domain or the services it's trying to proxy to.