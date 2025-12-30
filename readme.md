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
- supabase
- kestra
- pipecat
- open notebooklm

`apt update -y && apt upgrade -y`

`apt install curl -y`

`apt install docker.io -y`

`apt-get install -y ca-certificates curl gnupg`

`sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg`

`echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null`

`apt-get update`

`apt-get upgrade`

`apt-get install -y docker-compose-plugin`

`reboot`

Run `git clone https://github.com/patbhakta/vps.git` to clone this repo. cd into the vps directory and run `./prep.sh` to prepare the system. Review prep.sh first to see what it does and modify as needed.

Prep.sh will ask for 3 things: 

1. A username you want to login as (it's better if you don't use root)
2. The password for that user
3. The domain name you want to use (that you already own). For instance, I have tvl.st and want a n8n server to be reached at n.tvl.st, so here I enter tvl.st and press enter. 

After running the script, you will need to log out. Before logging back in, let's edit your ssh config file to make it easier to connect. Think of the name you would like to use to connect. If you don't have a config file, create one at `~/.ssh/config`. You want at least this entry:

```
Host vps
    HostName ipaddress
    User theusernameyoucreated
    IdentityFile ~/.ssh/thekeyyoucreatedintheinstall
```

Save that. Then you can run `ssh vps` to connect to your server. 

## Tailscale

Then you need to get a Tailscale account and add you home machine to your tailnet. You can do this by downloading the Tailscale app from the [Tailscale website](https://tailscale.com/).

### Create TSAUTHKEY

After its installed, you need a key to add your docker containers to the tailnet. I found the easiest way to do it is to add the key to a docker secret.

1.  Create a folder called `~/.config` on the home directory for the user you are logged in as. 
2.  Create a file called `tsauthkey` in the `~/.config` folder.
3.  Go to the tailscale admin page, click on Settings. On the left go to Keys. Click the button `Generate auth key...`.
4.  Enable `Reusable`. Click `Generate key`.
5.  Add the key to the `tsauthkey` file.
6.  Make the file only readable by the user: `chmod 600 ~/.config/tsauthkey`

### Install Tailscale on server

1.  Go to Machines 
2.  Click Add Device and choose Linux Server.
3.  Click Generate Install Script.
4.  Copy the script and run on your VPS. 
5.  Run `sudo tailscale up`


## n8n

1. Navigate into the n8n directory: `cd vps/n8n`
2. Review the .env file created by prep.sh

   a. `N8N_HOST` should be the hostname of your server.
   b. `WEBHOOK_URL` should be the URL of your server.
   c. `GENERIC_TIMEZONE` should be your timezone. You'll need to update this.

4.  Start the n8n container: `docker compose up -d`

## Caddy

1. Navigate to the caddy directory: `cd ~/vps/caddy`
2. prep.sh copied Caddyfile.example to Caddyfile and updated all the hostnames using your domain.
3. Edit the .env file and add your Cloudflare API Token. If you are not using Cloudflare for your domain's DNS, you have some research to do.

To get the Cloudflare API token:

1. Login to the Cloudflare dashboard
2. In the left sidebar, click Manage Account.
3. Click Account API Tokens.
4. Create a new token.
    a. Permissions should be Zone, Zone, Edit, and Zone, DNS, Edit. 
    b. Update Zone Resources to point to the domain used in prep.sh
5. When it shows you the token, copy it and paste it into the .env file.

Finally run `docker compose up -d`. This takes a bit to run. It is building a new version of Caddy with support for Cloudflare.

## Watchtower

This will update all the containers to the latest version every day at 4am

1. Navigate into the watchtower directory: `cd ~/vps/watchtower`
2. Edit the .env file and change the `TZ` to where ever you are. 
3. Start the watchtower container: `docker compose up -d`

## Karakeep

Hopefully you have added the Tailscale app to your local machine, or wherever you have Ollama installed. You will need to edit ~/vps/karakeep/.env` and change OLLAMA_BASE_URL to that machine with port 11434. Then make sure you have gemma3:12b, llava, and embeddinggemma:latest models pulled. 

Then run `docker compose up -d`