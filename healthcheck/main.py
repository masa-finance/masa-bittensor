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
import asyncpg

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from cachetools import TTLCache


from masa.base.healthcheck import PingMiner

nest_asyncio.apply()
app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://bittensor-test-tool.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

axons_cache = []
subtensor = "ws://100.28.51.29:9945"

# Create a cache with a TTL of 60 seconds
leaderboard_cache = TTLCache(maxsize=100, ttl=60*5)


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

async def store_uptime_report(axon_pk: int, status: str):
    """
    Store uptime report in the uptime table.

    Parameters:
    axon_pk (int): Primary key of the axon.
    status (str): Status of the axon (connected/disconnected).
    """


    # Get the current timestamp in UTC
    timestamp = datetime.now()
    
    db_connection = await asyncpg.connect(os.getenv("POSTGRES_URL"))
    

    # Assuming you have a database connection and a cursor
    # Replace `db_connection` and `db_cursor` with your actual database connection and cursor

    await db_connection.execute('''
        CREATE TABLE IF NOT EXISTS uptime (
            pk TEXT,
            status TEXT,
            timestamp TIMESTAMP
        )
    ''')
    
    # Ensure the timestamp is timezone-aware before inserting into the database

    await db_connection.execute('''
        INSERT INTO uptime (pk, timestamp, status) VALUES($1, $2, $3)
    ''', axon_pk, timestamp, status)

    # Close the cursor and connection
    await db_connection.close()


async def get_connected_axons_by_ip(ip: str, subnet_id: int):
    """
    Given an IP address, get all the connected axons.

    Parameters:
    ip (str): The IP address to filter axons.
    subnet_id (int): The subnet ID to query.

    Returns:
    List[dict]: A list of connected axons with the given IP address.
    """
    subnet = bt.metagraph(subnet_id, subtensor, lite=False)
    subnet.sync()

    axons = [
        {
            "version": axon.version,
            "ip": axon.ip,
            "port": axon.port,
            "ip_type": axon.ip_type,
            "hotkey": axon.hotkey,
            "coldkey": axon.coldkey,
            "protocol": axon.protocol,
            "status": "",
            "staked_amount": 0,
            "uid": None,
            "vpermit": False
        } for axon in subnet.axons
    ]

    uids = subnet.uids.tolist()
    stakes = subnet.S

    connected_axons = []

    for axon, uid in zip(axons, uids):
        axon["uid"] = uid

        stake = stakes.tolist()[uid]
        axon["staked_amount"] = stake
        if stake > 10:  # Assuming 10 is the min_tao_required_for_vpermit
            axon["vpermit"] = True

        connected_axons.append(axon)

    dividends = subnet.dividends.tolist()
    incentive = subnet.incentive.tolist()
    last_update = subnet.last_update.tolist()
    trust = subnet.trust.tolist()

    for axon, uid in zip(connected_axons, uids):
        axon["dividends"] = dividends[uid]
        axon["incentive"] = incentive[uid]
        axon["last_update"] = last_update[uid]
        axon["trust"] = trust[uid]
        
    # Filter out connected_axons that have a different IP
    connected_axons = [axon for axon in connected_axons if axon["ip"] == ip]
        
    validators_uids = [axon["uid"] for axon in connected_axons if axon["vpermit"]]
    miner_uids = [axon["uid"] for axon in connected_axons if not axon["vpermit"]]
    
    
    print(connected_axons)
    print(f"validators_uids: {validators_uids}")
    print(f"miners_uids: {miner_uids}")
    wallet = bt.wallet("validator")
    dendrite = bt.dendrite(wallet=wallet)

    healthy_unhealthy_validators = []
    try:
        healthy_miners, _ = await ping_uids(dendrite, subnet, miner_uids)
        healthy_validators = await get_axon_health_status(validators_uids, subnet)
        unhealthy_validators = [uid for uid in validators_uids if uid not in healthy_validators]
        if unhealthy_validators:
            healthy_unhealthy_validators, _ = await ping_uids(dendrite, subnet, unhealthy_validators)
            healthy_validators.extend(healthy_unhealthy_validators)
        connected_axon_uids = healthy_miners + healthy_validators
    except Exception as e:
        bt.logging.error(message=f"Failed to get random miner uids: {e}")
        return None
    finally:
        print("FINISHED")
        
    for axon in connected_axons:
        if axon["uid"] in healthy_unhealthy_validators:
            axon["vpermit"] = False
            
    connected_axons = [axon for axon in connected_axons if axon["uid"] in connected_axon_uids]
    
    for axon in connected_axons:
        axon["status"] = "connected"

    return connected_axons


