import pandas as pd

df1 = pd.read_csv("data/price_table_dropna.csv")
df2 = pd.read_csv("data/price_table_dropna_old.csv")

print("DF1 shape:", df1.shape)
print("DF2 shape:", df2.shape)

merged_df = df1.join(df2.set_index('checkin_date'), on='checkin_date', how='outer')

print("Merged DF shape:", merged_df.shape)
merged_df.to_csv("data/merged_price_table.csv", index=False)