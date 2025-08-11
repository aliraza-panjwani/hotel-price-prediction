import pandas as pd
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from utils import setup_logging

class PricePredictor:
    """
    Handles training and predicting hotel prices based on competitor data.
    """

    def __init__(self, data_path: str):
        """
        Initialize PricePredictor with dataset.
        Args:
            data_path (str): Path to CSV dataset.
        """
        self.logger = setup_logging("price_predictor", "logs/price_predictor.log")
        self.df = pd.read_csv(data_path, parse_dates=['checkin_date'])
        self.model = None
        self.logger.info("PricePredictor initialized with data: %s", data_path)

    def prepare_data(self, target_hotel: str, competitor_hotels: list, vs_days: int):
        """
        Prepare features and labels for model training.
        """
        features, labels = [], []
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for i in range(len(self.df)):
            date = self.df.loc[i, 'checkin_date']
            past_date = date - timedelta(days=vs_days)

            if past_date not in self.df['checkin_date'].values:
                continue

            past_row = self.df[self.df['checkin_date'] == past_date].iloc[0]
            today_row = self.df[self.df['checkin_date'] == date].iloc[0]

            try:
                target_yesterday_price = past_row[f"{target_hotel}_price"]
                target_yesterday_occ = past_row[f"{target_hotel}_inventory"]
                target_today_occ = today_row[f"{target_hotel}_inventory"]

                comp_yest_prices, comp_yest_occ, comp_today_prices, comp_today_occ = [], [], [], []
                for comp in competitor_hotels:
                    comp_yest_prices.append(past_row[f"{comp}_price"])
                    comp_yest_occ.append(past_row[f"{comp}_inventory"])
                    comp_today_prices.append(today_row[f"{comp}_price"])
                    comp_today_occ.append(today_row[f"{comp}_inventory"])

                day_of_week = date.day_name()
                day_one_hot = [1 if day_of_week == d else 0 for d in days]

                feature_vector = [target_yesterday_price, target_yesterday_occ, target_today_occ]
                for p, o in zip(comp_yest_prices, comp_yest_occ):
                    feature_vector.extend([p, o])
                for p, o in zip(comp_today_prices, comp_today_occ):
                    feature_vector.extend([p, o])
                feature_vector.extend(day_one_hot)

                features.append(feature_vector)
                labels.append(today_row[f"{target_hotel}_price"])

            except KeyError as e:
                self.logger.warning("Missing column during preparation: %s", e)

        columns = [
            f"{target_hotel}_yesterday_price", f"{target_hotel}_yesterday_occ", f"{target_hotel}_today_occ"
        ]
        for comp in competitor_hotels:
            columns.extend([f"{comp}_yesterday_price", f"{comp}_yesterday_occ"])
        for comp in competitor_hotels:
            columns.extend([f"{comp}_today_price", f"{comp}_today_occ"])
        columns.extend([f"day_{d[:3].lower()}" for d in days])

        return pd.DataFrame(features, columns=columns), labels

    def train_model(self, target_hotel: str, competitor_hotels: list, vs_days: int):
        """
        Train RandomForest model using historical data.
        """
        X, y = self.prepare_data(target_hotel, competitor_hotels, vs_days)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model = RandomForestRegressor(random_state=42)
        self.model.fit(X_train, y_train)
        self.logger.info("Model trained for target hotel: %s", target_hotel)

    def predict(self, predict_date: pd.Timestamp, target_hotel: str, competitor_hotels: list, vs_days: int):
        """
        Predict price for the given date and hotel.
        """
        if self.model is None:
            raise ValueError("Model not trained yet.")

        past_date = predict_date - timedelta(days=vs_days)
        if past_date not in self.df['checkin_date'].values or predict_date not in self.df['checkin_date'].values:
            raise ValueError("Required dates are missing from dataset.")

        past_row = self.df[self.df['checkin_date'] == past_date].iloc[0]
        today_row = self.df[self.df['checkin_date'] == predict_date].iloc[0]

        comp_yest_prices, comp_yest_occ, comp_today_prices, comp_today_occ = [], [], [], []
        for comp in competitor_hotels:
            comp_yest_prices.append(past_row[f"{comp}_price"])
            comp_yest_occ.append(past_row[f"{comp}_inventory"])
            comp_today_prices.append(today_row[f"{comp}_price"])
            comp_today_occ.append(today_row[f"{comp}_inventory"])

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_one_hot = [1 if predict_date.day_name() == d else 0 for d in days]

        feature_vector = [
            past_row[f"{target_hotel}_price"],
            past_row[f"{target_hotel}_inventory"],
            today_row[f"{target_hotel}_inventory"]
        ]
        for p, o in zip(comp_yest_prices, comp_yest_occ):
            feature_vector.extend([p, o])
        for p, o in zip(comp_today_prices, comp_today_occ):
            feature_vector.extend([p, o])
        feature_vector.extend(day_one_hot)

        predicted_price = self.model.predict([feature_vector])[0]
        self.logger.info("Predicted price for %s on %s = %.2f", target_hotel, predict_date.date(), predicted_price)
        return predicted_price
