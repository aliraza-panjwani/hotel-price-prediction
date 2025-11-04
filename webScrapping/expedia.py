import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import random
import re
try:
    from webScrapping.mapping import hotel_mapping
except ImportError:
    from mapping import hotel_mapping
import undetected_chromedriver as uc

# ===================== DRIVER SETUP ===================== #
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ===================== DATE GENERATION ===================== #
# def generate_october_dates(year=2025):
#     dates = []
#     start_date = datetime(year, 11, 1)
#     for i in range(5):
#         check_in = start_date + timedelta(days=i)
#         if check_in.month != 11:
#             break
#         check_out = check_in + timedelta(days=1)
#         if check_out.month == 11:
#             dates.append((check_in.strftime("%Y-%m-%d"), check_out.strftime("%Y-%m-%d")))
#     return dates
def generate_date_range(start_date: str, end_date: str):
    """
    Generate (check_in, check_out) date pairs between start_date and end_date (inclusive).
    Dates are in 'YYYY-MM-DD' format.
    """
    # Convert strings to datetime
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    dates = []
    current = start

    while current < end:
        check_in = current
        check_out = check_in + timedelta(days=1)
        if check_out > end:
            break
        dates.append((check_in.strftime("%Y-%m-%d"), check_out.strftime("%Y-%m-%d")))
        current += timedelta(days=1)

    return dates

# ===================== URL GENERATION ===================== #
def generate_hotel_url(base_url, hotel_id, checkin, checkout):
    """
    Always use expedia.co.in and force INR currency
    """
    core = base_url.split('?')[0]
    # Replace .com with .co.in if user gives wrong domain
    core = core.replace("expedia.com", "expedia.co.in")
    # Add INR currency parameter
    ts = int(time.time() * 1000)  # pwa_ts for freshness
    return (f"{core}?chkin={checkin}&chkout={checkout}"
            f"&x_pwa=1&rfrr=HSR&useRewards=true&rm1=a2"
            f"&selected={hotel_id}&sort=RECOMMENDED"
            f"&pwa_ts={ts}&top_cur=USD")

# ===================== HUMAN VERIFICATION ===================== #
first_run = True
def wait_for_human_verification(driver):
    global first_run
    if not first_run:
        print("Skipping verification wait (already completed once).")
        return
    first_run = False

    print("Waiting for potential human verification...")
    print("Please complete any CAPTCHA or verification if it appears.")
    print("The script will wait for 30 seconds.")
    time.sleep(30)

    verification_keywords = ["verify", "challenge", "captcha", "puzzle", "security"]
    current_url = driver.current_url.lower()
    if any(k in current_url for k in verification_keywords):
        print("Verification still detected after 30 seconds.")
        # input("Press Enter when verification is complete and the hotel page is loaded...")

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            if any(k in src.lower() for k in verification_keywords):
                print("Verification iframe detected.")
                # input("Press Enter when verification is complete and the hotel page is loaded...")
                break
    except:
        pass

# ===================== HELPERS ===================== #
def clean_price(text):
    if not text or text.strip() == "":
        return "Sold Out"
    # Normalize to INR
    cleaned_text = re.sub(r'[^\d.]', '', text)
    
    if cleaned_text:
        return float(cleaned_text)
    return None


def classify_room_and_bed(room_name, bed_type):
    """Normalize bed and room types based on known keywords."""
    bed_category = None
    room_category = "Normal"  # default
    
    # --- BED CATEGORY ---
    if bed_type:
        text = bed_type.lower()
        if "king" in text:
            bed_category = "King"
        elif "queen" in text:
            bed_category = "Queen"
        elif "twin" in text:
            bed_category = "Twin"
        elif "double" in text:
            bed_category = "Double"
        elif "sofa" in text:
            bed_category = "Sofa"
        else:
            bed_category = "Other"
    
    # --- ROOM CATEGORY ---
    if room_name:
        name = room_name.lower()
        if "suite" in name:
            room_category = "Suite"
        elif "deluxe" in name:
            room_category = "Deluxe"
        elif "premium" in name or "executive" in name:
            room_category = "Deluxe"
        elif "standard" in name or "classic" in name:
            room_category = "Normal"
        elif "superior" in name:
            room_category = "Normal"

    return bed_category, room_category

