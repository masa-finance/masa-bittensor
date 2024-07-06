import bittensor as bt
from typing import Union, Optional
from fastapi import FastAPI
import socket
import os
import nest_asyncio
import httpx
import requests
import threading
import asyncio

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

from masa.base.healthcheck import PingMiner


axons_cache = []

def get_external_ip() -> str:
    """
    Fetches the external IP address of the machine.

    Returns:
        str: The external IP address.
    """
    try:
        response = requests.get('https://api.ipify.org?format=json')
        response.raise_for_status()
        ip = response.json().get('ip')
        return ip
    except requests.RequestException as e:
        print(f"An error occurred while fetching the external IP: {e}")
        return None

external_ip = get_external_ip()
print(f"External IP: {external_ip}")


nest_asyncio.apply()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    

async def check_axon_health(axon):
    """
    Sends a GET request to the axon's health check endpoint.

    Args:
        axon (dict): A dictionary containing axon details including 'ip' and 'port'.

    Returns:
        bool: True if the axon is healthy, False otherwise.
    """
    url = f"http://{axon.ip}:8000/healthcheck"
    
    if(axon.ip == external_ip):
        url = f"http://localhost:8000/healthcheck"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                response_data = response.json()
                hotkey = response_data.get('hotkey')
                return hotkey
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}.")
    return False


async def get_axon_health_status(uids: list, metagraph) -> dict:
    """
    Checks the health status of axons corresponding to the given UIDs.

    Args:
        uids (list): A list of UIDs (unique identifiers) to check.
        metagraph (bittensor.metagraph): The metagraph instance containing network information.

    Returns:
        dict: A dictionary with UIDs as keys and their health status (True for healthy, False for unhealthy) as values.
    """
    axons = [metagraph.axons[uid] for uid in uids]
    health_status = {}

    for axon, uid in zip(axons, uids):
        axon_hotkey = await check_axon_health(axon)
        is_healthy = axon.hotkey == axon_hotkey
        health_status[uid] = is_healthy

    return [uid for uid, is_healthy in health_status.items() if is_healthy]



async def ping_uids(dendrite, metagraph, uids, timeout=3):
    """
    Pings a list of UIDs to check their availability on the Bittensor network.

    Args:
        dendrite (bittensor.dendrite): The dendrite instance to use for pinging nodes.
        metagraph (bittensor.metagraph): The metagraph instance containing network information.
        uids (list): A list of UIDs (unique identifiers) to ping.
        timeout (int, optional): The timeout in seconds for each ping. Defaults to 3.

    Returns:
        tuple: A tuple containing two lists:
            - The first list contains UIDs that were successfully pinged.
            - The second list contains UIDs that failed to respond.
    """
    axons = [metagraph.axons[uid] for uid in uids]
    try:
        request = PingMiner(sent_from=external_ip,  is_active=False)
        responses = await dendrite(
            axons,
            request,
            deserialize=False,
            
            # timeout=timeout,
        )
        
        print("RESSPONSES")
        print(responses)
        for response in responses:
            response_index = responses.index(response)
            corresponding_axon = axons[response_index]
            
            print("---------------------------------------------------")
            print(f"status code: {response.dendrite.status_code}")
            print(f"Is Axon serving: {corresponding_axon.is_serving}")
            
            
            if(corresponding_axon.ip == "179.24.204.155"):
                print(f"THIS IS LOCAL *** {corresponding_axon.ip}")
                print(response)
            if(response.dendrite.status_code == 404):
                print(f"AXON UID: {response_index}")
                print(corresponding_axon)

            
            if(response.dendrite.status_code < 400):
                print(f"AXON UID: {response_index}")
                print(corresponding_axon)
            print("-----------------------------------------------------")
        successful_uids = [
            uid
            for uid, response in zip(uids, responses)
            if response.is_active
        ]
        failed_uids = [
            uid
            for uid, response in zip(uids, responses)
            if response.dendrite.status_code != 200
        ]
    except Exception as e:
        bt.logging.error(f"Dendrite ping failed: {e}")
        successful_uids = []
        failed_uids = uids
    bt.logging.debug(f"ping() successful uids: {successful_uids}")
    bt.logging.debug(f"ping() failed uids    : {failed_uids}")
    return successful_uids, failed_uids



