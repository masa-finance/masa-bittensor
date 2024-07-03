# Use the official Golang image with version 1.22
FROM golang:1.22

# Set the working directory
WORKDIR /app

# Install necessary tools
RUN apt-get update && apt-get install -y git nodejs npm && \
    npm install -g yarn

# Clone the repository
RUN git clone https://github.com/masa-finance/masa-oracle.git .

# Build the node
RUN go build -v -o masa-node ./cmd/masa-node

# Install contract dependencies
WORKDIR /app/contracts
RUN yarn install

WORKDIR /app

# Copy the entrypoint script
COPY docker/protocol/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose the port
EXPOSE 8081
# 
EXPOSE 4001

# Set the entry point
ENTRYPOINT ["/app/entrypoint.sh"]
