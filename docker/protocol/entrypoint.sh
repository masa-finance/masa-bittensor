#!/bin/bash

# Create .env file
cat << EOF > /app/.env
BOOTNODES=/ip4/35.223.224.220/udp/4001/quic-v1/p2p/16Uiu2HAmPxXXjR1XJEwckh6q1UStheMmGaGe8fyXdeRs3SejadSa,/ip4/34.121.111.128/udp/4001/quic-v1/p2p/16Uiu2HAmKULCxKgiQn1EcfKnq1Qam6psYLDTM99XsZFhr57wLadF

API_KEY=${API_KEY:-}
RPC_URL=${RPC_URL:-https://ethereum-sepolia.publicnode.com}
ENV=${ENV:-test}
FILE_PATH=${FILE_PATH:-.}
VALIDATOR=${VALIDATOR:-false}
PORT=${PORT:-8081}

# AI LLM
CLAUDE_API_KEY=${CLAUDE_API_KEY:-}
CLAUDE_API_URL=${CLAUDE_API_URL:-https://api.anthropic.com/v1/messages}
CLAUDE_API_VERSION=${CLAUDE_API_VERSION:-2023-06-01}
ELAB_URL=${ELAB_URL:-https://api.elevenlabs.io/v1/text-to-speech/ErXwobaYiN019PkySvjV/stream}
ELAB_KEY=${ELAB_KEY:-}
OPENAI_API_KEY=${OPENAI_API_KEY:-}
PROMPT=${PROMPT:-"You are a helpful assistant."}

# X
TWITTER_USER=${TWITTER_USER:-}
TWITTER_PASS=${TWITTER_PASS:-}
TWITTER_2FA_CODE=${TWITTER_2FA_CODE:-}

# Worker node config
TWITTER_SCRAPER=${TWITTER_SCRAPER:-true}
DISCORD_SCRAPER=${DISCORD_SCRAPER:-true}
WEB_SCRAPER=${WEB_SCRAPER:-true}
EOF

# Start the node
if [ "$STAKE_AMOUNT" != "" ]; then
    echo "Staking $STAKE_AMOUNT MASA tokens..."
    ./masa-node --stake $STAKE_AMOUNT
    echo "Staking completed. Restarting node..."
fi

./masa-node &

# Keep the container running
tail -f /dev/null