# ===================== ROOM EXTRACTION ===================== #
def extract_room_data(driver, checkin, checkout, hotel_id, hotel_name, hotel_url):
    rooms_data = []
    try:
        WebDriverWait(driver, 30).until(
            lambda d: "hotel-information" in d.current_url.lower() and "verify" not in d.current_url.lower()
        )
        time.sleep(30)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        room_blocks = [
            h for h in soup.select('h3.uitk-heading.uitk-heading-6')
            if 'uitk-type-bold' not in (h.get('class') or [])
            and not h.get_text(strip=True).endswith('?')
        ]

        for room in room_blocks:
            try:
                room_name = room.get_text(strip=True)
                if "reviews" in room_name.lower():
                    continue

                container = room.find_parent()
                for _ in range(5):
                    if container and 'uitk-card' in (container.get('class') or []):
                        break
                    container = container.parent
                if not container:
                    continue

                price_elem = container.select_one(
                    'div.uitk-text.uitk-type-500.uitk-type-medium.uitk-text-emphasis-theme'
                )
                base_price = clean_price(price_elem.get_text(strip=True) if price_elem else "")

                total_elem = container.select_one(
                    'div.uitk-text.uitk-type-end.uitk-type-300.uitk-text-default-theme'
                )
                total_price = clean_price(total_elem.get_text(strip=True) if total_elem else "")

                print("Debug Prices:", base_price, total_price)
                if total_price != None and base_price != None:
                    tax_price = total_price - base_price
                else:
                    tax_price = None

                bed_type = "N/A"
                bed_elems = container.select('div.uitk-text.uitk-type-300.uitk-text-default-theme')
                for b in bed_elems:
                    text = b.get_text(strip=True)
                    if 'bed' in text.lower():
                        bed_type = text
                        bed_type = re.sub(r'^\d+\s+', '', bed_type).strip()
                        break

                facilities_ul = container.select_one(
                    'ul.uitk-typelist.uitk-typelist-orientation-stacked.uitk-typelist-size-2'
                )
                facilities = []
                if facilities_ul:
                    for li in facilities_ul.select('li'):
                        txt = li.get_text(strip=True)
                        if txt:
                            facilities.append(txt)

                hotel_source  = "Expedia.com"

                available_rooms_elem = container.select_one(
                    'div.uitk-text.uitk-type-end.uitk-type-100.uitk-text-negative-theme'
                )
                if available_rooms_elem:
                    match = re.search(r'(\d+)', available_rooms_elem.get_text(strip=True))
                    available_rooms = int(match.group(1)) if match else None
                else:
                    available_rooms = None

                # refundable_text = "N/A"
                # refundable_charges = 0.0

                # refundable_container = container.select_one(".uitk-spacing")

                # if refundable_container:
                #     text_block = refundable_container.get_text(separator=" ", strip=True)
                #     refundable_text = text_block

                #     # Extract any numeric charge (e.g. ₹500, INR 500, $10)
                #     match_charge = re.search(r'(?:₹|\$|INR)?\s*([\d,]+)', text_block)
                #     if match_charge:
                #         refundable_charges = float(match_charge.group(1).replace(',', ''))
                #     else:
                #         refundable_charges = 0.0

                # Extract breakfast info
                # breakfast_elem = container.find(text=re.compile(r'Breakfast', re.IGNORECASE))
                # breakfast = True if breakfast_elem else False


                rooms_data.append({
                    "hotel_id": hotel_id,
                    "hotel_source": hotel_source,
                    "hotel_name": hotel_name,
                    "check_in": checkin,
                    "check_out": checkout,
                    # "room_id": room_id,
                    "room_name": room_name,
                    "bed_type": bed_type,
                    "bed_category": classify_room_and_bed(room_name, bed_type)[0],
                    "room_category": classify_room_and_bed(room_name, bed_type)[1],
                    "available_rooms" : available_rooms,
                    "base_price": base_price,
                    "tax_price": tax_price,
                    "total_price": total_price,
                    # "refundable_text": refundable_text,
                    # "refundable_charges": refundable_charges,
                    # "breakfast_included": breakfast,
                    "room_facilities": ", ".join(facilities) if facilities else "N/A",
                    "link": hotel_url
                })
                print(f"✓ {hotel_name} | {room_name} | Base: {base_price} | Total: {total_price}")

            except Exception as e:
                print(f"Error parsing room: {e}")
                continue

    except Exception as e:
        print(f"Error in extract_room_data: {e}")
    return rooms_data

