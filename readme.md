# 🏨 Hotel Price Prediction Dashboard

A **Streamlit-based dashboard** for visualizing hotel price trends and predicting future hotel prices via a machine learning API.

---

## 🚀 Features

* 📈 **Dashboard View** – Visualize actual vs. predicted hotel prices over time
* 🔮 **ML API Integration** – Get real-time price predictions from a machine learning API
* 🏨 **Hotel Selector** – Choose and analyze different hotels
* 📅 **Date Picker** – Select specific check-in dates for predictions
* 📊 **Interactive Charts** – Line/bar charts to compare actual and predicted values

---

## 📁 Project Structure

```
hotel-price-prediction/
├── app.py                  # Streamlit app main file
├── requirements.txt        # Python dependencies
├── data/
│   └── price_table_dropna.csv   # Hotel price dataset
├── utils/
│   └── api_utils.py        # Utility functions for API communication
└── readme.md               # Project documentation
```

---

## 🛠️ Setup Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/hotel-price-prediction.git
   cd hotel-price-prediction
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure the ML API is running**

   The app expects a prediction API at:

   ```
   http://127.0.0.1:5000/predict
   ```

   > **Note:** You need to start the backend ML API separately.

4. **Run the Streamlit app**

   ```bash
   streamlit run app.py
   ```

5. **Open the app in your browser** using the URL provided in the terminal (usually `http://localhost:8501`)

---

## 💡 Usage Guide

### 🔍 Dashboard View

* Select a **hotel** to view its recent actual and predicted prices
* Use **interactive charts** to analyze trends and compare forecasts

### 📤 Predict via API

* Pick a **hotel** and **check-in date**
* Submit the request to the ML API
* View the **predicted price** and compare it with actuals (if available)

---

## 📨 API Format

### 🔧 Request Payload (JSON)

```json
{
  "predict_date": "YYYY-MM-DD",
  "vs_days": 1
}
```

### ✅ Expected Response

```json
{
  "predicted_price": 123.45
}
```

---

## 📋 Requirements

* Python 3.8 or higher
* All Python dependencies listed in `requirements.txt`

---

## 📎 Notes

* The app needs the CSV file at: `data/price_table_dropna.csv`
* The prediction API must be accessible at `http://127.0.0.1:5000/predict`