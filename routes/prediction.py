from flask import Blueprint, request, jsonify
from utils import setup_logging
from models.predictor import PricePredictor
import pandas as pd
from routes.registration import registered_hotels

prediction_bp = Blueprint("prediction", __name__)
logger = setup_logging("prediction", "logs/prediction.log")

predictor = PricePredictor(data_path="data/price_table_dropna.csv")

@prediction_bp.route("/predict", methods=["POST"])
def predict_price():
    """
    Predict price for a given date.
    """
    data = request.json
    predict_date_str = data.get("predict_date")
    vs_days = data.get("vs_days", 1)

    if not predict_date_str:
        return jsonify({"error": "predict_date is required"}), 400

    if not registered_hotels.get("target_hotel"):
        return jsonify({"error": "No hotel registered yet"}), 400

    predict_date = pd.Timestamp(predict_date_str)

    predictor.train_model(
        target_hotel=registered_hotels["target_hotel"],
        competitor_hotels=registered_hotels["competitor_hotels"],
        vs_days=vs_days
    )

    price = predictor.predict(
        predict_date=predict_date,
        target_hotel=registered_hotels["target_hotel"],
        competitor_hotels=registered_hotels["competitor_hotels"],
        vs_days=vs_days
    )

    return jsonify({"predicted_price": round(price, 2)})
