import pandas as pd

def merge_hotel_files(file1, file2,file3, output_file="merged_room_info.csv"):
    # Load both CSV files
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    df3 = pd.read_csv(file3)

    # ✅ Add hotel_id with unique prefix
    # df1["hotel_id"] = "AGODA_" + (df1.index + 1).astype(str)
    # df2["hotel_id"] = "BOOKING_" + (df2.index + 1).astype(str)
    # df3["hotel_id"] = "EXPEDIA_" + (df3.index + 1).astype(str)

    # Standardize column names in Agoda file
    df1 = df1.rename(columns={
        "base_price_usd": "base_price",
        "tax_price_usd": "tax_price",
        "total_price_usd": "total_price"
    })

    df3 = df3.rename(columns={
        "check_in": "checkin",
        "check_out": "checkout"
    })


    # Merge (stack) rows
    merged_df = pd.concat([df1, df2, df3], ignore_index=True)

    # Save to CSV
    merged_df.to_csv(output_file, index=False)

    print(f"✅ Files merged successfully! Saved as {output_file}")


# Example usage (replace with your file paths)
# merge_hotel_files("agoda_room_info.csv", "room_info.csv", "expedia_hotels.csv", "final_merged_hotels.csv")

