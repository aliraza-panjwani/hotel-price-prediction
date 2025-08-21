import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from utils.api_utils import fetch_prediction
import requests

# Constants
DATA_PATH = "data/price_table_dropna.csv"
API_URL = "http://127.0.0.1:5000/predict"

# Load data
@st.cache_data  
def load_data():
    return pd.read_csv(DATA_PATH, parse_dates=["checkin_date"])

df = load_data()

# Page navigation
st.set_page_config(page_title="Hotel Price Dashboard", layout="wide")
page = st.sidebar.radio("Pages", ["Dashboard", "Predict from API"])

# call register api
register_url = "/".join(API_URL.split("/")[:-1]+["register"])
print(register_url)
payload = {
    "target_hotel": "grand-season-inn-waupaca",
    "competitor_hotels": [
        "quality-inn-new-london-wisconsin",
        "motel-6-wisconsin-rapids",
        "valley-inn-neenah"
    ]
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(register_url, json=payload, headers=headers)
    print("Status Code:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Error:", str(e))


# ---------------- Dashboard ----------------
if page == "Dashboard":
    st.title("Hotel Price Analysis Dashboard")

    # Hotel selector for prediction
    price_cols = [col for col in df.columns if col.endswith("_price")]
    hotel_choice = st.selectbox("Select hotel to analyze", price_cols)
    
    # Prepare data
    df_sorted = df.sort_values("checkin_date")
    last_10_df = df_sorted.tail(20).copy()
    last_10_df["checkin_date"] = pd.to_datetime(last_10_df["checkin_date"])

    # Fetch predictions
    last_10_df["Predicted"] = None
    for i, row in last_10_df.iterrows():
        payload = {
            "predict_date": row["checkin_date"].strftime("%Y-%m-%d"),
            "vs_days": 1
        }
        response = fetch_prediction(API_URL, payload)
        if isinstance(response, dict) and "predicted_price" in response:
            last_10_df.at[i, "Predicted"] = response["predicted_price"]

    plot_df = last_10_df.dropna(subset=["Predicted"])

    # --- Chart 1: Actual vs Predicted for selected hotel ---
    st.subheader(f"Actual vs Predicted Prices for: {hotel_choice}")
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=plot_df, x="checkin_date", y=hotel_choice, label="Actual Price", marker="o", ax=ax)
    sns.lineplot(data=plot_df, x="checkin_date", y="Predicted", label="Predicted Price", marker="o", ax=ax)
    ax.set_title(f"{hotel_choice} - Last 10 Days")
    ax.set_ylabel("Price ($)")
    ax.set_xlabel("Check-in Date")
    ax.legend()
    st.pyplot(fig)

    # --- Chart 2: Compare Predicted with All Hotels ---
    st.subheader("Compare Predicted Price with All Hotels")
    fig2, ax2 = plt.subplots(figsize=(12, 4))
    sns.lineplot(data=plot_df, x="checkin_date", y="Predicted", label="Predicted Price", marker="o", linewidth=3, color="red", ax=ax2)

    for col in price_cols:
        if hotel_choice.strip() != col.strip():
            sns.lineplot(data=plot_df, x="checkin_date", y=col, label=col.replace("_price", ""), ax=ax2)

    ax2.set_title("Predicted vs Other Hotels (Last 10 Days)")
    ax2.set_ylabel("Price ($)")
    ax2.set_xlabel("Check-in Date")
    ax2.legend()
    st.pyplot(fig2)

    # Raw data
    if st.checkbox("Show raw data"):
        st.dataframe(plot_df[["checkin_date", "Predicted"] + price_cols])

# if page == "Dashboard":
#     st.title("Hotel Price Analysis Dashboard")

#     # Hotel selector
#     price_cols = [col for col in df.columns if col.endswith("_price")]
#     hotel_choice = st.selectbox("Select hotel to analyze", price_cols)

#     # Get last 10 rows sorted by date
#     df_sorted = df.sort_values("checkin_date")
#     last_10_df = df_sorted.tail(20).copy()

#     print(last_10_df.shape)
#     # Initialize predicted column
#     last_10_df["Predicted"] = None

#     # Fetch prediction from API for each date
#     st.info("Fetching predictions from API...")
#     for i, row in last_10_df.iterrows():
#         payload = {
#             "predict_date": row["checkin_date"].strftime("%Y-%m-%d"),
#             "vs_days": 1
#         }
#         response = fetch_prediction(API_URL, payload)
#         if isinstance(response, dict) and "predicted_price" in response:
#             last_10_df.at[i, "Predicted"] = response["predicted_price"]
#         else:
#             last_10_df.at[i, "Predicted"] = None  # or fallback value

#     # Drop rows without prediction
#     plot_df = last_10_df.dropna(subset=["Predicted"])
#     print(plot_df.shape)
#     # Plot actual vs predicted
#     st.subheader(f"Actual vs Predicted Prices for: {hotel_choice}")
#     fig, ax = plt.subplots(figsize=(10, 5))
#     sns.lineplot(data=plot_df, x="checkin_date", y=hotel_choice, label="Actual Price", marker="o", ax=ax)
#     sns.lineplot(data=plot_df, x="checkin_date", y="Predicted", label="Predicted Price", marker="o", ax=ax)
#     ax.set_title(f"{hotel_choice} - Last 10 Days")
#     ax.set_ylabel("Price ($)")
#     ax.set_xlabel("Check-in Date")
#     ax.legend()
#     st.pyplot(fig)

#     # Show raw data
#     if st.checkbox("Show raw data"):
#         st.dataframe(plot_df[["checkin_date", hotel_choice, "Predicted"]])


# ---------------- Prediction Section ----------------
elif page == "Predict from API":
    st.title("Predict Hotel Price using API")

    st.markdown(f"**POST** to: `{API_URL}`")

    # Select hotel
    price_cols = [col for col in df.columns if col.endswith("_price")]
    hotel_choice = st.selectbox("Select hotel", price_cols)

    # Available dates from CSV
    available_dates = df["checkin_date"].sort_values().dt.strftime('%Y-%m-%d').unique().tolist()
    selected_date = st.selectbox("Select a prediction date", available_dates)

    # Number of days ahead (if applicable)
    vs_days = st.number_input("vs_days", min_value=0, max_value=30, value=1)

    # Prepare payload
    payload = {
        "predict_date": selected_date,
        "vs_days": vs_days
    }

    st.markdown("#### Payload to be sent:")
    st.json(payload)

    if st.button("Get Prediction"):
        result = fetch_prediction(API_URL, payload)

        if "error" in result:
            st.error(f"Error: {result['error']}")
        else:
            st.success("Prediction Received!")
            st.markdown("#### API Response:")
            st.json(result)

            predicted = result.get("predicted_price", None)

            if predicted is not None:
                # Get actual price from CSV
                actual_row = df[df["checkin_date"] == pd.to_datetime(selected_date)]
                actual_price = actual_row[hotel_choice].values[0] if not actual_row.empty else None

                # Display metrics
                col1, col2 = st.columns(2)
                col1.metric("Predicted Price", f"${predicted:.2f}")
                if actual_price is not None:
                    col2.metric("Actual Price", f"${actual_price:.2f}")
                else:
                    col2.warning("Actual price not available.")

                # Bar chart: Actual vs Predicted
                chart_df = pd.DataFrame({
                    "Type": ["Actual", "Predicted"],
                    "Price": [actual_price, predicted]
                })

                st.markdown("#### Actual vs Predicted Price")
                st.bar_chart(chart_df.set_index("Type"))

            else:
                st.warning("'predicted_price' not found in API response.")
