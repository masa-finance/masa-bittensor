#!/bin/bash
set -e

# Set HOME explicitly for cron environment
export HOME=/home/ubuntu

# Get IMDSv2 token (suppress progress)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# Function to retrieve metadata
get_metadata() {
    local metadata_key=$1
    curl -s -f -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/$metadata_key"
}

# Function to retrieve tags
get_tag() {
    local tag_name=$1
    aws ec2 describe-tags --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=$tag_name" --region $REGION --query 'Tags[0].Value' --output text
}

# Function to get current btcli version
get_btcli_version() {
    btcli --version 2>/dev/null | grep -oP 'BTCLI version: \K[0-9]+\.[0-9]+\.[0-9]+' || echo "not found"
}

# Function to get latest btcli version from GitHub
get_latest_btcli_version() {
    curl -s https://api.github.com/repos/opentensor/btcli/releases/latest | grep -oP '"tag_name": "v\K[0-9]+\.[0-9]+\.[0-9]+' || echo "not found"
}

# Function to install or update btcli
install_btcli() {
    # Activate virtual environment first
    source $HOME/masa-bittensor/venv/bin/activate || {
        echo "Error: Could not activate virtual environment"
        return 1
    }

    echo "Checking btcli version..."
    current_version=$(get_btcli_version)
    echo "Current btcli version: '$current_version'"
    
    echo "Checking latest version..."
    latest_version=$(get_latest_btcli_version)
    echo "Latest btcli version: $latest_version"
    
    if [ "$current_version" != "$latest_version" ] && [ "$latest_version" != "not found" ]; then
        echo "Installing latest btcli version..."
        pip uninstall -y bittensor-cli
        pip install --no-deps "bittensor-cli==$latest_version"
        echo "btcli has been updated to version $latest_version"
    else
        echo "btcli is already at the latest version ($current_version)"
    fi
    
    echo "btcli check completed"
    
    # Deactivate virtual environment
    deactivate
}

# Set environment variables
echo "Getting AWS metadata..."
REGION=$(get_metadata "placement/region") || {
    echo "Error getting region metadata"
    exit 1
}
echo "Region: $REGION"

INSTANCE_ID=$(get_metadata "instance-id") || {
    echo "Error getting instance ID metadata"
    exit 1
}
echo "Instance ID: $INSTANCE_ID"

echo "=== Checking btcli ==="
install_btcli || true  # Don't let btcli issues stop the script

echo -e "\n=== Checking masa-bittensor ==="
# Change to the masa-bittensor directory using absolute path
cd $HOME/masa-bittensor || {
    echo "Error: Could not change to masa-bittensor directory"
    exit 1
}
echo "Changed to directory: $(pwd)"

# Store current commit hash
current_commit=$(git rev-parse HEAD)
current_branch=$(git rev-parse --abbrev-ref HEAD)
echo "Current state before update:"
echo "  Branch: ${current_branch}"
echo "  Commit: ${current_commit:0:8}"

# Get desired version from metadata
desired_version=$(get_tag "MASA_BITTENSOR_VERSION")
echo "Checking EC2 tag MASA_BITTENSOR_VERSION: '$desired_version'"

if [ -z "$desired_version" ] || [ "$desired_version" == "None" ]; then
    echo "No specific version tag found, defaulting to 'latest'"
    desired_version="latest"
fi

# Fetch all updates from remote
echo "Fetching updates from remote..."
git fetch origin --tags --force
echo "Remote updates fetched"

# Determine target reference and commit
if [ "$desired_version" == "latest" ]; then
    target_ref="origin/main"
    if ! target_commit=$(git rev-parse origin/main 2>/dev/null); then
        echo "Error: Could not get latest main branch commit"
        exit 1
    fi
    echo "Using latest main branch version:"
    echo "  Target commit: ${target_commit:0:8}"
else
    # First check for branch
    if git rev-parse --verify "origin/$desired_version" >/dev/null 2>&1; then
        target_ref="origin/$desired_version"
        target_commit=$(git rev-parse "origin/$desired_version")
        echo "Found branch '$desired_version':"
        echo "  Remote branch hash: ${target_commit:0:8}"
    # Then check for tag
    elif git rev-parse --verify "refs/tags/$desired_version" >/dev/null 2>&1; then
        target_ref="refs/tags/$desired_version"
        target_commit=$(git rev-parse "refs/tags/$desired_version")
        echo "Found tag '$desired_version':"
        echo "  Tag hash: ${target_commit:0:8}"
    else
        echo "Error: Version '$desired_version' not found as branch or tag"
        echo "Available branches:"
        git branch -r
        echo "Available tags:"
        git tag
        exit 1
    fi
fi

# Compare current and target commits
echo -e "\nComparing versions:"
echo "  Current: ${current_commit:0:8} (${current_branch})"
echo "  Target:  ${target_commit:0:8} ($desired_version)"

if [ "$current_commit" == "$target_commit" ]; then
    echo "Already at latest version for $desired_version"
    exit 0
fi

echo -e "\nUpdates available - proceeding with update..."

# Reset any local changes and checkout target
echo "Resetting to target version..."
git reset --hard "$target_ref"
git clean -fd

# Update dependencies
echo "Installing dependencies..."
source $HOME/masa-bittensor/venv/bin/activate
pip install -e .

# Restart the validator service
echo "Restarting masa-validator service..."
sudo systemctl restart masa-validator

# Update version file with new commit hash
echo "$target_commit" > $HOME/.masa-bittensor-version

echo -e "\nUpdate completed successfully:"
echo "  Version: $desired_version"
echo "  Commit:  ${target_commit:0:8}"
