from flask import Blueprint, request, jsonify, url_for
from utils.api_utils import setup_logging
from models.predictor import PricePredictor
import pandas as pd
from routes.registration import registered_hotels
from webScrapping.scrapping import starScrapping
from datetime import datetime

prediction_bp = Blueprint("prediction", __name__)
logger = setup_logging("prediction", "logs/prediction.log")

predictor = PricePredictor(data_path="data/price_table_dropna.csv")

@prediction_bp.route("/scrapping", methods=["GET"])
def start_scrapping():
    """
    Start the web scraping process to gather hotel data.
    """
    print("Received request to start web scraping.")
    try:
        # Get start_date and end_date from query params
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        print(f"Scraping for dates from {start_date} to {end_date}")
        # Validate and format dates
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date are required"}), 400

        # Ensure correct format (YYYY-MM-DD)
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        print("Starting the web scraping process...")
        # Call scraper function with dates
        result = starScrapping(start_date, end_date)

        if result.get("status") == "completed":
            urls = [url_for('serve_data_file', filename=path.replace('./data/', ''), _external=True)
                    for path in result['doneSteps']]
            processed_url = url_for('serve_data_file', filename=result['processed_file'].replace('./data/', ''), _external=True)

            result['doneSteps'] = urls
            result['processed_file'] = processed_url

            return jsonify(result), 200
        else:
            return jsonify({"error": "Scraping process failed."}), 500

    except Exception as e:
        print(f"Error during web scraping: {e}")
        return jsonify({"error": "Failed to start web scraping process."}), 500

@prediction_bp.route("/predict", methods=["POST"])
def predict_price():
    """
    Predict price for a given date.
    """
    print("Received prediction request.")
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