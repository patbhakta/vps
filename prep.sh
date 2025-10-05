#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# prep.sh — Interactive helper to create a non-root sudo user,
#                  harden SSH, and set up the VPS project.
#
# Works on modern Ubuntu (20.04/22.04) but should be portable to most
# systemd-based Linux distributions that ship OpenSSH and use /etc/ssh/sshd_config.
# -----------------------------------------------------------------------------

# ----------------------------------------------------------------------
#  Safety rails and script directory
# ----------------------------------------------------------------------
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# ----------------------------------------------------------------------
#  Install dependencies
# ----------------------------------------------------------------------
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -yq zsh eza

ZSH_BIN="$(command -v zsh || true)"
if [[ -n "$ZSH_BIN" && ! $(grep -Fxq "$ZSH_BIN" /etc/shells) ]]; then
  echo "$ZSH_BIN" >> /etc/shells
fi

# ----------------------------------------------------------------------
#  1. Get user input
# ----------------------------------------------------------------------
while true; do
    read -rp "Enter a username for the new non-root user: " username
    if [[ "$username" =~ ^[a-z][-a-z0-9_]*$ ]]; then
        break
    else
        echo "⚠️  Invalid username. Use lowercase letters, digits, underscores; must start with a letter."
    fi
done

while true; do
    read -rsp "Enter a password for that user: " password; echo
    read -rsp "Confirm password: " password_confirm; echo
    if [[ "$password" == "$password_confirm" && -n "$password" ]]; then
        break
    else
        echo "⚠️  Passwords do not match. Please try again."
    fi
done

read -rp "Enter the domain name you own (e.g., example.com): " domain; echo
read -rsp "Enter your Tailscale Auth Key (it will not be displayed): " tsauthkey; echo

# ----------------------------------------------------------------------
#  2. Abort early if the user already exists
# ----------------------------------------------------------------------
if id "$username" &>/dev/null; then
    echo "❌ User '$username' already exists." >&2
    exit 1
fi

# ----------------------------------------------------------------------
#  3. Create user, set password, and add to sudo/docker groups
# ----------------------------------------------------------------------
default_shell="/bin/bash"
[[ -x "$ZSH_BIN" ]] && default_shell="$ZSH_BIN"
useradd --create-home --shell "$default_shell" "$username"
echo "${username}:${password}" | chpasswd
usermod -aG sudo "$username"
usermod -aG docker "$username"

# ----------------------------------------------------------------------
#  4. Prepare the user’s home directory and SSH keys
# ----------------------------------------------------------------------
mkdir -p "/home/$username/.ssh"
chmod 700 "/home/$username/.ssh"

if [ -f "/root/.ssh/authorized_keys" ]; then
    cp /root/.ssh/authorized_keys "/home/$username/.ssh/authorized_keys"
    chmod 600 "/home/$username/.ssh/authorized_keys"
fi
chown -R "$username":"$username" "/home/$username/.ssh"

# ----------------------------------------------------------------------
#  5. Set up ZSH for the new user
# ----------------------------------------------------------------------
if [[ -x "$ZSH_BIN" ]]; then
  cat > "/home/$username/.zshrc" <<'EOF'
# ~/.zshrc – minimal starter file
export HISTFILE=~/.zsh_history
export HISTSIZE=10000
export SAVEHIST=10000
setopt inc_append_history share_history
alias la='eza -la'
PROMPT='%F{green}%n@%m%f:%F{blue}%~%f$ '
EOF
  chown "$username":"$username" "/home/$username/.zshrc"
fi

# ----------------------------------------------------------------------
#  6. Harden SSH daemon configuration
# ----------------------------------------------------------------------
SSHCFG='/etc/ssh/sshd_config'
patch_line() {
  local key=$1 value=$2
  if grep -qiE "^\s*#?\s*${key}\s+" "$SSHCFG"; then
    sed -Ei "s|^\s*#?\s*${key}\s+.*|${key} ${value}|I" "$SSHCFG"
  else
    echo "${key} ${value}" >> "$SSHCFG"
  fi
}
patch_line "PasswordAuthentication" "no"
patch_line "PermitRootLogin"        "no"
patch_line "UsePAM"                 "no"

# Remove cloud-init override file if present
if [[ -f /etc/ssh/sshd_config.d/50-cloud-init.conf ]]; then
    rm -f /etc/ssh/sshd_config.d/50-cloud-init.conf
fi

# ----------------------------------------------------------------------
#  7. Validate and reload sshd
# ----------------------------------------------------------------------
/usr/sbin/sshd -t && systemctl restart ssh
echo "✅ User '$username' created and SSH hardened successfully."

# ----------------------------------------------------------------------
#  8. Create configuration files from examples
# ----------------------------------------------------------------------
MEILI_MASTER_KEY="$(openssl rand -base64 36 | tr -dc 'A-Za-z0-9')"
NEXTAUTH_SECRET="$(openssl rand -base64 36)"
SEARXNG_SECRET="$(openssl rand -base64 36)"
POSTGRES_PASSWORD="$(openssl rand -base64 36)"
WEBUI_SECRET="$(openssl rand -base64 36)"

cp "$SCRIPT_DIR/caddy/example.env" "$SCRIPT_DIR/caddy/.env"
cp "$SCRIPT_DIR/watchtower/example.env" "$SCRIPT_DIR/watchtower/.env"

sed -e "s|bhakta.us|${domain}|g" "$SCRIPT_DIR/caddy/Caddyfile.example" > "$SCRIPT_DIR/caddy/Caddyfile"
sed -e "s|bhakta.us|${domain}|g" "$SCRIPT_DIR/n8n/example.env" > "$SCRIPT_DIR/n8n/.env"
sed -e "s|bhakta.us|${domain}|g" "$SCRIPT_DIR/searxng/example.env" > "$SCRIPT_DIR/searxng/.env"
sed -e "s|bhakta.us|${domain}|g" -e "s|webuisecret|${WEBUI_SECRET}|" "$SCRIPT_DIR/openwebui/example.env" > "$SCRIPT_DIR/openwebui/.env"
sed -e "s|postgrespassword|${POSTGRES_PASSWORD}|g" "$SCRIPT_DIR/postgres/example.env" > "$SCRIPT_DIR/postgres/.env"
sed -e "s|searxngsecret|${SEARXNG_SECRET}|g" "$SCRIPT_DIR/searxng/config/settings.yml.example" > "$SCRIPT_DIR/searxng/config/settings.yml"
sed -e "s|meilimasterkey|${MEILI_MASTER_KEY}|" -e "s|nextauthsecret|${NEXTAUTH_SECRET}|" -e "s|bhakta.us|${domain}|g" "$SCRIPT_DIR/karakeep/example.env" > "$SCRIPT_DIR/karakeep/.env"

# ----------------------------------------------------------------------
#  9. Create Tailscale auth key file and move project to user's home
# ----------------------------------------------------------------------
mkdir -p "/home/$username/.config"
echo -n "$tsauthkey" > "/home/$username/.config/tsauthkey"
chmod 600 "/home/$username/.config/tsauthkey"
chown -R "$username":"$username" "/home/$username/.config"

mv "$SCRIPT_DIR" "/home/$username/vps"
chown -R "$username":"$username" "/home/$username/vps"

echo "✅ Project setup complete. Log out and ssh back in as '$username'."