import logging
import random
import joblib

class AIPredictor:
    """
    An AI-based interface predictor.

    This class loads a pre-trained model to predict the best interface.
    If no model is found, it falls back to using a simple heuristic.
    """
    def __init__(self, model_path='model.joblib'):
        self.model = None
        self.model_path = model_path
        try:
            self.model = joblib.load(self.model_path)
            logging.info(f"Successfully loaded pre-trained model from {self.model_path}")
        except FileNotFoundError:
            logging.warning(f"Model file not found at {self.model_path}. AIPredictor will use a fallback heuristic.")
            logging.warning("To use the ML model, run `python -m netmix.agent.train` on a generated data log.")
        except Exception as e:
            logging.error(f"Error loading model: {e}. Falling back to heuristic.")

    def _extract_features(self, health_data):
        """Prepares the input data into a list of dictionaries for prediction."""
        features_list = []
        for name, data in health_data.items():
            latencies = list(data['latencies'])
            # Get the last 5 latencies for a simple rolling average
            last_5_latencies = latencies[-5:]
            latency_avg_5 = sum(last_5_latencies) / len(last_5_latencies) if last_5_latencies else 9999

            features_list.append({
                'interface_name': name,
                'latency_avg_5': latency_avg_5,
                'failures_rolling_5': data['failures'],  # The model expects this feature name
                'successes': data['successes'],
                'active_conns': data['active_conns']
            })
        return features_list

    def predict_best_interface(self, interface_health_data):
        """
        Predicts the best interface to use based on a pre-trained model or a heuristic.
        """
        if not interface_health_data:
            return None

        # --- ML Model Prediction ---
        if self.model:
            features_list = self._extract_features(interface_health_data)
            if not features_list:
                return None

            # Prepare data for the model (must be in the same order as trained)
            features_order = ['latency_avg_5', 'failures_rolling_5', 'successes', 'active_conns']
            X = [[d[f] for f in features_order] for d in features_list]

            # Get probability of being the 'best' interface (class 1)
            probabilities = self.model.predict_proba(X)[:, 1]
            best_index = probabilities.argmax()
            best_interface = features_list[best_index]['interface_name']

            logging.info(f"ML Model predicted best interface: '{best_interface}'")
            return best_interface

        # --- Heuristic Logic (Fallback) ---
        best_interface = None
        best_score = float('inf') # Lower is better

        for name, data in interface_health_data.items():
            latencies = list(data['latencies'])
            if not latencies:
                avg_latency = 9999
            else:
                avg_latency = sum(latencies) / len(latencies)

            total_attempts = data['successes'] + data['failures']
            success_rate = (data['successes'] / total_attempts) if total_attempts > 0 else 1.0

            # Score to minimize: weighted latency minus success rate bonus
            score = (avg_latency * 0.8) - (success_rate * 20)

            logging.debug(f"Heuristic score for '{name}': {score:.2f}")

            if score < best_score:
                best_score = score
                best_interface = name

        logging.info(f"Heuristic predicted best interface: '{best_interface}'")
        return best_interface

if __name__ == '__main__':
    # This block now demonstrates the fallback heuristic, as no model exists by default.
    logging.basicConfig(level=logging.INFO)
    dummy_health_data = {
        'Wi-Fi': {'latencies': [80, 90, 100, 120], 'successes': 50, 'failures': 5, 'active_conns': 3},
        'Ethernet': {'latencies': [10, 12, 11, 15], 'successes': 200, 'failures': 0, 'active_conns': 10},
        '4G LTE': {'latencies': [150, 200, 180], 'successes': 20, 'failures': 10, 'active_conns': 1}
    }

    predictor = AIPredictor()
    best = predictor.predict_best_interface(dummy_health_data)
    print(f"\nPredicted best interface (heuristic): {best}")
