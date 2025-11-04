from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time, re
import pandas as pd
from bs4 import BeautifulSoup
try:
    from webScrapping.mapping import hotel_mapping 
except:
    from mapping import hotel_mapping
from webdriver_manager.chrome import ChromeDriverManager


def load_soup(url):
    opts = Options()  # run browser in headless mode
    opts.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.get(url)
    try:
        # Wait for the initial room grid to be present
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#roomGridContent"))
        )
        print("✅ Room grid loaded.")
    except Exception as e:
        print(f"⚠️ Room grid not loaded within timeout: {e}")
        driver.quit()
        return None

    # --- Smarter Scrolling Logic ---
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll to the bottom of the page
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        
        # Wait for new content to load
        time.sleep(3) # A short wait for the page to react to the scroll
        
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # If heights are the same, it means no new content was loaded, so we can break
            print("✅ Reached the end of the page.")
            break
        last_height = new_height

    # Final wait to ensure everything is rendered
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    
    return soup

def extract_hotel_name_from_url(url):
    """Extract clean hotel name from Agoda URL path."""
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2:
        raw_name = path_parts[1]  # example: 'econo-lodge_2'
        hotel_name = re.sub(r"[_\d-]+", " ", raw_name).strip().title()
        return hotel_name
    return None


def generate_date_ranges(start_date, end_date):
    """Generate consecutive checkin/checkout date pairs"""
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    return [(dates[i].strftime("%Y-%m-%d"), dates[i+1].strftime("%Y-%m-%d"))
            for i in range(len(dates)-1)]

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def url_builder(hotel_url, adults, checkin, checkout, currency="USD"):
    # Calculate LOS
    los = (pd.to_datetime(checkout) - pd.to_datetime(checkin)).days
    
    # --- Parse and update ---
    parsed = urlparse(hotel_url)
    query_params = parse_qs(parsed.query)
    
    # Update dynamic fields
    query_params["adults"] = [str(adults)]
    query_params["checkIn"] = [checkin]
    query_params["currencyCode"] = [currency]
    query_params["los"] = [str(los)]

    # Remove any INR remnants
    if "currencyCode" in query_params and query_params["currencyCode"][0] != "USD":
        query_params["currencyCode"] = ["USD"]
    
    # Rebuild URL
    new_query = urlencode(query_params, doseq=True)
    final_url = urlunparse(parsed._replace(query=new_query))
    
    print("\nfinal_url: ",final_url)
    return final_url


def get_all_hotel_details(hotel_url, checkin, checkout, adults=2, rooms=1):
    """Scrape general hotel details"""
    url = url_builder(hotel_url, adults=adults, checkin=checkin, checkout=checkout, currency="USD")
    soup = load_soup(url)
    print("Soup loaded for hotel details.", url,soup is None)
    # Hotel Title
    hotel_title = soup.select_one("h1[data-selenium='hotel-header-name']")
    hotel_title = hotel_title.get_text(strip=True) if hotel_title else None

    # Nearby places
    nearby_places = {}
    landmarks_container = soup.select_one("div[data-element-name='nearby-location-box']")
    if landmarks_container:
        landmark_items = landmarks_container.select("div[data-testid='drone-box']")
        for item in landmark_items:
            data_divs = [div.get_text(strip=True) for div in item.find_all('div', recursive=False) if div.get_text(strip=True)]
            if len(data_divs) >= 2:
                name = data_divs[0]
                distance = data_divs[-1]
                nearby_places[name] = distance

    # Amenities
    amenities = [item.get_text(strip=True) for item in soup.select("div[data-element-name='atf-top-amenities-item']")]

    # Rating & reviews
    rating, review_text = None, None
    rating_element = soup.find("span", string=re.compile(r'^\d\.\d$'))
    if rating_element:
        rating = rating_element.get_text(strip=True)
        review_text_element = rating_element.find_next_sibling("span")
        if review_text_element:
            review_text = review_text_element.get_text(strip=True)

    review_number_tag = soup.select_one("span[data-testid='text']")
    review_numbers = review_number_tag.get_text(strip=True) if review_number_tag else None

    # Stars
    stars_tag = soup.select_one("[data-testid='star-rating-container']")
    stars = stars_tag.get_text(strip=True) if stars_tag else None

    # Address
    address_tag = soup.select_one(".Spanstyled__SpanStyled-sc-16tp9kb-0.gwICfd.kite-js-Span.HeaderCerebrum__Address")
    address = address_tag.get_text(strip=True) if address_tag else None

    return {
        "hotel_title": hotel_title,
        "near_by_places": nearby_places,
        "amenities": amenities,
        "review_text": review_text,
        "review_numbers": review_numbers,
        "rating": rating,
        "stars": stars,
        "address": address
    }


