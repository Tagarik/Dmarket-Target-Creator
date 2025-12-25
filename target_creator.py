import os, datetime, config, api_calls, logging as log, dotenv, os, time
dotenv.load_dotenv()
log.basicConfig(level=log.INFO)


def low_fee_buy_orders():
    items = []
    offset = 0
    
    while True:
        data = api_calls.custom_fees(offset=offset*1000)
        reduced_fees = data.get("reducedFees", [])
        
        if not reduced_fees:
            break
        
        for i in reduced_fees:
            if not check(i["title"]):
                items.append(i["title"])
        
        log.info(f"Fetched offset {offset}, total items: {len(items)}")
        offset += 1
    
    print(f"Total items with reduced fees: {len(items)}")
    
    # Process items through aggregate_items in batches of 200
    deal_list = []
    batch_size = 200
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(items))
        batch = items[start_idx:end_idx]
        
        log.info(f"Processing batch {batch_num + 1}/{total_batches}, items {start_idx} to {end_idx - 1} ({len(batch)} items)")
        
        data = api_calls.aggregate_items(titles=batch, limit=len(batch))
        aggregated_prices = data.get("aggregatedPrices", [])
        
        log.info(f"Received {len(aggregated_prices)} aggregated prices from API")
        
        for item in aggregated_prices:
            if item['offerBestPrice'] is None or item['orderBestPrice'] is None:
                continue
            deal_list.append({
                "title": item['title'],
                "Sale_Offers": float(item['offerBestPrice']["Amount"])/100,
                "Listings": item['offerCount'],
                "Buy_Orders": float(item['orderBestPrice']["Amount"])/100
                })
        time.sleep(0.2)
    
    return deal_list

def compare_prices(deal_list: list, percentage: float):
    order_list = []
    compatible_items = []
    balance = api_calls.get_dmarket_balance()

    for i in deal_list:
        if float(i["Buy_Orders"]) < percentage * float(i["Sale_Offers"]) and float(i["Listings"]) > config.listings_amount and config.min_price < float(i["Buy_Orders"]) < int(balance)/100:
            compatible_items.append(i)
         
    print(f"Found {len(compatible_items)} compatible items")
    
    for i in compatible_items:
        is_liquid = liquidity_check(item=i["title"])
        if is_liquid == True:
            order_list.append(i)
            
    print(f"{len(order_list)} items passed liquidity check")
    return order_list

def place_orders(order_list: list):
    targets = []
    
    if order_list != []:
        # Limit to 100 items
        for i in order_list[:100]:
            targets.append({
                    "Amount": "1",
                    "Price": {
                        "Currency": "USD",
                        "Amount": float(i["Buy_Orders"])+0.01
                    },
                    "Title": i["title"],
                })

        response = api_calls.post_order(items=targets)
        
        # Log each individual order result
        with open("orders_log.txt", "a") as f:
            for result in response["Result"]:
                if result["Successful"]:
                    target = result["CreateTarget"]
                    log_entry = f"SUCCESS | {target['Title']} | ${target['Price']['Amount']} | ID: {result['TargetID']}\n"
                    f.write(log_entry)
                    log.info(f"ORDER PLACED: {target['Title']} | Price: ${target['Price']['Amount']}")
                else:
                    error_msg = f"ERROR | {result['CreateTarget']['Title']} | {result['Error']['Message']}\n"
                    f.write(error_msg)
                    log.error(f"COULDN'T PLACE ORDER FOR {result['CreateTarget']['Title']}: {result['Error']['Message']}")
        
        log.info(f"Total orders placed: {len(targets)} items")
    else:
        log.info("no items to order")
    print("Press Enter to continue")
    choice = input(" > ")
    main_menu()

def high_fee_buy_orders():
    deal_list = []
    all_items = []
    seen_titles = set()
    cursor = None
    page = 0
    no_new_items_count = 0

    while True:
        details = api_calls.aggregate_items(cursor=cursor, limit=1000)
        items = details.get("aggregatedPrices", [])
        
        # Track new unique items
        new_items = 0
        for item in items:
            # Skip items with missing price data
            if item.get('offerBestPrice') is None or item.get('orderBestPrice') is None:
                continue
                
            title = item.get('title', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                all_items.append(item)
                new_items += 1
        
        print(f"Fetched cursor {page + 1}, new items: {new_items}, total unique: {len(all_items)}")
        
        # If no new items found, increment counter
        if new_items == 0:
            no_new_items_count += 1
            if no_new_items_count >= 2:
                print("No new items in 2 consecutive batches, stopping pagination")
                break
        else:
            no_new_items_count = 0
        
        if details.get("nextCursor") is None:
            break
        cursor = details.get("nextCursor")
        page += 1

    filtered_items = []
    for x in all_items:
        if not check(i=x['title']):
            filtered_items.append(x)

    for x in filtered_items:
        deal_list.append({"title": x['title'],
                            "Sale_Offers": float(x['offerBestPrice']["Amount"])/100,
                            "Listings": x['offerCount'],
                            "Buy_Orders": float(x['orderBestPrice']["Amount"])/100})
    return deal_list

def liquidity_check(item: str):
    sales_indicator = 0
    targets_indicator = 0
    data = api_calls.last_sales(item=item)
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
        items = low_fee_buy_orders()
        order_list = compare_prices(items, config.SMALL_FEE)
        place_orders(order_list)
    elif choice == "2":
        items = high_fee_buy_orders()
        order_list = compare_prices(items, config.BIG_FEE)
        place_orders(order_list)
    elif choice == "3":
        quit()
    else:
        main_menu()

if __name__ == "__main__":
    main_menu()
