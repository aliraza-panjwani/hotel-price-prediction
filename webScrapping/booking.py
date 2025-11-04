from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time, re
import pandas as pd
from bs4 import BeautifulSoup
try:
    from webScrapping.mapping import hotel_mapping 
except:
    from mapping import hotel_mapping
from urllib.parse import urlparse


def load_soup(url):
    opts = Options()  # run browser in headless mode
    opts.add_argument("--window-size=1920,1080")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=opts)
    driver.get(url)
    time.sleep(5)  # allow time for JS-driven content to load
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    
    return soup


def generate_date_ranges(start_date, end_date):
    """Generate consecutive checkin/checkout date pairs."""
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    return [(dates[i].strftime("%Y-%m-%d"), dates[i+1].strftime("%Y-%m-%d"))
            for i in range(len(dates)-1)]

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

def get_all_hotel_details(hotel_url, checkin, checkout, adults=2, rooms=1):
    """
    Scrape details for ALL hotels in hotels_df.
    Returns a DataFrame with one row per hotel (with checkin/checkout).
    """

    # Clean URL & add params (force USD currency)
    url = (
        hotel_url.split("?")[0] +
        f"?checkin={checkin}&checkout={checkout}"
        f"&group_adults={adults}&no_rooms={rooms}&group_children=0"
        f"&selected_currency=IND"
    )
    soup = load_soup(url)
    # all_details = []

    # print(f"Scraping hotel details from: {url}")
    

    # --- Hotel Title ---
    hotel_title = soup.select_one("h2.pp-header__title, h2.d2fee87262.pp-header__title")
    hotel_title = hotel_title.get_text(strip=True) if hotel_title else None

    # --- Nearby Places ---
    nearby_places = {}
    section = soup.select_one("div[data-testid='property-section--content']")
    if section:
        for li in section.find_all("li"):
            spans = [span.get_text(strip=True) for span in li.find_all("span") if span.get_text(strip=True)]
            divs = [div.get_text(strip=True) for div in li.find_all("div") if div.get_text(strip=True)]
            for i in range(max(len(spans), len(divs))):
                key = spans[i] if i < len(spans) else None
                value = divs[i] if i < len(divs) else None
                if key:
                    nearby_places[key] = value

    # --- Amenities ---
    amenities = {}
    amenity_sections = soup.select("div[data-testid='property-most-popular-facilities-wrapper']")
    for item in amenity_sections:
        text = item.get_text(strip=True)
        if ":" in text:
            k, v = text.split(":", 1)
            amenities[k.strip()] = v.strip()
        else:
            amenities[text] = True

    # --- Reviews ---
    review_text = soup.select_one("div[data-testid='review-score-component'] span")
    review_text = review_text.get_text(strip=True) if review_text else None

    review_span = soup.select_one("span.f63b14ab7a.fb14de7f14.eaa8455879")
    review_numbers = review_span.get_text(strip=True) if review_span else None

    rating = soup.select_one("div[data-testid='review-score-component'] div")
    rating = rating.get_text(strip=True) if rating else None

    # --- Stars ---
    stars_elem = soup.select_one("span[data-testid='rating-stars']")
    stars = None
    if stars_elem and stars_elem.has_attr("aria-label"):
        match = re.search(r"(\d+) out of \d+ stars", stars_elem["aria-label"])
        if match:
            stars = int(match.group(1))

    # --- Address ---
    address = None
    map_anchor = soup.find("a", id="map_trigger_header_pin")
    if map_anchor:
        next_elem = map_anchor.find_next_sibling(["span", "div"])
        if next_elem:
            address = next_elem.get_text(" ", strip=True)
    if not address:
        address_elem = soup.select_one("span.hp_address_subtitle, span[data-testid='PropertyHeaderAddressDesktop-wrapper']")
        if address_elem:
            address = address_elem.get_text(" ", strip=True)

    # --- Description ---
    description_elem = soup.select_one("div#property_description_content")
    description = description_elem.get_text(" ", strip=True) if description_elem else None


    return{
        "hotel_title": hotel_title,
        "near_by_places": nearby_places,
        "amenities": amenities,
        "review_text": review_text,
        "review_numbers": review_numbers,
        "rating": rating,
        "stars": stars,
        "address": address,
        "description": description,
        # "checkin": checkin,
        # "checkout": checkout
    }

