import requests, json, time, json, logging, dotenv, os
from datetime import datetime
from nacl.bindings import crypto_sign
from furl import furl

dotenv.load_dotenv()
signature_prefix = "dmar ed25519 "

def header_creator_params(request_method: str, api_url: str, params: dict = None,):
    global signature_prefix
    nonce = str(round(datetime.now().timestamp()))
    string_to_sign = request_method + api_url
    if params:
        string_to_sign = str(furl(string_to_sign).add(params))
    string_to_sign += nonce
    encoded = string_to_sign.encode('utf-8')
    signature_bytes = crypto_sign(encoded, bytes.fromhex(os.getenv("private_key")))
    signature = signature_bytes[:64].hex()
    headers = {
        "X-Request-Sign": signature_prefix + signature,
        "X-Api-Key": os.getenv("public_key"),
        "X-Sign-Date": nonce,
        "Content-Type": "application/json"
        }
    return headers

def header_creator_body(request_method: str, api_url: str, body: dict):
    global signature_prefix
    nonce = str(round(datetime.now().timestamp()))
    string_to_sign = request_method + api_url + json.dumps(body) + nonce
    encoded = string_to_sign.encode('utf-8')
    signature_bytes = crypto_sign(encoded, bytes.fromhex(os.getenv("private_key")))
    signature = signature_bytes[:64].hex()
    headers = {
        "X-Request-Sign": signature_prefix + signature,
        "X-Api-Key": os.getenv("public_key"),
        "X-Sign-Date": nonce,
        "Content-Type": "application/json"
        }
    return headers

def get_dmarket_balance():
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/account/v1/balance"
    request_method = "GET"    
    headers = header_creator_params(request_method, api_url)
    response = requests.get(rootApiUrl + api_url, headers=headers)
    if response.status_code == 200:
        logging.info(f"GET DMARKET BALANCE STATUS CODE - {response.status_code}")
    else:
        logging.error(f"GET DMARKET BALANCE STATUS CODE - {response.status_code}")
        logging.error(response.text)
    data = json.loads(response.text)
    balance = data["usd"]
    logging.info(f"current balance: {float(balance)/100}$")
    return balance

def custom_fees(offset: int):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/exchange/v1/customized-fees"
    request_method = "GET"    
    params = {
        "gameId": "a8db", 
        "offerType": "dmarket",
        "limit": 1000,
        "offset": offset
        }
    headers = header_creator_params(request_method, api_url, params)
    resp = requests.get(rootApiUrl + api_url, params = params, headers = headers)
    if resp.status_code == 200:
        logging.info(f"GET ITEMS WITH CUSTOM FEES STATUS CODE - {resp.status_code}")
    else:
        logging.error(f"GET ITEMS WITH CUSTOM FEES STATUS CODE - {resp.status_code}")
        logging.error(resp.text)
    data = json.loads(resp.text)
    return data

def post_order(items: dict):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/marketplace-api/v1/user-targets/create"
    request_method = "POST"
    body = {
            "GameID": "a8db",
            "Targets": items
            }
    headers = header_creator_body(request_method, api_url, body)
    resp = requests.post(rootApiUrl + api_url, json=body, headers=headers)
    if resp.status_code == 200:
        logging.info(f"POST TARGET STATUS CODE - {resp.status_code}")
    else:
        logging.error(f"POST TARGET STATUS CODE - {resp.status_code}")
        logging.error(resp.text)
    details = json.loads(resp.text)
    return details

def aggregate_items(cursor: str = None, titles: list = [], limit: int = 1000):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/marketplace-api/v1/aggregated-prices"
    request_method = "POST"
    body = {'filter': {'game': 'a8db'}, 'limit': str(limit), 'cursor': cursor}
    if titles != []:
        body['filter']['titles'] = titles
    headers = header_creator_body(request_method, api_url, body)
    resp = requests.post(rootApiUrl + api_url, json=body, headers=headers)
    
    if resp.status_code != 200:
        logging.error(f"AGGREGATOR STATUS CODE - {resp.status_code}")
        logging.error(resp.text)
        quit()
    data = resp.json()
    return data

def last_sales(item):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/trade-aggregator/v1/last-sales"
    request_method = "GET"
    operation_type = ["Target","Offer"]
    details = []
    for x in operation_type:
        params = {
            "gameId":"a8db",
            "title":item,
            "txOperationType":x,
            "Limit": 20
            }
        headers = header_creator_params(request_method, api_url, params)
        resp = requests.get(rootApiUrl + api_url, params=params, headers=headers)
        time.sleep(0.2)
        if resp.status_code == 200:
            logging.info(f"GET SALES DATA STATUS CODE - {resp.status_code}")
        else:
            logging.error(f"GET SALES DATA STATUS CODE - {resp.status_code}")
            logging.error(resp.text)
        details.append(json.loads(resp.text))
    return details