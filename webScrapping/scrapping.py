import time
import pandas as pd
try:
    from .mapping import hotel_mapping
    from webScrapping import agoda_test, booking, expedia, merge, process
except:
    from mapping import hotel_mapping
    import agoda_test, booking, expedia, merge, process
import os

def run_full_scraping_process(start_date, end_date, output_dir="./data/scrapped"):
    """
    Orchestrates the entire scraping and merging process by calling
    the main functionalities from the other scripts in sequence.
    """
    print("🚀 STARTING AUTOMATED SCRAPING & MERGING PROCESS 🚀")
    print("="*60)
    doneSteps = []
    gotError = {}

    start_time = time.time()
    
    # --- STEP 1: SCRAPE AGODA DATA ---
    try:
        print("\n[1/4] ▶️  Running Agoda Scraper...")
        # Get Agoda URLs from the mapping file
        agoda_urls = [details["agoda"]["url"] for hotel, details in hotel_mapping.items()]
        print("** Agoda URLs to scrape:", len(agoda_urls))
        # Call the main scraping function from agoda_test.py
        _, agoda_rooms_df = agoda_test.scrape_hotels_and_rooms_agoda(
            hotel_urls2=agoda_urls,
            start_date=start_date,
            end_date=end_date,
            adults=2,
            rooms=1
        )
        
        # Save the collected data to its CSV file
        agoda_rooms_df.to_csv(output_dir+"/agoda_room_info.csv", index=False, encoding="utf-8-sig")
        print("✅ Agoda scraping complete. Data saved to 'agoda_room_info.csv'.")
        doneSteps.append(output_dir+"/agoda_room_info.csv")
    except Exception as e:
        gotError["agoda"] = str(e)
        print(f"❌ ERROR during Agoda scraping: {e}")

    print("="*60)
    
    # --- STEP 2: SCRAPE BOOKING.COM DATA ---
    try:
        print("\n[2/4] ▶️  Running Booking.com Scraper...")
        # Get Booking.com URLs from the mapping file
        booking_urls = [details["booking"]["url"] for hotel, details in hotel_mapping.items()]
        
        # Call the main scraping function from booking.py
        # This function handles saving the files internally.
        booking.scrape_hotels_and_rooms(
            hotel_urls=booking_urls,
            start_date=start_date,
            end_date=end_date,
            adults=2,
            rooms=1,
            fileName_prefix=output_dir,
        )
        print("✅ Booking.com scraping complete. Data saved to 'room_info.csv' and 'hotel_info.csv'.")
        doneSteps.append(output_dir+"/room_info.csv")
    except Exception as e:
        gotError["booking"] = str(e)
        print(f"❌ ERROR during Booking.com scraping: {e}")
        
    print("="*60)

    # --- STEP 3: SCRAPE EXPEDIA DATA ---
    try:
        print("\n[3/4] ▶️  Running Expedia Scraper...")
        # Prepare the hotel list in the format required by expedia.py
        expedia_hotels = []
        for name, sources in hotel_mapping.items():
            if "expedia" in sources:
                expedia_data = sources["expedia"]
                expedia_hotels.append({
                    "name": name.replace("_", " ").title(),
                    "id": expedia_data["hotel_id"],
                    "url": expedia_data["url"]
                })
        print("** Expedia hotels to scrape:", len(expedia_hotels))
        # Call the main functions from expedia.py
        scraped_data = expedia.scrape_hotels(expedia_hotels, start_date, end_date)
        expedia.save_to_csv(scraped_data, output_dir+"/expedia_hotels.csv")
        print("✅ Expedia scraping complete. Data saved to 'expedia_hotels.csv'.")
        doneSteps.append(output_dir+"/expedia_hotels.csv")
    except Exception as e:
        gotError["expedia"] = str(e)
        print(f"❌ ERROR during Expedia scraping: {e}")
        
    print("="*60)
    
    # --- STEP 4: MERGE ALL DATA FILES ---
    try:
        print("\n[4/4] ▶️  Merging all CSV files...")
        # Call the merge function from merge.py
        merge.merge_hotel_files(
            file1=output_dir+"/agoda_room_info.csv",
            file2=output_dir+"/room_info.csv",        # From Booking.com
            file3=output_dir+"/expedia_hotels.csv",
            output_file=output_dir+"/final_merged_hotels.csv"
        )
        # The merge function prints its own success message.
        doneSteps.append(output_dir+"/final_merged_hotels.csv")
    except Exception as e:
        gotError["merging"] = str(e)
        print(f"❌ ERROR during file merging: {e}")
        
    print("="*60)
    total_time = time.time() - start_time
    print(f"🎉 AUTOMATION COMPLETE! 🎉")
    print(f"Total execution time: {total_time:.2f} seconds.")
    print("The final combined data is available in 'final_merged_hotels.csv'.")
    return doneSteps, gotError, total_time

def starScrapping(start_date, end_date):
    if os.path.exists("./data/price_table_dropna_Scrapped.csv"):
        # merge with ./data/price_table_dropna.csv and delete ./data/price_table_dropna_Scrapped.csv
        df_existing = pd.read_csv("./data/price_table_dropna.csv")
        df_scrapped = pd.read_csv("./data/price_table_dropna_Scrapped.csv")
        df_merged = pd.merge(df_existing, df_scrapped, on=["hotel_name", "checkin_date"], how="left", suffixes=('_existing', '_scrapped'))
        df_merged.to_csv("./data/price_table_dropna.csv", index=False)
        os.remove("./data/price_table_dropna_Scrapped.csv")

    print("Starting the full scraping process...")
    doneSteps, gotError, total_time = run_full_scraping_process(start_date=start_date, end_date=end_date,output_dir="./data/scrapped")
    print("Processing the scraped data...")
    result = process.hotel_process(hotel_path="./data/scrapped/final_merged_hotels.csv",
                          output_path="./data/price_table_dropna_Scrapped.csv")
    print("Data processing complete.")
    return {
        "status": "completed",
        "message": "Scraping and merging process completed.",
        "doneSteps": doneSteps,
        "gotError": gotError,
        "processed_file": "./data/price_table_dropna.csv",
        "total_time_seconds": total_time
    }

if __name__ == "__main__":
    import os 
    if not os.path.exists("./data/scrapped"):
        os.makedirs("./data/scrapped")
    run_full_scraping_process("2025-11-10", "2025-11-23", output_dir="./data/scrapped")