def scrape_agoda_room_details(hotel_url, checkin, checkout, adults=2, rooms=1):
    """Scrape room-level details for a given hotel & date pair"""

    url = url_builder(hotel_url, adults=adults, checkin=checkin, checkout=checkout, currency="USD")
    soup = load_soup(url)
    rooms_list = []
    if soup is None:
        print("❌ Skipping — Page not loaded properly")
        return pd.DataFrame(rooms_list)
    room_cards = soup.select(".MasterRoom")
    
    for card in room_cards:
            # --- Room Name and Bed Type ---
            room_name_tag = card.select_one(".MasterRoom-headerTitle--text")
            full_room_name = room_name_tag.get_text(strip=True) if room_name_tag else None
            room_name = full_room_name.split("Recommended")[0].strip()

            hotel_id, hotel_source = get_hotel_info_from_mapping(url)

            # ✅ Extract hotel name (with fallback)
            hotel_name_tag = soup.select_one("h1[data-selenium='hotel-header-name']")
            if hotel_name_tag:
                hotel_name = hotel_name_tag.get_text(strip=True)
            else:
                hotel_name = extract_hotel_name_from_url(hotel_url)

            bed_type = None
            facilities = []

            # # 1. Get ALL amenity/facility items from the list
            amenity_items = card.select(".MasterRoom-amenities")
        
            # This logic is correct and will now work!
            for item in amenity_items:
                text = item.get_text(strip=True)
                
                # Use regex to see if this line is the specific bed description
                bed_match = re.search(r'\d+\s+(king|queen|double|single|twin)\s+beds?', text, re.IGNORECASE)
                
                if bed_match:
                    # If it matches the bed pattern, assign it to bed_type
                    bed_type = bed_match.group(0)
                    bed_type = re.sub(r'^\d+\s+', '', bed_type).strip()
                else:
                    # If it's anything else, add it to the facilities list
                    facilities.append(text)

            facilities = [item_am.get_text(strip=True) 
            for item_am in card.select("ul.MasterRoom-amenities div.MasterRoom-amenitiesTitle")]
            

            available_tag = card.select_one("[data-testid='book-button-urgency-text']")
            available_text = available_tag.get_text(strip=True) if available_tag else None

            if available_text:
                match = re.search(r'\d+', available_text)
                available_rooms = int(match.group()) if match else 0
            else:
                available_rooms = 0

            base_price_tag = card.select_one(".Typographystyled__TypographyStyled-sc-j18mtu-0.gGXIen.kite-js-Typography.finalPrice")
            base_price_text = base_price_tag.get_text(strip=True) if base_price_tag else None
            base_price_match = re.search(r"[\d,]+", base_price_text) if base_price_text else None
            base_price = int(base_price_match.group().replace(",", "")) if base_price_match else None

            tax_price = 0  # Agoda often includes taxes in the base price

            total_price_tag = card.select_one(".Typographystyled__TypographyStyled-sc-j18mtu-0.gGXIen.kite-js-Typography.finalPrice")
            total_price_text = total_price_tag.get_text(strip=True) if total_price_tag else None
            total_price_match = re.search(r"[\d,]+", total_price_text) if total_price_text else None
            total_price = int(total_price_match.group().replace(",", "")) if total_price_match else None

            rooms_list.append({
            "hotel_id": hotel_id,
            "hotel_source": hotel_source,
            "hotel_name": hotel_name,
            "room_name": room_name,
            "bed_type": bed_type,
            "bed_category": classify_room_and_bed(room_name, bed_type)[0],
            "room_category": classify_room_and_bed(room_name, bed_type)[1],
            "available_rooms": available_rooms,
            "base_price_usd": base_price,
            "tax_price_usd": tax_price,
            "total_price_usd": total_price,
            "room_facilities": facilities,
            "checkin": checkin,
            "checkout": checkout
        })

    return pd.DataFrame(rooms_list)

