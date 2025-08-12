# Hotel Price Prediction API

A Flask-based machine learning API that predicts hotel prices based on competitor hotel pricing and occupancy data.

## Improvements needed:
- add preprocessing of base file
  - as per filters
- add visiualization

## 📂 Project Structure
```

hotel\_price\_prediction/
│
├── app.py                # Flask entry point
├── models/
│   ├── **init**.py
│   ├── predictor.py      # ML logic for price prediction
│
├── routes/
│   ├── **init**.py
│   ├── registration.py   # Route to register hotels and competitors
│   ├── prediction.py     # Route to predict hotel prices
│
├── utils.py              # Logging setup utility
├── price\_table\_dropna.csv # Your dataset
├── requirements.txt      # Python dependencies
└── README.md

````

---

## ⚙️ Installation

1. **Clone the repository**
```bash
git clone https://github.com/aliraza-panjwani/hotel-price-prediction.git
cd hotel-price-prediction
````

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Ensure dataset is available**
   Place your `price_table_dropna.csv` in the root\data project folder.
   It should contain:

* `checkin_date` (datetime column)
* `<hotel_name>_price` and `<hotel_name>_inventory` for target and competitors.

---

## 🚀 Running the API

```bash
python app.py
```

The API will start on:

```
http://127.0.0.1:5000
```

---

## 📌 API Endpoints

### 1️⃣ Register Hotel & Competitors

**Endpoint:**

```
POST /register
```

**Request JSON:**

```json
{
    "target_hotel": "grand-season-inn-waupaca",
    "competitor_hotels": [
        "quality-inn-new-london-wisconsin",
        "motel-6-wisconsin-rapids",
        "valley-inn-neenah"
    ]
}
```

**Response:**

```json
{
    "message": "Registration successful"
}
```

---

### 2️⃣ Predict Price

**Endpoint:**

```
POST /predict
```

**Request JSON:**

```json
{
    "predict_date": "2026-06-03",
    "vs_days": 1
}
```

**Response:**

```json
{
    "predicted_price": 125.75
}
```

---

## 📝 Logging

* Logs are stored in the `logs/` folder:

  * `logs/price_predictor.log` → model training & prediction logs
  * `logs/registration.log` → registration activity
  * `logs/prediction.log` → prediction requests

---

## ⚠️ Notes

* This model **requires** that both the prediction date and the `vs_days`-offset date exist in the dataset.
* Ensure dataset columns follow naming format:
  `<hotel-name>_price`, `<hotel-name>_inventory`.
* For production, disable `debug=True` in `app.py`.
