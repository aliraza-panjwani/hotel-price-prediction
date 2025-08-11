from flask import Flask
from routes.registration import registration_bp
from routes.prediction import prediction_bp

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(registration_bp)
app.register_blueprint(prediction_bp)

if __name__ == "__main__":
    app.run(debug=True)