def normalize_url(url):
    parsed = urlparse(url)
    # Only scheme + netloc + path (ignore query, fragment)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

def get_hotel_info_from_mapping(url):
    """Find hotel_id + source by matching normalized base URL."""
    parsed_base = normalize_url(url)

    for h_name, h_data in hotel_mapping.items():
        for source in ["agoda", "booking"]:
            mapped_base = normalize_url(h_data[source]["url"])
            if parsed_base == mapped_base:
                return h_data[source]["hotel_id"], source
    return None, None

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

def scrape_hotels_and_rooms_agoda(hotel_urls2, start_date, end_date, adults=2, rooms=1):
    """
    Main function → Scrape hotel details + room details for multiple hotels.
    Returns: (hotels_df, rooms_df)
    """
    hotel_details = []
    all_rooms_data = []

    # This will generate the date pairs like ('2025-11-01', '2025-11-02'), etc.
    date_pairs = generate_date_ranges(start_date, end_date)

    for url in hotel_urls2:
        print(f"\n--- Scraping Hotel: {url.split('?')[0]} ---")
        
        # Get hotel-level details (only needs to be done once per hotel)
        # We can use the first check-in date for this
        first_checkin, first_checkout = date_pairs[0]
        hotel_info = get_all_hotel_details(url, first_checkin, first_checkout, adults, rooms)
        hotel_info["hotel_url"] = url
        hotel_details.append(hotel_info)

        # CORRECTED LOGIC: Loop through each date pair for room details
        for checkin, checkout in date_pairs:
            print(f"  -> Scraping rooms for check-in: {checkin}")
            
            # Scrape rooms for this specific date pair
            rooms_for_date_df = scrape_agoda_room_details(url, checkin, checkout, adults, rooms)
            
            # Add hotel_url to the DataFrame for easy reference
            if not rooms_for_date_df.empty:
                rooms_for_date_df["hotel_url"] = url
                all_rooms_data.append(rooms_for_date_df)

    hotels_df = pd.DataFrame(hotel_details)
    
    # Concatenate all the room DataFrames from all dates and hotels
    if all_rooms_data:
        rooms_df = pd.concat(all_rooms_data, ignore_index=True)
    else:
        rooms_df = pd.DataFrame()

    #save outputs to CSV
    # hotels_df.to_csv("agoda_hotel_info.csv", index=False, encoding="utf-8-sig")
    # rooms_df.to_csv("agoda_room_info.csv", index=False, encoding="utf-8-sig")

    return hotels_df, rooms_df


# ---------- Example Run ----------
# hotel_urls2 = ["https://www.agoda.com/econo-lodge_2/hotel/mount-laurel-nj-us.html?countryId=181&finalPriceView=1&isShowMobileAppPrice=false&cid=-1&numberOfBedrooms=&familyMode=false&adults=2&children=0&rooms=1&maxRooms=0&checkIn=2025-11-1&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=1&showReviewSubmissionEntry=false&currencyCode=INR&isFreeOccSearch=false&los=4&searchrequestid=054e8861-9dbe-4d30-a873-69fffa1fe3d6&ds=CH3TEme3dqOaFa9f",
#         "https://www.agoda.com/americas-best-value-inn-new-london_4/hotel/new-london-wi-us.html?countryId=181&finalPriceView=1&isShowMobileAppPrice=false&cid=-1&numberOfBedrooms=&familyMode=false&adults=2&children=0&rooms=1&maxRooms=0&checkIn=2025-11-1&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=1&showReviewSubmissionEntry=false&currencyCode=INR&isFreeOccSearch=false&tspTypes=8&los=4&searchrequestid=88693a4b-7fef-4a69-9b08-650154e6aa7b&ds=CH3TEme3dqOaFa9f"
# ]

# Pick all Agoda URLs
# hotel_urls2 = [details["agoda"]["url"] for hotel, details in hotel_mapping.items()]

# hotels_df, rooms_df = scrape_hotels_and_rooms_agoda(
#     hotel_urls2,
#     start_date="2025-11-01",
#     end_date="2025-11-05",
#     adults=2,
#     rooms=1
# )

# print("Hotels:\n", hotels_df.head())
# print("Rooms:\n", rooms_df.head())

# #In room i show all the column properly
# rooms_df.to_csv("agoda_room_info.csv", index=False, encoding="utf-8-sig")