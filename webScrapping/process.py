import pandas as pd
from datetime import datetime, timedelta
from functools import reduce
import numpy as np

def hotel_data(hotel_df, hotel_id = "americinn-of-new-london"):
    th = hotel_df[hotel_df["hotel_id"] == hotel_id]
    hotel_name = "-".join(th[th['hotel_source'] == 'agoda']["hotel_name"].iloc[0].lower().split())
    th['checkin'] = pd.to_datetime(th['checkin'])  # not needed
    th['checkout'] = pd.to_datetime(th['checkout'])
    th2 = th[(th['checkout'] - th['checkin']).dt.days <= 1] # remove long days
    th3 = th2.loc[th2.groupby('checkin')['total_price'].idxmin()][["checkin","available_rooms","total_price"]]
    th3.columns = ["checkin_date",hotel_name+"_"+th3.columns[1],hotel_name+"_"+th3.columns[2]]
    return th3

def hotel_process(hotel_path = r"final_merged_hotels.csv",output_path = r"price_table_dropna.csv"):
    hotel = pd.read_csv(hotel_path)
    print(hotel.shape)
    hotel["hotel_id"] = [i.split("_")[-1] for i in hotel["hotel_id"]]
    hotel1 = hotel[hotel['room_category'] == "Normal"]
    hotel2 = hotel1[hotel1['bed_category'] == hotel1["bed_category"].value_counts().keys()[0]]
    print(hotel2.shape)
    hotel2['available_rooms'] = hotel2['available_rooms'].replace(0, np.nan)
    
    hotels = [hotel_data(hotel2, hotel_id = i) for i in set(hotel2["hotel_id"])]
    merged_df = reduce(lambda left, right: pd.merge(left, right, on='checkin_date', how='outer'), hotels)
    print(merged_df.shape)
    merged_df = merged_df.interpolate(method='linear')
    merged_df.to_csv(output_path,index=False)
    return merged_df

# mdf = hotel_process()
# print(mdf.head())
if __name__ == "__main__":
    hotel_process(hotel_path=r"C:\Old data\Projects\Forcasting\FullProject\hotel-price-prediction\webScrapping\data\scrapped\final_merged_hotels.csv",output_path="./data/price_table_dropna.csv")