async def get_axons(subnet_id: int):
    subnet = bt.metagraph(subnet_id, subtensor, lite=False)
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
            "status": "",
            "staked_amount": 0,
            "uid": None,
            "vpermit": False
        } for axon in subnet.axons
    ]

    uids = subnet.uids.tolist()
    stakes = subnet.S

    connected_axons = []

    for axon, uid in zip(axons, uids):
        axon["uid"] = uid

        stake = stakes.tolist()[uid]
        print(stake)

        axon["staked_amount"] = stake
        if stake > min_tao_required_for_vpermit:
            axon["vpermit"] = True
            
    dividends = subnet.dividends.tolist()
    incentive = subnet.incentive.tolist()
    last_update = subnet.last_update.tolist()
    trust = subnet.trust.tolist()

    for axon, uid in zip(axons, uids):
        axon["dividends"] = dividends[uid]
        axon["incentive"] = incentive[uid]
        axon["last_update"] = last_update[uid]
        axon["trust"] = trust[uid]

    validators_uids = [uid for axon, uid in zip(axons, uids) if axon["vpermit"]]
    miner_uids = [uid for axon, uid in zip(axons, uids) if not axon["vpermit"]]
    wallet = bt.wallet("validator")
    dendrite = bt.dendrite(wallet=wallet)
    healthy_unhealthy_validators = []
    try:
        healthy_miners, _ = await ping_uids(dendrite, subnet, miner_uids)
        healthy_validators = await get_axon_health_status(validators_uids, subnet)
        unhealthy_validators = [uid for uid in validators_uids if uid not in healthy_validators]
        if unhealthy_validators:
            healthy_unhealthy_validators, _ = await ping_uids(dendrite, subnet, unhealthy_validators)
            healthy_validators.extend(healthy_unhealthy_validators)
        connected_axons = healthy_miners + healthy_validators
    except Exception as e:
        bt.logging.error(message=f"Failed to get random miner uids: {e}")
        return None
    finally:
        print("FINISHED")
        
        

    for axon in axons:
        if axon["uid"] in connected_axons:
            axon["status"] = "connected"
            if axon["uid"] in healthy_unhealthy_validators:
                axon["vpermit"] = False
                
        else:
            axon["status"] = "disconnected"

    global axons_cache
    axons_cache = axons



    # Store or update axons in the database
    conn = await asyncpg.connect(os.getenv("POSTGRES_URL"))
    
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS axons (
            pk TEXT PRIMARY KEY,
            version INTEGER,
            ip TEXT,
            port INTEGER,
            ip_type INTEGER,
            hotkey TEXT,
            coldkey TEXT,
            protocol INTEGER,
            status TEXT,
            staked_amount FLOAT,
            uid INTEGER,
            vpermit BOOLEAN,
            last_seen TIMESTAMP,
            dividends FLOAT,
            incentive FLOAT,
            trust FLOAT,
            last_update INTEGER
        )
    ''')
    
    for axon in axons:
        pk = f"{subnet_id}_{subtensor}_{axon['uid']}_{axon['hotkey']}"
        existing_axon = await conn.fetchrow('SELECT * FROM axons WHERE pk = $1', pk)
        if existing_axon:
            timestamp = None
            if axon['status'] == "connected":
                timestamp = datetime.now()
                
            if timestamp:
                await conn.execute('''
                    UPDATE axons SET version=$1, port=$2, ip_type=$3, coldkey=$4, protocol=$5, status=$6, staked_amount=$7, uid=$8, vpermit=$9, last_seen=$10, dividends=$11, incentive=$12, trust=$13, last_update=$14, ip=$15 WHERE pk=$16
                ''', axon['version'], axon['port'], axon['ip_type'], axon['coldkey'], axon['protocol'], axon['status'], axon['staked_amount'], axon['uid'], axon['vpermit'], timestamp, axon['dividends'], axon['incentive'], axon['trust'], axon['last_update'],axon['ip'], pk)
            else:
                await conn.execute('''
                    UPDATE axons SET version=$1, port=$2, ip_type=$3, coldkey=$4, protocol=$5, status=$6, staked_amount=$7, uid=$8, vpermit=$9, dividends=$10, incentive=$11, trust=$12, last_update=$13, ip=$14 WHERE pk=$15
                ''', axon['version'], axon['port'], axon['ip_type'], axon['coldkey'], axon['protocol'], axon['status'], axon['staked_amount'], axon['uid'], axon['vpermit'], axon['dividends'], axon['incentive'], axon['trust'], axon['last_update'], axon['ip'], pk)
        else:
            if(axon['ip'] != '0.0.0.0'):
                await conn.execute('''
                    INSERT INTO axons(pk, version, ip, port, ip_type, hotkey, coldkey, protocol, status, staked_amount, uid, vpermit, dividends, incentive, trust, last_update) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ''', pk, axon['version'], axon['ip'], axon['port'], axon['ip_type'], axon['hotkey'], axon['coldkey'],
                axon['protocol'], axon['status'], axon['staked_amount'],
                axon['uid'], axon['vpermit'], axon['dividends'], axon['incentive'], axon['trust'], axon['last_update'])
        await store_uptime_report(pk, axon['status'])
    await conn.close()
    

async def periodic_axons_update():
    while True:
        await get_axons(subnet_id=1)  # Replace '1' with the appropriate subnet value if needed
        await asyncio.sleep(60)


def start_periodic_update():
    asyncio.run(periodic_axons_update())

update_thread = threading.Thread(target=start_periodic_update)
update_thread.start()


@app.get("/axons/{subnet}")
async def get_axons_rest():
    conn = await asyncpg.connect(os.getenv("POSTGRES_URL"))
    axons = await conn.fetch('SELECT * FROM axons')
    
    
    await conn.close()
    return { "axons": [dict(axon) for axon in axons] }


async def get_subnet_weights(subnet: int):
    conn = await asyncpg.connect(os.getenv("POSTGRES_URL"))

    metagraph = bt.metagraph(subnet, subtensor, lite=False)

    weights = metagraph.weights.tolist()
    uids = metagraph.uids.tolist()
    weights_with_uids = [{"uid": uid, "weight": weight} for uid, weight in zip(uids, weights)]
    axons = await conn.fetch('SELECT * FROM axons')
    axons_info = []
    for axon in axons:
        axon_dict = dict(axon)
        uid = axon_dict['uid']
        weight = next((w for u, w in zip(uids, weights) if u == uid), None)
        if weight is not None:
            axon_dict['weight'] = weight
        axons_info.append(axon_dict)
    return { "weights_with_uids": weights_with_uids }


@app.get("/weights/{subnet}")
async def get_weights(subnet: int):
    # Assuming `bt` is the Bittensor module and `metagraph` is accessible
    try:
        return await get_subnet_weights(subnet)
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})



@app.get("/leaderboard/{subnet}")
async def get_leaderboard(subnet: int):
    try:
        # Check if the leaderboard for the given subnet is in the cache
        if subnet in leaderboard_cache:
            return leaderboard_cache[subnet]

        conn = await asyncpg.connect(os.getenv("POSTGRES_URL"))

        # Fetch axons and their trust values
        axons = await conn.fetch('SELECT * FROM axons')
        if not axons:
            return JSONResponse(status_code=404, content={"message": "No axons found for the given subnet"})

        weights = await get_subnet_weights(subnet)
        
        # Calculate uptime percentage for each axon in the last 24 hours
        leaderboard = []
        for axon in axons:
            axon_dict = dict(axon)
            pk = f"{subnet}_{subtensor}_{axon_dict['uid']}_{axon_dict['hotkey']}"
            
            uptime_records = await conn.fetch('''
                SELECT * FROM uptime 
                WHERE pk = $1 AND timestamp >= NOW() - INTERVAL '24 HOURS'
            ''', pk)
            
            total_records = len(uptime_records)
            uptime_percentage = sum(record['status'] == 'connected' for record in uptime_records) / total_records if total_records > 0 else 0
            
            validators_uids = [axon["uid"] for axon in axons if axon["vpermit"]]
            # Calculate the average weight for the axon
            axon_weights = [w['weight'][axon['uid']] for w in weights['weights_with_uids'] if w['uid'] in validators_uids]
            if axon_weights:
                average_weight = sum(axon_weights) / len(axon_weights)
                axon_dict['average_weight'] = average_weight
            else:
                axon_dict['average_weight'] = 0
            
            if uptime_percentage > 0:
                axon_dict['uptime_percentage'] = uptime_percentage
                leaderboard.append(axon_dict)
                
        # Sort axons based on trust value and uptime percentage
        leaderboard.sort(key=lambda x: (x['trust'], x['average_weight'], x['uptime_percentage']), reverse=True)

        # Assign positions
        for position, axon in enumerate(leaderboard, start=1):
            axon['position'] = position

        await conn.close()

        # Cache the leaderboard for the given subnet
        leaderboard_cache[subnet] = leaderboard

        return leaderboard
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})



@app.get("/axon/uptime/{subnet}/{uid}")
async def get_axon_uptime(subnet: int, uid: int):
    conn = await asyncpg.connect(os.getenv("POSTGRES_URL"))
    
    axon = await conn.fetchrow('''
        SELECT * FROM axons 
        WHERE uid = $1
    ''', uid)
    
    if not axon:
        return JSONResponse(status_code=404, content={"message": "Axon not found"})
    # Fetch the last up to 60 uptime records for the given axon on the specified subnet from the uptime table
    pk = f"{subnet}_{subtensor}_{axon['uid']}_{axon['hotkey']}"


    uptime_records = await conn.fetch('''
        SELECT * FROM uptime 
        WHERE pk = $1
        ORDER BY timestamp DESC 
        LIMIT 60
    ''', pk)
    
    await conn.close()
    
    return { "uptime": [dict(record) for record in uptime_records] }



@app.post("/axons/setup/{subnet}")
async def get_connected_axons(subnet: int, request: Request):
    """
    Get all connected axons by IP address and subnet ID.

    Parameters:
    subnet_id (int): The subnet ID to query.
    request (Request): The incoming request object containing the IP address.

    Returns:
    List[dict]: A list of connected axons with the given IP address.
    """
    try:
        request_data = await request.json()
        ip = request_data.get("ip")
        if not ip:
            raise HTTPException(status_code=400, detail="IP address is required")
        
        connected_axons = await get_connected_axons_by_ip(ip, subnet)
        return {"connected_axons": connected_axons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.post("/axon/call_all")
async def call_all_axons_with_vpermit(request: Request):
    """
    Calls a specific method on all axons with vpermit.

    Args:
        request (Request): The incoming request object containing method, path, body, etc.

    Returns:
        List[dict]: An array of responses from the axons.
    """
    responses = []

    # Extract method, path, and body from the request
    request_data = await request.json()
    method = request_data.get("method")
    path = request_data.get("path")
    body = request_data.get("body", {})

    if not method or not path:
        return JSONResponse(status_code=400, content={"message": "Method and path are required"})

    for axon in axons_cache:
        if axon.get("vpermit"):
            # Validate that the axon is connected
            if axon["status"] != "connected":
                responses.append({"axon": axon, "response": {"status_code": 400, "message": "Axon is not connected"}})
                continue

            # Construct the URL
            url = f"http://{axon['ip']}:8000/{path}"
            if axon['ip'] == external_ip:
                url = f"http://localhost:8000/{path}"

            # Forward the request to the axon
            async with httpx.AsyncClient() as client:
                try:
                    if method.upper() == "GET":
                        response = await client.get(url, params=body)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=body)
                    elif method.upper() == "PUT":
                        response = await client.put(url, json=body)
                    else:
                        responses.append({"axon": axon, "response": {"status_code": 400, "message": "Invalid method"}})
                        continue

                    responses.append({"axon": axon, "response": response.json()})
                except Exception as e:
                    responses.append({"axon": axon, "response": {"status_code": 500, "message": str(e)}})

    return responses

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
    try:
        # Get axons
        conn = await asyncpg.connect(os.getenv("POSTGRES_URL"))
        axons = await conn.fetch('SELECT * FROM axons')
        await conn.close()
        
        
        # Find the axon with the given UID
        axon = next((axon for axon in axons if axon["uid"] == uid), None)
        
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
        try:
            if method.upper() == "GET":
                response = requests.get(url)
            elif method.upper() == "POST":
                response = requests.post(url, json=body)
            elif method.upper() == "PUT":
                response = requests.put(url, json=body)
            elif method.upper() == "DELETE":
                response = requests.delete(url, json=body)
            elif method.upper() == "PATCH":
                response = requests.patch(url, json=body)
            else:
                return JSONResponse(status_code=405, content={"message": "Method not allowed"})
        except requests.RequestException as e:
            return JSONResponse(status_code=500, content={"message": str(e)})
        print(f"RESPONSE: {response}")
        
        return JSONResponse(status_code=response.status_code, content=response.json())

    except Exception as e:
        print("Exception", e)
        raise HTTPException(status_code=500, detail=str(e))

    