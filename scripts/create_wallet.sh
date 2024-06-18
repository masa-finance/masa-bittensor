services:
  subnet:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: subnet_machine
    volumes:
      - ./scripts/localnet.sh:/usr/local/bin/localnet.sh
    ports:
      - "9945:9945"  # Expose port 9945
      - "9946:9946"  # Expose port 9946
      - "30334:30334"  # Expose internal communication port
      - "30335:30335"  # Expose internal communication port
    networks:
      - subnet_network

  control:
    build:
      context: .
      dockerfile: Dockerfile.control
    container_name: control_machine
    depends_on:
      - subnet
    networks:
      - subnet_network
    environment:
      - COLDKEY_PASSWORD=your_coldkey_password
      - HOTKEY_PASSWORD=your_hotkey_password

networks:
  subnet_network:
    driver: bridge
