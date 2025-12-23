import os, datetime, config, api_calls, logging as log, dotenv, os
dotenv.load_dotenv()
log.basicConfig(level=log.INFO)

output_file_path = "dmakret_fees.json"
balance = 0

def low_fee_buy_orders():
    percentage = config.SMALL_FEE
    data =  api_calls.custom_fees(private_key=os.getenv("PRIVATE_KEY"), public_key=os.getenv("PUBLIC_KEY"))
    items = []
    for i in data["reducedFees"]:
        if not check(i["title"]):
            items.append({'i':i["title"]})
    deal_list = api_calls.aggregate(items=items, private_key=os.getenv("PRIVATE_KEY"), public_key=os.getenv("PUBLIC_KEY"))
    compare_prices(deal_list, percentage)

def compare_prices(deal_list: list, percentage: float):
    order_list = []
    balance = api_calls.get_dmarket_balance(private_key=os.getenv("PRIVATE_KEY"), public_key=os.getenv("PUBLIC_KEY"))

    for i in deal_list:
        if float(i["Buy_Orders"]) < percentage * float(i["Sale_Offers"]) and float(i["Listings"]) > config.listings_amount and config.min_price < float(i["Buy_Orders"]) < int(balance)/100 * 0.95:
            is_liquid = liquidity_check(item=i["title"])
            if is_liquid == True:
                order_list.append(i)
    place_orders(order_list)

def place_orders(order_list: list):
    if order_list != []:
        for i in order_list:
            response = api_calls.post_order(item=i, private_key=os.getenv("PRIVATE_KEY"), public_key=os.getenv("PUBLIC_KEY"))
            if response["Result"][0]["Successful"] != True:
                log.error(f"COULDN'T PLACE ORDER FOR {response['Result'][0]['CreateTarget']['Title']}: {response['Result'][0]['Error']['Message']}")
            else:
                log.info(f"ORDER PLACED: {response['Result'][0]['CreateTarget']['Title']} | Price - {response['Result'][0]['CreateTarget']['Price']['Amount']}$ | Amount - {response['Result'][0]['CreateTarget']['Amount']}")
    else:
        log.info("no items to order")
    print("Press Enter to continue")
    choice = input(" > ")
    main_menu()

def high_fee_buy_orders():
    deal_list = []
    details_full = []
    items = []
    percentage = config.BIG_FEE

    for i in range(6):
        details = api_calls.aggregate_full(private_key=os.getenv("PRIVATE_KEY"), public_key=os.getenv("PUBLIC_KEY"), Offset=i)
        details_full.append(details["AggregatedTitles"])

    for i in details_full:
        for x in i:
            if not check(i=x['MarketHashName']):
                if x["GameID"] == "a8db":
                    items.append(x)

    for x in items:
        deal_list.append({"title": x['MarketHashName'],
                            "Sale_Offers": x['Offers']["BestPrice"],
                            "Listings": x['Offers']["Count"],
                            "Buy_Orders": x['Orders']["BestPrice"]})
    compare_prices(deal_list, percentage)

def liquidity_check(item: str):
    sales_indicator = 0
    targets_indicator = 0
    data = api_calls.last_sales(private_key=os.getenv("PRIVATE_KEY"), public_key=os.getenv("PUBLIC_KEY"), item=item)
    sales = data[0]["sales"]
    targets = data[1]["sales"]
    for i in sales:
        if datetime.datetime.fromtimestamp(int(i["date"])) > datetime.datetime.now() - datetime.timedelta(days=6):
            sales_indicator += 1
    for i in targets:
        if datetime.datetime.fromtimestamp(int(i["date"])) > datetime.datetime.now() - datetime.timedelta(days=6):
            targets_indicator += 1
    if sales_indicator + targets_indicator > config.total_liquidity and sales_indicator > config.sales_liquidity and targets_indicator > config.targets_liquidity:
        return True
    else: return False

def check(i: str) -> bool:
    for x in config.blacklist:
        if x in i: return True
    return False

def clear_screen():
    os.system("cls")

def main_menu():
    clear_screen()
    print("==========TARGET CREATOR==========\n")
    print(f"[1] fetch buy orders (2% fee)\n[2] fetch buy orders (10% fee)\n[3] quit")
    choice = input(" > ")
    if choice == "1":
        low_fee_buy_orders()
    elif choice == "2":
        high_fee_buy_orders()
    elif choice == "3":
        quit()
    else:
        main_menu()

if __name__ == "__main__":
    main_menu()
