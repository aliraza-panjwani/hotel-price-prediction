# Hotel Price Prediction Dashboard

This project provides a **Streamlit-based GUI** for visualizing hotel price trends and interacting with a machine learning API for hotel price prediction.

## Features

- 📈 **Dashboard:** Visualize actual vs. predicted hotel prices for recent dates.
- 🔮 **API Prediction:** Send requests to a machine learning API and display predicted prices alongside actual prices.
- 🏨 **Hotel Selector:** Analyze different hotels' price trends.
- 📅 **Date Picker:** Choose check-in dates for predictions.
- 📊 **Interactive Charts:** Compare actual and predicted prices with line and bar charts.

## Project Structure
hotel-price-prediction/ 
│ ├── app.py # Streamlit app main file 
├── requirements.txt # Python dependencies 
├── data/ 
│ └── price_table_dropna.csv # Hotel price data 
├── utils/ 
│ └── api_utils.py # Utility for API requests 
└── readme.md # Project documentation

## Setup Instructions

1. **Clone the repository** and navigate to the project folder.

2. **Install dependencies:**
```pip install -r requirements.txt```

3. **Ensure the ML API is running**  
The app expects a prediction API at:  
http://127.0.0.1:5000/predict

(You may need to run the backend ML API separately.)

4. **Run the Streamlit app:**
streamlit run ```app.py```


5. **Open your browser** to the provided local URL to use the dashboard.

## Usage

- **Dashboard:**  
  - Select a hotel to view recent actual and predicted prices.
  - Visualize trends and compare predictions with real data.

- **Predict from API:**  
  - Choose a hotel and date.
  - Send a request to the API and view the predicted price.
  - Compare with the actual price (if available).

## Requirements

- Python 3.8+
- See `requirements.txt` for Python package dependencies.

## Notes

- The app requires a CSV file (`data/price_table_dropna.csv`) with hotel price data.
- The API endpoint must accept POST requests with JSON payloads like:
  ```json
  {
 "predict_date": "YYYY-MM-DD",
 "vs_days": 1
  }```

and respond with:
```{
  "predicted_price": 123.45
}```