#!/bin/bash
# Runs ON the server (called by deploy.ps1 with sudo): install / update /opt/sgserver and restart the service.
# Arguments: public IP, game port, countdown seconds (0 = restart now), update download port.  Safe to run again.
set -e
IP="$1"; PORT="${2:-3000}"; COUNTDOWN="${3:-0}"; UPORT="${4:-3001}"; RPORT="${5:-3002}"
APP=/opt/sgserver; NEW=/tmp/sgdeploy; TS=$(date +%Y%m%d-%H%M%S)

id sg >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin sg
mkdir -p "$APP/server" "$APP/tools" "$APP/logs" "$APP/deploy-backups" "$APP/updates/objects" "$APP/updates/versions"
command -v python3 >/dev/null || (apt-get update -qq && apt-get install -y -qq python3)
# (2026-11-02) encrypted connection + encrypted game.db need the 'cryptography' package
python3 -c 'import cryptography' 2>/dev/null || (apt-get update -qq && apt-get install -y -qq python3-cryptography)

# 1. back up the player data before touching anything (last 30 kept)
if [ -f "$APP/server/game.db" ]; then
  python3 -c "import sqlite3; s=sqlite3.connect('$APP/server/game.db'); d=sqlite3.connect('/tmp/game-$TS.db'); s.backup(d); d.close()"
  tar -czf "$APP/deploy-backups/data-$TS.tgz" -C /tmp "game-$TS.db" -C "$APP/server" $(cd "$APP/server" && ls gm_accounts.json 2>/dev/null)
  rm -f "/tmp/game-$TS.db"
  chmod 600 "$APP"/deploy-backups/*.tgz
  ls -1t "$APP"/deploy-backups/data-*.tgz | tail -n +31 | xargs -r rm -f
fi

# 1b. (2026-11-02) the keys deploy.ps1 uploaded to /tmp/sgkeys: connection key -> $APP/.netkey, database key -> $APP/.dbkey
#     (owner sg, mode 600).  A key already here is never replaced by a different one (game.db would become unreadable,
#     every player's ddraw.dll would stop connecting): the deploy stops here, before any new code is copied.
install_key() {
  [ -f "$1" ] || { echo "!! key $1 was not uploaded"; exit 1; }
  if [ -f "$2" ]; then
    if [ "$(tr -d ' \r\n\t' < "$1")" != "$(tr -d ' \r\n\t' < "$2")" ]; then
      echo "!! $2 on the server differs from the uploaded $(basename "$1") - NOT replaced, deploy stopped"; rm -rf /tmp/sgkeys; exit 1
    fi
  else
    (umask 077; tr -d '\r' < "$1" > "$2"); echo "installed $2"
  fi
  chown sg:sg "$2"; chmod 600 "$2"
}
install_key /tmp/sgkeys/net_key.json "$APP/.netkey"
install_key /tmp/sgkeys/db_key "$APP/.dbkey"
rm -rf /tmp/sgkeys

# 2. new code (runtime data files are not in the package, so they stay as they are)
cp -r "$NEW/server/." "$APP/server/"
cp -r "$NEW/tools/." "$APP/tools/"
cp "$NEW/SG_debug.exe" "$APP/"
[ -f "$APP/server/gm_accounts.json" ] || echo '[]' > "$APP/server/gm_accounts.json"

python3 -m py_compile "$APP/server/sgserver.py" && python3 -m compileall -q "$APP/server/sgs"
chown -R sg:sg "$APP"
chmod 700 "$APP/server" "$APP/deploy-backups"          # player data (game.db) readable by the service user only
chmod 755 "$APP" "$APP/updates"                          # launcher downloads (public files)

# 3. service (auto start at boot, restart after a crash) + log rotation
sed -e "s/@IP@/$IP/g" -e "s/@PORT@/$PORT/g" -e "s/@UPORT@/$UPORT/g" -e "s/@RPORT@/$RPORT/g" "$NEW/deploy/sgserver.service" > /etc/systemd/system/sgserver.service
cat > /etc/logrotate.d/sgserver <<EOF
$APP/logs/*.log $APP/server/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
EOF
# a small swap file protects the 2 GB machine against out-of-memory kills
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
command -v ufw >/dev/null && ufw status | grep -q "Status: active" && ufw allow "$PORT/tcp" >/dev/null && ufw allow "$UPORT/tcp" >/dev/null && ufw allow "$RPORT/udp" >/dev/null || true

systemctl daemon-reload
systemctl enable sgserver >/dev/null 2>&1
OLDPID=$(systemctl show -p MainPID --value sgserver)
if [ "$COUNTDOWN" -gt 0 ] && [ "$OLDPID" != "0" ]; then
  # the running server announces the restart to the players, saves and exits; systemd starts the new code
  echo "{\"seconds\": $COUNTDOWN, \"why\": \"\"}" > "$APP/server/restart_request.json"
  chown sg:sg "$APP/server/restart_request.json"
  echo "waiting for the in-game countdown ($COUNTDOWN s)..."
  for i in $(seq 1 $((COUNTDOWN + 90))); do
    sleep 1
    NOW=$(systemctl show -p MainPID --value sgserver)
    if [ "$NOW" != "$OLDPID" ] && [ "$NOW" != "0" ]; then break; fi
  done
  NOW=$(systemctl show -p MainPID --value sgserver)
  if [ "$NOW" = "$OLDPID" ]; then echo "server did not restart by itself (old version?) -> restarting now"; rm -f "$APP/server/restart_request.json"; systemctl restart sgserver; fi
else
  systemctl restart sgserver
fi
sleep 3
systemctl is-active --quiet sgserver || { journalctl -u sgserver -n 40 --no-pager; exit 1; }
echo "---- sgserver running on $IP:$PORT ----"
tail -n 5 "$APP/logs/sgserver.log"
