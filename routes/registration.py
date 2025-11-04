from flask import Blueprint, request, jsonify
from utils.api_utils import setup_logging

registration_bp = Blueprint("registration", __name__)
logger = setup_logging("registration", "logs/registration.log")

# In-memory storage
registered_hotels = {}

@registration_bp.route("/register", methods=["POST"])
def register_hotel():
    """
    Register a target hotel and its competitors.
    """
    data = request.json
    target_hotel = data.get("target_hotel")
    competitor_hotels = data.get("competitor_hotels")

    if not target_hotel or not competitor_hotels:
        return jsonify({"error": "target_hotel and competitor_hotels are required"}), 400

    registered_hotels["target_hotel"] = target_hotel
    registered_hotels["competitor_hotels"] = competitor_hotels

    logger.info("Registered hotel: %s with competitors: %s", target_hotel, competitor_hotels)
    return jsonify({"message": "Registration successful"})