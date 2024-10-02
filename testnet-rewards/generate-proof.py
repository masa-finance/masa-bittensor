import bittensor as bt
import argparse

def generate_proof(): 
    args = argparse.Namespace()
    
    args.hotkey = input("Enter your hotkey: ")
    args.ethaddress = input("Enter your ETH address: ")
    args.name = input("Enter your coldkey name: ")
    
    wallet = bt.wallet(name=args.name)
    keypair = wallet.coldkey

    message = f"{args.ethaddress}"
    signature = keypair.sign(data=message)

    file_contents = f"{message}\n\tSigned by: {keypair.ss58_address}\n\tHotkey: {args.hotkey}\n\tSignature: {signature.hex()}"
    print(file_contents)
    open("message_and_signature.txt", "w").write(file_contents)

    print(f"Signature generated and saved to message_and_signature.txt")
    
    
generate_proof()