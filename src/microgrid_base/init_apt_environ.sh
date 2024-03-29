#!/bin/bash

function install_packages {
  # Install the packages
  apt install -y redis rabbitmq-server tmux tmuxp openjdk-8-jdk htop swi-prolog

  # courtesy from ChatGPT
  local status=$?
  # Return the exit status
  return $status
}

install_packages
# Check the status of the package installation
if [ $? -ne 0 ]; then
# If the installation failed, run apt update and try again
echo "Package installation failed. Running apt update and trying again..."
apt update
install_packages
fi
