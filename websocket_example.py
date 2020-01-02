#!/usr/bin/env python
import time
import datetime
import uuid
import urllib
import asyncio
import websockets
import json
import hmac
import base64
import hashlib
import gzip
import traceback

        

def generate_signature(host, method, params, request_path, secret_key):
    """Generate signature of huobi future.
    
    Args:
        host: api domain url.PS: colo user should set this host as 'api.hbdm.com',not colo domain.
        method: request method.
        params: request params.
        request_path: "/notification"
        secret_key: api secret_key

    Returns:
        singature string.

    """
    host_url = urllib.parse.urlparse(host).hostname.lower()
    sorted_params = sorted(params.items(), key=lambda d: d[0], reverse=False)
    encode_params = urllib.parse.urlencode(sorted_params)
    payload = [method, host_url, request_path, encode_params]
    payload = "\n".join(payload)
    payload = payload.encode(encoding="UTF8")
    secret_key = secret_key.encode(encoding="utf8")
    digest = hmac.new(secret_key, payload, digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(digest)
    signature = signature.decode()
    return signature

async def subscribe(url, access_key, secret_key, subs, callback=None, auth=False):
    """ Huobi Future subscribe websockets.

    Args:
        url: the url to be signatured.
        access_key: API access_key.
        secret_key: API secret_key.
        subs: the data list to subscribe.
        callback: the callback function to handle the ws data received. 
        auth: True: Need to be signatured. False: No need to be signatured.

    """
    async with websockets.connect(url) as websocket:
        if auth:
            timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            data = {
                "AccessKeyId": access_key,
                "SignatureMethod": "HmacSHA256",
                "SignatureVersion": "2",
                "Timestamp": timestamp
            }
            sign = generate_signature(url,"GET", data, "/notification", secret_key)
            data["op"] = "auth"
            data["type"] = "api"
            data["Signature"] = sign
            msg_str = json.dumps(data)
            await websocket.send(msg_str)
            print(f"send: {msg_str}")
        for sub in subs:
            sub_str = json.dumps(sub)
            await websocket.send(sub_str)
            print(f"send: {sub_str}")
        last_version = 0
        last_ts = 0
        while True:
            rsp = await websocket.recv()
            data = json.loads(gzip.decompress(rsp).decode())
            #print(f"recevie<--: {data}")
            if "op" in data and data.get("op") == "ping":
                pong_msg = {"op": "pong", "ts": data.get("ts")}
                await websocket.send(json.dumps(pong_msg))
                #print(f"send: {pong_msg}")
                continue
            if "ping" in data: 
                pong_msg = {"pong": data.get("ping")}
                await websocket.send(json.dumps(pong_msg))
                #print(f"send: {pong_msg}")
                continue
            if 'ch' in data and 'depth' in data['ch']:
                t_ts = data['tick']['ts']
                o_ts = data['ts']
                version = data['tick']['version']
                now_ts = int(time.time()*1000)
                if now_ts - o_ts > 200:
                    print(f"now ts:{now_ts} tick ts:{t_ts} inner_diff: {now_ts-t_ts} outer_diff: {now_ts - o_ts}")
                if last_version !=0 and version != last_version + 1:
                    print(f"now ts:{time.time()*1000},now version:{version}, last version:{last_version}")  
                if o_ts - last_ts > 500:
                    print(f"last packet outer_ts:{last_ts},  now outer_ts:{o_ts}, now version:{version} diff: {o_ts-last_ts}")
                last_version = version
                last_ts = o_ts
            #print(data)
            #rsp = await callback(data)

async def handle_ws_data(*args, **kwargs):
    """ callback function
    Args:
        args: values
        kwargs: key-values.
    """
    print("callback param", *args,**kwargs)

if __name__ == "__main__":
    ####  input your access_key and secret_key below:
    access_key  = ""
    secret_key  = ""
   
     #market_url = 'wss://www.hbdm.vn/ws'
    market_url = 'wss://www.btcquant.pro/ws'
    order_url = 'wss://api.hbdm.vn/notification'
    
    market_subs = [
                {
                    "sub": "market.BTC_CQ.depth.size_150.high_freq",
                    "data_type": "incremental",
                    "id": str(uuid.uuid1())
                },
                #{
                #    "sub": "market.BTC_CQ.depth.size_150.high_freq",
                #    "data_type": "incremental",
                #    "id": str(uuid.uuid1())
                #}
            ]

    order_subs = [
                {
                    "op": "sub",
                    "cid": str(uuid.uuid1()),
                    "topic": "orders.EOS"
                },
                {
                    "op": "sub",
                    "cid": str(uuid.uuid1()),
                    "topic": "positions.EOS"
                },
                {
                    "op": "sub",
                    "cid": str(uuid.uuid1()),
                    "topic": "accounts.EOS"
                }

            ]

    while True: 
        try:
            asyncio.get_event_loop().run_until_complete(subscribe(market_url, access_key,  secret_key, market_subs, handle_ws_data, auth=False))
            #asyncio.get_event_loop().run_until_complete(subscribe(order_url, access_key,  secret_key, order_subs, handle_ws_data, auth=True))
        #except (websockets.exceptions.ConnectionClosed):
        except Exception as e:
            traceback.print_exc()
            print('%s websocket connection error. reconnect rightnow' % (time.time()))
