import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import logging

def train_model(data_path='netmix_training_data.csv', model_path='model.joblib'):
    """
    Trains a Random Forest model to predict interface stability.

    This function reads the logged data, engineers features, defines a target,
    trains a model, and saves it to a file.
    """
    logging.info(f"Starting model training from data at {data_path}")
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        logging.error(f"Training data not found at {data_path}. Please run the main application to generate data.")
        return

    if len(df) < 100:
        logging.warning(f"Dataset is very small ({len(df)} rows). Model performance may be poor. Collect more data.")
        return

    # --- Feature Engineering ---
    # We want to predict which interface will be 'best' in the near future.
    # Let's create features based on rolling averages.
    df['latency_avg_5'] = df.groupby('interface_name')['latency'].transform(lambda x: x.rolling(5, 1).mean())
    df['failures_rolling_5'] = df.groupby('interface_name')['failures'].transform(lambda x: x.rolling(5, 1).sum())

    # --- Target Variable ---
    # Our target: Is this interface the one with the lowest latency in the next time step?
    # This is a simplification. A more complex target could be "most stable" or "highest bandwidth".
    df['future_latency'] = df.groupby('interface_name')['latency'].shift(-1)
    df.dropna(inplace=True) # Drop rows where we can't calculate a future state

    if df.empty:
        logging.error("Not enough data to create future-state targets. Let the application run longer.")
        return

    # For each timestamp, find the interface that had the minimum future latency.
    best_future_interface = df.loc[df.groupby('timestamp')['future_latency'].idxmin()]
    best_future_interface = best_future_interface.set_index('timestamp')['interface_name'].rename('best_interface')

    df = df.join(best_future_interface, on='timestamp')
    df['is_best'] = (df['interface_name'] == df['best_interface']).astype(int)

    # --- Model Training ---
    features = ['latency_avg_5', 'failures_rolling_5', 'successes', 'active_conns']
    target = 'is_best'

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    logging.info(f"Training RandomForestClassifier on {len(X_train)} samples...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)

    # --- Evaluation ---
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Model accuracy on test set: {accuracy:.2%}")

    # --- Save Model ---
    logging.info(f"Saving trained model to {model_path}")
    joblib.dump(model, model_path)
    logging.info("Training complete.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    train_model()