async def get_axons(subnet: int):
    subnet = bt.metagraph(subnet, "ws://54.205.45.3:9945", lite = False)  
    subnet.sync()
    min_tao_required_for_vpermit = 10

    axons = [
        {
            "version": axon.version,
            "ip": axon.ip,
            "port": axon.port,
            "ip_type": axon.ip_type,
            "hotkey": axon.hotkey,
            "coldkey": axon.coldkey,
            "protocol": axon.protocol,
            "placeholder1": axon.placeholder1,
            "placeholder2": axon.placeholder2,
            "status": "",
            "staked_amount": 0,
            "uid": None,
            "vpermit": False
        } for axon in subnet.axons
    ]
   
    uids = subnet.uids.tolist()
    stakes = subnet.S
    
    connected_axons = []

       
    
    # It seems like you're trying to iterate over a numpy.float32 object which is not iterable.
    # You might need to check the data type of 'stakes' before iterating over it.
    # If 'stakes' is supposed to be a list of numpy.float32, you can iterate over it.
    # If 'stakes' is just a single numpy.float32 value, you cannot iterate over it.
    # Here is a simple check you can do:

    
  
        # if(stake > min_tao_required_for_vpermit):
        #     axon["vpermit"] = True
        
    for axon, uid in zip(axons, uids):
        axon["uid"] = uid
        
        stake = stakes.tolist()[uid]
        print(stake)
        
        axon["staked_amount"] = stake
        if(stake > min_tao_required_for_vpermit):
            axon["vpermit"] = True
            
            
    validators_uids = [uid for axon, uid in zip(axons, uids) if axon["vpermit"]]
    miner_uids = [uid for axon, uid in zip(axons, uids) if not axon["vpermit"]]
    wallet = bt.wallet("validator")
    dendrite = bt.dendrite(wallet=wallet)
    
    try:

        healthy_miners, _ = await ping_uids(dendrite, subnet, miner_uids)
        
        healthy_validators = await get_axon_health_status(validators_uids, subnet)
    
        connected_axons = healthy_miners + healthy_validators

    except Exception as e:
        bt.logging.error(message=f"Failed to get random miner uids: {e}")
        return None
    finally:
        # dendrite.close_session()
        print("FINISHED")
        
        
    for axon in axons:
        if axon["uid"] in connected_axons:
            axon["status"] = "connected"
        else:
            axon["status"] = "disconnected"
            
    global axons_cache
            
    axons_cache = axons
    
    




async def periodic_axons_update():
    while True:
        await get_axons(subnet=1)  # Replace '1' with the appropriate subnet value if needed
        await asyncio.sleep(10)


def start_periodic_update():
    asyncio.run(periodic_axons_update())

update_thread = threading.Thread(target=start_periodic_update)
update_thread.start()


@app.get("/axons/{subnet}")
async def get_axons_rest():
    return { "axons": axons_cache }

@app.post("/axon/call/{uid}")
async def call_axon(uid: int, request: Request):
    """
    Calls a specific method on the axon identified by the given UID.

    Args:
        uid (int): The UID of the axon.
        request (Request): The incoming request object containing method, path, body, etc.

    Returns:
        Response: The response from the axon.
    """
    # Find the axon with the given UID
    axon = next((axon for axon in axons_cache if axon["uid"] == uid), None)
    
    if not axon:
        return JSONResponse(status_code=404, content={"message": "Axon not found"})

    # Validate that the axon is connected
    if axon["status"] != "connected":
        return JSONResponse(status_code=400, content={"message": "Axon is not connected"})
    
    # Extract method, path, and body from the request
    request_data = await request.json()
    method = request_data.get("method")
    path = request_data.get("path")
    body = request_data.get("body", {})

    if not method or not path:
        return JSONResponse(status_code=400, content={"message": "Method and path are required"})
    
    
    # Construct the URL
    url = f"http://{axon['ip']}:8000/{path}"
    
    if axon['ip'] == external_ip:
        url = f"http://localhost:8000/{path}"
        
    print(f"IP: {axon['ip']}")
    print(f"path: {path}")
    print(f"method: {method}")
    print(f"URL: {url}")
    
    
    # Forward the request to the axon
    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            response = await client.get(url, params=body)
        elif method.upper() == "POST":
            response = await client.post(url, json=body)
        elif method.upper() == "PUT":
            response = await client.put(url, json=body)
        elif method.upper() == "DELETE":
            response = await client.delete(url, json=body)
        elif method.upper() == "PATCH":
            response = await client.patch(url, json=body)
        else:
            return JSONResponse(status_code=405, content={"message": "Method not allowed"})
        
    print(f"RESPONSE: {response.status_code}")
    
    return JSONResponse(status_code=response.status_code, content=response.json())