# ===================== SCRAPER ===================== #
def scrape_hotels(hotels,start_date, end_date):
    # driver = setup_driver()
    print("Launching undetected Chrome driver...")
    driver = uc.Chrome(version_main=141)
    all_data = []
    print("Chrome driver launched.")
    october_dates = generate_date_range(start_date, end_date)
    print(f"Generated {len(october_dates)} date pairs for October 2025.")
    try:
        for h_index, hotel in enumerate(hotels, 1):
            base_url = hotel["url"]
            hotel_id = hotel["id"]
            print(f"\n==================== HOTEL {h_index}/{len(hotels)}: {hotel['name']} ====================")

            for i, (checkin, checkout) in enumerate(october_dates):
                url = generate_hotel_url(base_url, hotel_id, checkin, checkout)
                print(f"\n-- {hotel['name']} | {checkin} to {checkout} ({i+1}/{len(october_dates)}) --")
                print(f"URL: {url}")
                driver.get(url)

                # wait_for_human_verification(driver)

                # Get hotel name (fresh each time)
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.uitk-heading'))
                    )
                    soup_name = BeautifulSoup(driver.page_source, "html.parser")
                    hotel_name_elem = soup_name.select_one('h1.uitk-heading')
                    hotel_name = hotel_name_elem.get_text(strip=True) if hotel_name_elem else hotel["name"]
                except:
                    hotel_name = hotel["name"]

                rooms = extract_room_data(driver, checkin, checkout, hotel_id, hotel_name, url)
                if rooms:
                    all_data.extend(rooms)
                delay = random.uniform(8, 15)
                print(f"Waiting {delay:.1f} seconds before next request...")
                time.sleep(delay)

            # Pause for manual verification before next hotel
            if h_index < len(hotels):
                next_hotel = hotels[h_index]["name"]
                print(f"\n{'='*80}")
                print(f"✅ Completed scraping for: {hotel['name']}")
                print(f"📊 Total records collected so far: {len(all_data)}")
                print(f"➡️ Next hotel: {next_hotel}")
                print(f"{'='*80}")
                # response = input("Press Enter to continue to the next hotel, or type 'quit' to stop: ").strip().lower()
                # if response == 'quit':
                #     break
                global first_run
                first_run = True

    finally:
        driver.quit()
    return all_data

# ===================== SAVE ===================== #
def save_to_csv(data, filename):
    if not data:
        print("No data to save")
        return
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n✅ Data saved to {filename}")
    print(f"Total records: {len(df)}")

# # ===================== MAIN ===================== #
# if __name__ == "__main__":
#     hotels = []
#     for name, sources in hotel_mapping.items():
#         if "expedia" in sources:
#             expedia_data = sources["expedia"]
#             hotels.append({
#                 "name": name.replace("_", " ").title(),
#                 "id": expedia_data["hotel_id"],   # EXPEDIA_*
#                 "url": expedia_data["url"]
#             })

#     data = scrape_hotels(hotels)
#     save_to_csv(data, "expedia_hotels.csv")

