from flask import Flask,send_from_directory
import os
from routes.registration import registration_bp
from routes.prediction import prediction_bp

app = Flask(__name__)

DATA_FOLDER = os.path.join(os.getcwd(), 'data')

@app.route('/data/<path:filename>')
def serve_data_file(filename):
    return send_from_directory(DATA_FOLDER, filename)

# Register Blueprints
app.register_blueprint(registration_bp)
app.register_blueprint(prediction_bp)


if __name__ == "__main__":
    app.run(debug=True)