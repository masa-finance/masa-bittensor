# Guide to Verify Your Key Ownership

## Step 1: Generate the Proof

1. **Clone the Repository**: Start by cloning our company's GitHub repository to access the necessary scripts.
    ```bash
    git clone https://github.com/masa-finance/masa-bittensor/tree/feature/verify-tao-signature
    ```

2. **Navigate to the Directory**: Change your directory to where the `generate-proof.py` script is located.
    ```bash
    cd <repository-directory>/testnet-rewards
    ```

3. **Run the Script**: Execute the `generate-proof.py` script. You will be prompted to enter your hotkey, Ethereum address, and coldkey name ( This cold key HAS to be associated with the submited hotkey ). Make sure to enter these details accurately.
    ```bash
    python generate-proof.py
    ```

    - **Example Input:**
        - Enter your hotkey: `YourHotkey`
        - Enter your ETH address: `YourEthereumAddress`
        - Enter your coldkey name: `YourColdkeyName`
        - Enter password to unlock key: `[YourColdKeyPassword]`

    - **Output:** This will generate a signature and save it to a file named `message_and_signature.txt`.

4. **Send the Proof File**: Once the script has generated the proof, send the `message_and_signature.txt` file to us via Discord or email.

---

Please ensure that the information you provide when running the script is accurate, as this will be used to validate your key ownership. If you encounter any issues, don’t hesitate to reach out for assistance!
