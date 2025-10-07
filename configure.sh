#!/bin/bash

# Script to configure Ollama settings for mastrogpt-training

echo "=== MastroGPT Configuration ==="
echo

# Prompt for Ollama Host
echo -n "Enter Ollama Host [default: host.docker.internal:11434]: "
read OLLAMA_HOST
if [ -z "$OLLAMA_HOST" ]; then
    OLLAMA_HOST="host.docker.internal:11434"
fi

# Prompt for Ollama Auth
echo -n "Enter Ollama Auth [default: ignore:me]: "
read OLLAMA_AUTH
if [ -z "$OLLAMA_AUTH" ]; then
    OLLAMA_AUTH="ignore:me"
fi

# Prompt for Ollama Proto
echo -n "Enter Ollama Proto [default: http]: "
read OLLAMA_PROTO
if [ -z "$OLLAMA_PROTO" ]; then
    OLLAMA_PROTO="http"
fi

echo
echo "Configuration summary:"
echo "  OLLAMA_HOST: $OLLAMA_HOST"
echo "  OLLAMA_AUTH: $OLLAMA_AUTH"
echo "  OLLAMA_PROTO: $OLLAMA_PROTO"
echo

# Ask for confirmation
echo -n "Apply these settings? [y/N]: "
read CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "No changes made. Exiting."
    exit 0
fi

# Function to update or add environment variable in a file
update_env_var() {
    local file="$1"
    local var_name="$2"
    local var_value="$3"
    
    if [ ! -f "$file" ]; then
        echo "Warning: $file does not exist, creating it..."
        touch "$file"
    fi
    
    # Check if variable exists in file
    if grep -q "^${var_name}=" "$file"; then
        # Variable exists, update it
        sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" "$file"
        echo "Updated ${var_name} in $file"
    else
        # Variable doesn't exist, add it
        echo "${var_name}=${var_value}" >> "$file"
        echo "Added ${var_name} to $file"
    fi
}

# Update packages/.env
echo
echo "Updating packages/.env..."
update_env_var "packages/.env" "OLLAMA_HOST" "$OLLAMA_HOST"
update_env_var "packages/.env" "OLLAMA_PROTO" "$OLLAMA_PROTO"
update_env_var "packages/.env" "AUTH" "$OLLAMA_AUTH"

# Update tests/.env
echo
echo "Updating tests/.env..."
update_env_var "tests/.env" "OLLAMA_HOST" "$OLLAMA_HOST"
update_env_var "tests/.env" "OLLAMA_PROTO" "$OLLAMA_PROTO"
update_env_var "tests/.env" "AUTH" "$OLLAMA_AUTH"

echo
echo "Configuration completed successfully!"
echo "Files updated:"
echo "  - packages/.env"
echo "  - tests/.env"
