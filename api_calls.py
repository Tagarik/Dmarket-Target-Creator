import requests, json, time, json, logging
from datetime import datetime
from nacl.bindings import crypto_sign
from furl import furl

signature_prefix = "dmar ed25519 "

def header_creator_params( private_key, public_key, request_method: str, api_url: str, params: dict = None,):
    global signature_prefix
    nonce = str(round(datetime.now().timestamp()))
    string_to_sign = request_method + api_url
    if params:
        string_to_sign = str(furl(string_to_sign).add(params))
    string_to_sign += nonce
    encoded = string_to_sign.encode('utf-8')
    signature_bytes = crypto_sign(encoded, bytes.fromhex(private_key))
    signature = signature_bytes[:64].hex()
    headers = {
        "X-Request-Sign": signature_prefix + signature,
        "X-Api-Key": public_key,
        "X-Sign-Date": nonce,
        "Content-Type": "application/json"
        }
    return headers

def header_creator_body(private_key, public_key, request_method: str, api_url: str, body: dict):
    global signature_prefix
    nonce = str(round(datetime.now().timestamp()))
    string_to_sign = request_method + api_url + json.dumps(body) + nonce
    encoded = string_to_sign.encode('utf-8')
    signature_bytes = crypto_sign(encoded, bytes.fromhex(private_key))
    signature = signature_bytes[:64].hex()
    headers = {
        "X-Request-Sign": signature_prefix + signature,
        "X-Api-Key": public_key,
        "X-Sign-Date": nonce,
        "Content-Type": "application/json"
        }
    return headers

def get_dmarket_balance(private_key, public_key):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/account/v1/balance"
    request_method = "GET"    
    headers = header_creator_params(private_key, public_key, request_method, api_url)
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

def custom_fees(private_key, public_key):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/exchange/v1/customized-fees"
    request_method = "GET"
    x = 1        
    params = {
        "gameId": "a8db", 
        "offerType": "dmarket",
        "limit": 10000,
        "offset": x
        }
    headers = header_creator_params(private_key, public_key, request_method, api_url, params)
    resp = requests.get(rootApiUrl + api_url, params = params, headers = headers)
    if resp.status_code == 200:
        logging.info(f"GET ITEMS WITH CUSTOM FEES STATUS CODE - {resp.status_code}")
    else:
        logging.error(f"GET ITEMS WITH CUSTOM FEES STATUS CODE - {resp.status_code}")
        logging.error(resp.text)
    data = json.loads(resp.text)
    return data

def post_order(item: dict, private_key, public_key):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/marketplace-api/v1/user-targets/create"
    request_method = "POST"
    amount = float(item["Buy_Orders"])+0.01
    body = {
            "GameID": "a8db",
            "Targets": [
                {
                    "Amount": "1",
                    "Price": {
                        "Currency": "USD",
                        "Amount": amount
                    },
                    "Title": item["title"],
                }
            ]
            }
    headers = header_creator_body(private_key, public_key, request_method, api_url, body)
    resp = requests.post(rootApiUrl + api_url, json=body, headers=headers)
    if resp.status_code == 200:
        logging.info(f"POST TARGET STATUS CODE - {resp.status_code}")
    else:
        logging.error(f"POST TARGET STATUS CODE - {resp.status_code}")
        logging.error(resp.text)
    details = json.loads(resp.text)
    return details

def aggregate(items: list, private_key, public_key):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/price-aggregator/v1/aggregated-prices"
    request_method = "GET"
    deal_list = []
    item_list = []
    for i in items:
        item_list.append(i["i"])
        if len(item_list) > 50:
            params = {"Titles": item_list,
                      "gameId": "a8db"}
            headers = header_creator_params(private_key, public_key, request_method, api_url, params)
            resp = requests.get(rootApiUrl + api_url, params = params, headers = headers)
            details = json.loads(resp.text)
            if resp.status_code == 200:
                logging.info(f"PARTIAL AGGREGATOR STATUS CODE - {resp.status_code}")
            else:
                logging.error(f"PARTIAL AGGREGATOR STATUS CODE - {resp.status_code}")
                logging.error(resp.text)
            item_list = []
            c = 0
            time.sleep(0.2)
            for x in details:
                deal_list.append({"title": details['AggregatedTitles'][c]['MarketHashName'],
                "Sale_Offers": details['AggregatedTitles'][c]['Offers']["BestPrice"],
                "Listings": details['AggregatedTitles'][c]['Offers']["Count"],
                "Buy_Orders": details['AggregatedTitles'][c]['Orders']["BestPrice"]})
                c = c + 1
            item_list = []
    return deal_list

def aggregate_full(private_key, public_key, Offset):
    rootApiUrl = "https://api.dmarket.com"
    api_url = "/price-aggregator/v1/aggregated-prices"
    request_method = "GET"
    params = {"Offset": Offset*10000,
              "GameID": "a8db"}
    headers = header_creator_params(private_key, public_key, request_method, api_url, params)
    resp = requests.get(rootApiUrl + api_url, params = params, headers = headers)
    if resp.status_code == 200:
        logging.info(f"FULL AGGREGATOR STATUS CODE - {resp.status_code}")
    else:
        logging.error(f"FULL AGGREGATOR STATUS CODE - {resp.status_code}")
        logging.error(resp.text)
    details = json.loads(resp.text)
    return details

def last_sales(private_key, public_key, item):
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
        headers = header_creator_params(private_key, public_key, request_method, api_url, params)
        resp = requests.get(rootApiUrl + api_url, params=params, headers=headers)
        time.sleep(0.2)
        if resp.status_code == 200:
            logging.info(f"GET SALES DATA STATUS CODE - {resp.status_code}")
        else:
            logging.error(f"GET SALES DATA STATUS CODE - {resp.status_code}")
            logging.error(resp.text)
        details.append(json.loads(resp.text))
    return details