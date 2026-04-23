# Deployment Runbook

VM: Oracle Cloud Free Tier (AMD E2.1.Micro, Ubuntu 22.04, Frankfurt)
Public IP: `130.162.230.238`
SSH: `ssh -i "/c/Users/Tim/.ssh/ssh-key-2026-04-22.key" ubuntu@130.162.230.238`
Domain: `https://bot.random-class.de` (via Cloudflare Tunnel)

## Dienste (systemd)

| Service | Zweck | Auto-Start |
|---|---|---|
| `discord-bot` | Der Bot selbst | Nein (nur ueber Panel) |
| `bot-panel` | Flask Web-Panel auf Port 8080 | Ja |
| `cloudflared` | Cloudflare Tunnel nach `bot.random-class.de` | Ja |

**Status pruefen:**
```bash
sudo systemctl status discord-bot
sudo systemctl status bot-panel
sudo systemctl status cloudflared
```

**Logs:**
```bash
sudo journalctl -u discord-bot -n 50 --no-pager
sudo journalctl -u bot-panel -n 50 --no-pager
sudo journalctl -u cloudflared -n 50 --no-pager
```

## Code-Updates

### Bot-Code (aus GitHub pullen)

```bash
cd /home/ubuntu/discordRandomClass
git pull
sudo systemctl restart discord-bot
```

Neue Python-Dependencies? Dann vor dem Restart:
```bash
source venv/bin/activate
pip install <paket>
```

### Flask-Panel (app.py)

Direkt auf der VM:
```bash
nano /home/ubuntu/bot-panel/app.py
sudo systemctl restart bot-panel
```

### Cloudflare Tunnel Config

```bash
sudo nano /etc/cloudflared/config.yml
sudo systemctl restart cloudflared
```

## Oracle Cloud Security List

Ingress-Rule hinzufuegen/entfernen (z.B. Port 8080 temporaer oeffnen):

1. Console → **Networking** → **Virtual Cloud Networks** → `bot-vcn`
2. Resources → **Security Lists** → `Default Security List for bot-vcn`
3. **Add Ingress Rules**:
   - Source Type: `CIDR`
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: `TCP`
   - Source Port Range: leer
   - Destination Port Range: `8080` (oder was benoetigt)
   - Description: z.B. `Bot Panel temp`
4. **Add Ingress Rules** klicken

Zum Entfernen: Drei-Punkte-Menue bei der Rule → **Remove**.

## Temporaer IP:8080 oeffnen / schliessen

Wenn der Tunnel/die Domain mal nicht geht, kannst du per IP aufs Panel:

**Oeffnen:**
```bash
sudo iptables -I INPUT 1 -p tcp --dport 8080 -j ACCEPT
sudo netfilter-persistent save
```
+ in Oracle Security List Port 8080 Ingress-Rule wieder anlegen (siehe oben).

Panel dann unter `http://130.162.230.238:8080` erreichbar.

**Schliessen:**
```bash
sudo iptables -D INPUT -p tcp --dport 8080 -j ACCEPT
sudo netfilter-persistent save
```
+ in Oracle Security List die Ingress-Rule fuer Port 8080 wieder loeschen.

## Bot-Token aendern

```bash
nano /home/ubuntu/discordRandomClass/.env
sudo systemctl restart discord-bot
```

## Panel-Passwort aendern

```bash
nano /home/ubuntu/bot-panel/.env
sudo systemctl restart bot-panel
```

## DNS-Status (nach Domain-Aenderungen)

```bash
# Auf dem lokalen PC (PowerShell):
nslookup bot.random-class.de 1.1.1.1
```

Online-Check: https://dnschecker.org/#CNAME/bot.random-class.de

## Reboot

VM reboot (Bot-Panel + cloudflared starten auto):
```bash
sudo reboot
```
`discord-bot` startet bewusst **nicht** automatisch - das muss immer ueber das Panel oder manuell passieren.

## Pfade auf der VM (Referenz)

| Was | Pfad |
|---|---|
| Bot-Code | `/home/ubuntu/discordRandomClass/` |
| Bot venv | `/home/ubuntu/discordRandomClass/venv/` |
| Bot `.env` (Discord Token) | `/home/ubuntu/discordRandomClass/.env` |
| Panel-Code | `/home/ubuntu/bot-panel/app.py` |
| Panel `.env` (PANEL_PASSWORD) | `/home/ubuntu/bot-panel/.env` |
| Cloudflare Config | `/etc/cloudflared/config.yml` |
| Cloudflare Credentials | `/etc/cloudflared/<tunnel-id>.json` |
| systemd Units | `/etc/systemd/system/discord-bot.service` etc. |
| Sudoers fuer Panel | `/etc/sudoers.d/bot-panel` |
