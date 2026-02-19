#!/bin/bash
# Setup script: Apply desktop defaults for all users + autostart for x_user_001
# Run with: sudo bash setup-desktop-defaults.sh

set -e

echo "=== Part 1: System-wide dconf desktop defaults ==="

# 1. Create dconf profile
mkdir -p /etc/dconf/profile
cat > /etc/dconf/profile/user << 'PROFILE'
user-db:user
system-db:local
PROFILE
echo "✅ Created /etc/dconf/profile/user"

# 2. Create system-wide defaults database
mkdir -p /etc/dconf/db/local.d
cat > /etc/dconf/db/local.d/01-desktop-defaults << 'DCONF'
[org/gnome/desktop/interface]
gtk-theme='Yaru-blue'
icon-theme='Yaru-blue'
color-scheme='default'

[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/Clouds_by_Tibor_Mokanszki.jpg'
picture-uri-dark='file:///usr/share/backgrounds/Clouds_by_Tibor_Mokanszki.jpg'
picture-options='zoom'
primary-color='#000000'
secondary-color='#000000'
color-shading-type='solid'

[org/gnome/desktop/screensaver]
picture-uri='file:///usr/share/backgrounds/Clouds_by_Tibor_Mokanszki.jpg'
picture-options='zoom'
primary-color='#000000'
secondary-color='#000000'
color-shading-type='solid'

[org/gnome/desktop/input-sources]
sources=[('xkb', 'us'), ('xkb', 'th')]
per-window=false

[org/gnome/desktop/wm/keybindings]
switch-input-source=['grave']
switch-input-source-backward=['<Shift>grave']

[org/gnome/desktop/peripherals/keyboard]
numlock-state=true

[org/gnome/shell]
favorite-apps=['firefox_firefox.desktop', 'antigravity.desktop', 'google-chrome.desktop', 'thunderbird_thunderbird.desktop', 'org.gnome.Nautilus.desktop', 'org.gnome.Rhythmbox3.desktop', 'libreoffice-writer.desktop', 'snap-store_snap-store.desktop', 'yelp.desktop', 'org.gnome.Terminal.desktop']

[org/gnome/shell/extensions/dash-to-dock]
dock-position='BOTTOM'
show-apps-at-top=true
DCONF
echo "✅ Created /etc/dconf/db/local.d/01-desktop-defaults"

# 3. Compile dconf database
dconf update
echo "✅ Ran dconf update"

echo ""
echo "=== Part 2: Apply settings to existing user x_user_001 ==="

# Load the same settings into x_user_001's user database
sudo -u x_user_001 dbus-launch dconf load / << 'USERCONF'
[org/gnome/desktop/interface]
gtk-theme='Yaru-blue'
icon-theme='Yaru-blue'
color-scheme='default'

[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/Clouds_by_Tibor_Mokanszki.jpg'
picture-uri-dark='file:///usr/share/backgrounds/Clouds_by_Tibor_Mokanszki.jpg'
picture-options='zoom'
primary-color='#000000'
secondary-color='#000000'
color-shading-type='solid'

[org/gnome/desktop/screensaver]
picture-uri='file:///usr/share/backgrounds/Clouds_by_Tibor_Mokanszki.jpg'
picture-options='zoom'
primary-color='#000000'
secondary-color='#000000'
color-shading-type='solid'

[org/gnome/desktop/input-sources]
sources=[('xkb', 'us'), ('xkb', 'th')]
per-window=false

[org/gnome/desktop/wm/keybindings]
switch-input-source=['grave']
switch-input-source-backward=['<Shift>grave']

[org/gnome/desktop/peripherals/keyboard]
numlock-state=true

[org/gnome/shell]
favorite-apps=['firefox_firefox.desktop', 'antigravity.desktop', 'google-chrome.desktop', 'thunderbird_thunderbird.desktop', 'org.gnome.Nautilus.desktop', 'org.gnome.Rhythmbox3.desktop', 'libreoffice-writer.desktop', 'snap-store_snap-store.desktop', 'yelp.desktop', 'org.gnome.Terminal.desktop']

[org/gnome/shell/extensions/dash-to-dock]
dock-position='BOTTOM'
show-apps-at-top=true
USERCONF
echo "✅ Applied settings to x_user_001"

echo ""
echo "=== Part 3: Port forward 80 → 3000 ==="

# Redirect port 80 to 3000 so frontend is accessible without :3000
iptables -t nat -C PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3000 2>/dev/null || \
  iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3000
iptables -t nat -C OUTPUT -o lo -p tcp --dport 80 -j REDIRECT --to-port 3000 2>/dev/null || \
  iptables -t nat -A OUTPUT -o lo -p tcp --dport 80 -j REDIRECT --to-port 3000
echo "✅ Port 80 → 3000 redirect active"

# Persist iptables rules across reboots
if command -v netfilter-persistent &> /dev/null; then
  netfilter-persistent save
  echo "✅ iptables rules saved (netfilter-persistent)"
else
  echo "⚠️  Installing iptables-persistent to save rules across reboots..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent > /dev/null 2>&1
  netfilter-persistent save
  echo "✅ iptables-persistent installed and rules saved"
fi

echo ""
echo "=== Part 4: Autostart Chrome to frontend for x_user_001 ==="

# Create autostart directory and .desktop file
mkdir -p /home/x_user_001/.config/autostart
cat > /home/x_user_001/.config/autostart/xmixing-frontend.desktop << 'AUTOSTART'
[Desktop Entry]
Type=Application
Name=xMixing Frontend
Exec=google-chrome --start-fullscreen http://x_mixing_control
X-GNOME-Autostart-enabled=true
AUTOSTART

chown -R x_user_001:x_user_001 /home/x_user_001/.config/autostart
echo "✅ Created autostart entry for x_user_001 → http://x_mixing_control"

echo ""
echo "================================================"
echo "✅ All done! Summary:"
echo "  • System-wide desktop defaults applied"
echo "  • x_user_001 settings updated"
echo "  • Port 80 → 3000 redirect (persistent)"
echo "  • x_user_001 will auto-open Chrome to http://x_mixing_control on login"
echo "================================================"
