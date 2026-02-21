#!/bin/bash

# Script to create a new user user-001 with the same desktop configuration as x92120

# 1. Create group 'user' if it doesn't already exist
if ! getent group user > /dev/null; then
    sudo groupadd user
    echo "Group 'user' created."
fi

# 2. Create user 'user-001'
if id "user-001" &>/dev/null; then
    echo "User 'user-001' already exists."
else
    sudo useradd -m -s /bin/bash -g user user-001
    echo "User 'user-001' created."
fi

# 3. Set the password
echo "user-001:mitrphol100x" | sudo chpasswd
echo "Password set for user-001."

# 4. Copy desktop configuration from x92120 to user-001
echo "Copying desktop configuration from x92120..."
FOLDERS_TO_COPY=(".config" ".local" ".bashrc" ".profile")

for item in "${FOLDERS_TO_COPY[@]}"; do
    if [ -e "/home/x92120/$item" ]; then
        sudo cp -rp "/home/x92120/$item" "/home/user-001/"
    fi
done

# 5. Fix ownership of the home directory
sudo chown -R user-001:user /home/user-001/
echo "Ownership fixed for /home/user-001/."

echo "--------------------------------------------------"
echo "User user-001 creation and configuration complete."
echo "--------------------------------------------------"
