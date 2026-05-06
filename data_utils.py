# data_utils.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_customers(csv_path):
    """
    Load the cleaned customer data from a CSV file.
    The file should contain all original features (19 columns) plus optionally 'customerID' and 'Churn'.
    """
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} customers from {csv_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading customers: {e}")
        return pd.DataFrame()

def filter_customers(df, features):
    """
    Filter a DataFrame based on extracted features.
    Supports exact matches and numeric comparisons (>, <, >=, <=).
    """
    if df.empty:
        return df
    mask = pd.Series([True] * len(df))
    for key, value in features.items():
        if key not in df.columns:
            logger.warning(f"Feature '{key}' not in DataFrame columns")
            continue
        try:
            if isinstance(value, str) and value.startswith(('>', '<', '>=', '<=')):
                # Handle comparison operators
                if value.startswith('>='):
                    num = float(value[2:])
                    mask &= (df[key] >= num)
                elif value.startswith('<='):
                    num = float(value[2:])
                    mask &= (df[key] <= num)
                elif value.startswith('>'):
                    num = float(value[1:])
                    mask &= (df[key] > num)
                elif value.startswith('<'):
                    num = float(value[1:])
                    mask &= (df[key] < num)
            else:
                # Exact match (convert value to appropriate type if needed)
                if pd.api.types.is_numeric_dtype(df[key]):
                    value = float(value) if '.' in str(value) else int(value)
                mask &= (df[key] == value)
        except Exception as e:
            logger.error(f"Error applying filter for {key}={value}: {e}")
            continue
    return df[mask]