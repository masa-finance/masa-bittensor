
from substrateinterface import Keypair
from binascii import unhexlify
import argparse
import bittensor as bt

subtensor = "ws://100.28.51.29:9945"

 
def verify_proof():
    
    args = argparse.Namespace()
    args.file = input("Enter file name: ")
    
    file_data = open(args.file).read()
    file_split = file_data.split("\n\t")

    address_line = file_split[1]
    address_prefix = "Signed by: "
    if address_line.startswith(address_prefix):
        address = address_line[len(address_prefix) :]
    else:
        address = address_line

    keypair = Keypair(ss58_address=address, ss58_format=42)

    message = file_split[0]

    signature_line = file_split[3]
    signature_prefix = "Signature: "
    if signature_line.startswith(signature_prefix):
        signature = signature_line[len(signature_prefix) :]
    else:
        signature = signature_line

    real_signature = unhexlify(signature.encode())

    if not keypair.verify(data=message, signature=real_signature):
        raise ValueError(f"Invalid signature for address={address}")
    else:
        subtensor_network = bt.subtensor(subtensor)
        hotkey_line = file_split[2]
        hotkey_prefix = "Hotkey: "
        if hotkey_line.startswith(hotkey_prefix):
            hotkey = hotkey_line[len(hotkey_prefix) :]
        else:
            hotkey = hotkey_line
        try:
            coldkey = subtensor_network.get_hotkey_owner(hotkey)
                
            if coldkey == address:
                print(f"Signature verified, signed by {address}")
            else:
                print("Invalid address: Coldkey doesn't own this hotkey")
        except Exception as e:
            print(f"Error retrieving coldkey owner for hotkey {hotkey}: {e}")
            return
        
   
            
verify_proof()