def extract_hotel_name_from_url(url):
    """Extract clean hotel name from Agoda URL path."""
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2:
        raw_name = path_parts[1]  # example: 'econo-lodge_2'
        hotel_name = re.sub(r"[_\d-]+", " ", raw_name).strip().title()
        return hotel_name
    return None

def clean_price(text):
    if not text or text.strip() == "":
        return "Sold Out"
    # Normalize to INR
    cleaned_text = re.sub(r'[^\d.]', '', text)
    
    if cleaned_text:
        return float(cleaned_text)
    return None

def get_room_info(hotel_url, start_date, end_date, adults=2, rooms=1):
    """
    Scrape room details for multiple date ranges (expanded).
    Returns DataFrame with checkin/checkout columns and USD prices.
    """
    all_room_data = []
    date_pairs = generate_date_ranges(start_date, end_date)

    for (checkin, checkout) in date_pairs:
        # force USD currency
        url = (
            f"{hotel_url.split('?')[0]}"
            f"?checkin={checkin}&checkout={checkout}"
            f"&group_adults={adults}&no_rooms={rooms}&group_children=0"
            f"&selected_currency=IND"
        )
        print("Processing URL:", url)
        soup = load_soup(url)

        # print(f"Scraping room details from: {url}")
        hotel_id, hotel_source = get_hotel_info_from_mapping(url)

        # ✅ Extract hotel name (with fallback)
        hotel_name_tag = soup.select_one("#hp_hotel_name")
        if hotel_name_tag:
            hotel_name = hotel_name_tag.get_text(strip=True)
        else:
            hotel_name = extract_hotel_name_from_url(hotel_url)

        room_data = {}
        room_rows = soup.select("tr.js-rt-block-row")

        for row in room_rows:
            try:
            # ---- Room Basic Info ----
                room_name = row.select_one(".hprt-roomtype-link span")
                room_name = room_name.get_text(strip=True) if room_name else "Unknown Room"

                bed_type = row.select_one(".rt-bed-type")
                print("Bed type raw:", bed_type,type(bed_type))
                bed_type = bed_type.get_text(strip=True) if bed_type else None
                if bed_type:
                    bed_type = re.sub(r'^\d+\s+', '', bed_type).strip()

                #alternative of 2nd hotel
                if not bed_type:
                    bed_type = row.select_one(".bedroom_bed_type")
                    bed_type = bed_type.get_text(strip=True) if bed_type else None
                    if bed_type:
                        bed_type = re.sub(r'^\d+\s+', '', bed_type).strip()

                facilities = [f.get_text(strip=True) for f in row.select(".hprt-facilities-facility span")]

                # ---- Available Rooms ----
                available_rooms_text = None

                # First selector
                tag = row.select_one(".thisRoomAvailabilityNew")
                if tag:
                    available_rooms_text = tag.get_text(strip=True)

                # Alternative selector if first is empty
                if not available_rooms_text:
                    for i in row.select(".bui-list__description"):
                        txt = i.get_text(strip=True)
                        if "we have" in txt.lower() or "only" in txt.lower():
                            available_rooms_text = txt
                            break

                # Extract only the number from text
                if available_rooms_text:
                    match = re.search(r'\d+', available_rooms_text)
                    available_rooms = int(match.group()) if match else 0
                else:
                    available_rooms = 0

                # ---- Breakfast Info ----
                # breakfast_elem = row.find(text=re.compile(r'Breakfast', re.IGNORECASE))
                # breakfast = True if breakfast_elem else False


                base_price = row.select_one(".prco-valign-middle-helper").text
                base_price = clean_price(base_price)
                tax_price = row.select_one(".prd-taxes-and-fees-under-price").text
                tax_price = clean_price(tax_price)

                total_price = base_price+tax_price
                # choice = {
                #     "base_price": base_price,
                #     "tax_price": tax_price,
                #     "total_price": base_price
                # }


                # ---- Grouping Logic ----
                if room_name not in room_data:
                    room_data[room_name] = {
                        "hotel_id": hotel_id,
                        "hotel_source": hotel_source,
                        "hotel_name": hotel_name,
                        "room_name": room_name,
                        "bed_type": bed_type,
                        "bed_category": classify_room_and_bed(room_name, bed_type)[0],
                        "room_category": classify_room_and_bed(room_name, bed_type)[1],
                        # "breakfast_included": breakfast,
                        # "refundable_info": refundable_text, 
                        # "refundable_charges": refundable_charges,
                        "available_rooms": available_rooms,
                        "room_facilities": facilities,
                        "base_price" : base_price,
                        "tax_price" : tax_price,
                        "total_price" : total_price,
                        "checkin": checkin,
                        "checkout": checkout
                    }

            except Exception as e:
                print("Room parse error:", e)

        # Add this date pair’s rooms into final list
        all_room_data.extend(room_data.values())

    df = pd.DataFrame(all_room_data)

    # 🚀 Filter out "Unknown Room" rows
    df = df[df["room_name"] != "Unknown Room"].reset_index(drop=True)

    return df

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

