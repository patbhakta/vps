#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# create-user.sh — Interactive helper to create a non-root sudo user,
#                  harden SSH, and migrate root SSH keys.
#
# Works on modern Ubuntu (20.04/22.04) but should be portable to most
# systemd-based Linux distributions that ship OpenSSH and use /etc/ssh/sshd_config.
# -----------------------------------------------------------------------------

# ----------------------------------------------------------------------
#  Safety rails
# ----------------------------------------------------------------------
set -euo pipefail
# -e  : exit immediately on non-zero status
# -u  : treat unset variables as errors
# -o pipefail : fail a pipeline if any component command fails

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -yq zsh eza

ZSH_BIN="$(command -v zsh || true)"

# Add zsh to /etc/shells if missing
if [[ -n "$ZSH_BIN" && ! $(grep -Fx "$ZSH_BIN" /etc/shells) ]]; then
  echo "$ZSH_BIN" >> /etc/shells
fi

cp caddy/example.env caddy/.env
cp watchtower/example.env watchtower/.env

MEILI_MASTER_KEY="$(openssl rand -base64 36 | tr -dc 'A-Za-z0-9')"
NEXTAUTH_SECRET="$(openssl rand -base64 36)"
SEARXNG_SECRET="$(openssl rand -base64 36)"
POSTGRES_PASSWORD="$(openssl rand -base64 36)"
WEBUI_SECRET="$(openssl rand -base64 36)"

sed \
    -e "s|meilimasterkey|${MEILI_MASTER_KEY}|" \
    -e "s|nextauthsecret|${NEXTAUTH_SECRET}|" \
    -e "s|mydomain.com|${domain}|g" \
    karakeep/example.env > karakeep/.env
sed -e "s|mydomain.com|${domain}|g" caddy/Caddyfile.example > caddy/Caddyfile
sed -e "s|mydomain.com|${domain}|g" n8n/example.env > n8n/.env
sed -e "s|mydomain.com|${domain}|g" searxng/example.env > searxng/.env
sed -e "s|mydomain.com|${domain}|g" -e "s|webuisecret|${WEBUI_SECRET}|" openwebui/example.env > openwebui/.env
sed -e "s|searxngsecret|${SEARXNG_SECRET}|g" searxng/config/settings.yml.example > searxng/config/settings.yml
sed -e "s|postgrespassword|${POSTGRES_PASSWORD}|g" postgres/example.env > postgres/.env

cd ~
mv vps /home/$username/vps
chown -R $username:$username /home/$username/vps

mkdir /home/$username/.config
chown -R $username:$username /home/$username/.config