def scrape_hotels_and_rooms(hotel_urls, start_date, end_date, adults=2, rooms=1,fileName_prefix="./"):
    """
    Main function → Scrape hotel details + room details for multiple hotels.
    Returns: (hotels_df, rooms_df)
    """
    hotel_details = []
    all_rooms = []

    for url in hotel_urls:
        # Hotel details (only once → no checkin/checkout)
        hotel_details.append(get_all_hotel_details(url, start_date, end_date, adults, rooms))

        # Room details (multiple date pairs → includes checkin/checkout)
        room_df = get_room_info(url, start_date, end_date, adults, rooms)
        room_df["hotel_url"] = url
        all_rooms.append(room_df)

    hotels_df = pd.DataFrame(hotel_details)
    rooms_df = pd.concat(all_rooms, ignore_index=True) if all_rooms else pd.DataFrame()

    # Save outputs to CSV
    hotels_df.to_csv(fileName_prefix+"/hotel_info.csv", index=False, encoding="utf-8-sig")
    rooms_df.to_csv(fileName_prefix+"/room_info.csv", index=False, encoding="utf-8-sig")


    return hotels_df, rooms_df


# ---------- Example Run ----------
# hotel_urls = [
#     "https://www.booking.com/hotel/us/hotel-south-middle-street-frackville.en-gb.html?aid=311984&label=hotel-south-middle-street-frackville-0s5BKYBc4PAtRSy1Mf27vAS718104141763%3Apl%3Ata%3Ap1%3Ap2%3Aac%3Aap%3Aneg%3Afi%3Atikwd-784489940811%3Alp1007753%3Ali%3Adec%3Adm%3Appccp%3DUmFuZG9tSVYkc2RlIyh9YboIMJYQAPicrzwdxpGM5o8&sid=60e8984aee2dcaa3d5c6bb0582a2baa0&all_sr_blocks=49125801_383586274_2_0_0&{checkin}&{checkout}&dest_id=20108302&dest_type=city&dist=0&group_adults=2&group_children=0&hapos=1&highlighted_blocks=49125801_383586274_2_0_0&hpos=1&matching_block_id=49125801_383586274_2_0_0&no_rooms=1&req_adults=2&req_children=0&room1=A%2CA&sb_price_type=total&sr_order=popularity&sr_pri_blocks=49125801_383586274_2_0_0__199000&srepoch=1758876428&srpvid=56a03dc18c4800ea&type=total&ucfs=1&",
#     "https://www.booking.com/hotel/us/best-western-plover.html?aid=356980&label=gog235jc-10CAso7AFCE2Jlc3Qtd2VzdGVybi1wbG92ZXJIM1gDaGyIAQGYATO4ARfIAQzYAQPoAQH4AQGIAgGoAgG4ArOn2cYGwAIB0gIkZGE5ZTg3ODUtNjE2ZS00NmRmLWI2ZTgtZWRkYjk2MGI5Zjky2AIB4AIB&sid=60e8984aee2dcaa3d5c6bb0582a2baa0&age=0&all_sr_blocks=33582008_346789923_2_1_0&{checkin}&{checkout}&dest_id=20150908&dest_type=city&dist=0&group_adults=2&group_children=0&hapos=1&highlighted_blocks=33582008_346789923_2_1_0&hpos=1&matching_block_id=33582008_346789923_2_1_0&no_rooms=1&req_adults=2&req_children=0&room1=A%2CA&sb_price_type=total&sr_order=popularity&sr_pri_blocks=33582008_346789923_2_1_0__297178&srepoch=1758876602&srpvid=67973e1aa6eb02a8&type=total&ucfs=1&",
#     "https://www.booking.com/hotel/us/grand-season-inn-waupaca.html?aid=356980&label=gog235jc-10CAso7AFCGGdyYW5kLXNlYXNvbi1pbm4td2F1cGFjYUgzWANobIgBAZgBM7gBF8gBDNgBA-gBAfgBAYgCAagCAbgChfPexgbAAgHSAiRkNzI0NzBlYi00NzFmLTRjNDItYjBkYy1mODg5ZjU5YjY3NTfYAgHgAgE&sid=60e8984aee2dcaa3d5c6bb0582a2baa0&age=0&all_sr_blocks=42704214_93753437_2_1_0&{checkin}&{checkout}&dest_id=20151464&dest_type=city&dist=0&group_adults=2&group_children=0&hapos=1&highlighted_blocks=42704214_93753437_2_1_0&hpos=1&matching_block_id=42704214_93753437_2_1_0&no_rooms=1&req_adults=2&req_children=0&room1=A%2CA&sb_price_type=total&sr_order=popularity&sr_pri_blocks=42704214_93753437_2_1_0__35840&srepoch=1758968204&srpvid=af404843c8f000e2&type=total&ucfs=1&",
#     "https://www.booking.com/hotel/us/grand-season-inn-waupaca.html?aid=356980&label=gog235jc-10CAso7AFCGGdyYW5kLXNlYXNvbi1pbm4td2F1cGFjYUgzWANobIgBAZgBM7gBF8gBDNgBA-gBAfgBAYgCAagCAbgChfPexgbAAgHSAiRkNzI0NzBlYi00NzFmLTRjNDItYjBkYy1mODg5ZjU5YjY3NTfYAgHgAgE&sid=60e8984aee2dcaa3d5c6bb0582a2baa0&age=0&all_sr_blocks=42704214_93753437_2_1_0&{checkin}&{checkout}&dest_id=20151464&dest_type=city&dist=0&group_adults=2&group_children=0&hapos=1&highlighted_blocks=42704214_93753437_2_1_0&hpos=1&matching_block_id=42704214_93753437_2_1_0&no_rooms=1&req_adults=2&req_children=0&room1=A%2CA&sb_price_type=total&sr_order=popularity&sr_pri_blocks=42704214_93753437_2_1_0__35840&srepoch=1758968204&srpvid=af404843c8f000e2&type=total&ucfs=1&",
#     "https://www.booking.com/hotel/us/la-quinta-stevens-point.html?aid=356980&label=gog235jc-10CAso7AFCF2xhLXF1aW50YS1zdGV2ZW5zLXBvaW50SDNYA2hsiAEBmAEzuAEXyAEM2AED6AEB-AEBiAIBqAIBuAKMm-PGBsACAdICJGExMGU1OTMwLWJmNzUtNDVmZi05ODAxLWU1OGQ0YzA1YzI4NdgCAeACAQ&sid=b4a3f7b31a243b80f8ac20db0073a78a&all_sr_blocks=46222902_147737010_2_1_0&{checkin}&{checkout}&dest_id=20151269&dest_type=city&dist=0&group_adults=2&group_children=0&hapos=1&highlighted_blocks=46222902_147737010_2_1_0&hpos=1&matching_block_id=46222902_147737010_2_1_0&no_rooms=1&req_adults=2&req_children=0&room1=A%2CA&sb_price_type=total&sr_order=popularity&sr_pri_blocks=46222902_147737010_2_1_0__39336&srepoch=1759038870&srpvid=385d29875e1b02cd&type=total&ucfs=1&"
# ]

# Pick all Agoda URLs
# hotel_urls = [details["booking"]["url"] for hotel, details in hotel_mapping.items()]

# hotels_df, rooms_df = scrape_hotels_and_rooms(
#     hotel_urls,
#     start_date="2025-11-01",
#     end_date="2025-11-05",
#     adults=2,
#     rooms=1
# )

# print("Hotels:\n", hotels_df.head())
# print("Rooms:\n", rooms_df.head())
