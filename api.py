# api.py
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
import os
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from llm_chatbot import extract_features_from_query
from data_utils import load_customers, filter_customers

FEATURE_COLUMNS = [
    'gender', 'Senior_Citizen', 'Is_Married', 'Dependents', 'tenure',
    'Phone_Service', 'Dual', 'Internet_Service', 'Online_Security',
    'Online_Backup', 'Device_Protection', 'Tech_Support', 'Streaming_TV',
    'Streaming_Movies', 'Contract', 'Paperless_Billing', 'Payment_Method',
    'Monthly_Charges', 'Total_Charges'
]

model = None
customers_df = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, customers_df
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    try:
        model_path = os.path.join(BASE_DIR, "churn_model.pkl")
        model = joblib.load(model_path)
        logger.info("Pipeline model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise RuntimeError("Could not load model")

    csv_path = os.path.join(BASE_DIR, "cleaned_data.csv")
    customers_df = load_customers(csv_path)
    if customers_df.empty:
        logger.error("Customer data is empty.")
        raise RuntimeError("Customer data could not be loaded")
    yield

app = FastAPI(title="Churn Prediction API", lifespan=lifespan)

# ── CORS ── مهم لـ n8n لو شغال على بورت تاني
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CustomerFeatures(BaseModel):
    gender: int
    Senior_Citizen: int
    Is_Married: int
    Dependents: int
    tenure: float
    Phone_Service: int
    Dual: str
    Internet_Service: str
    Online_Security: str
    Online_Backup: str
    Device_Protection: str
    Tech_Support: str
    Streaming_TV: str
    Streaming_Movies: str
    Contract: str
    Paperless_Billing: int
    Payment_Method: str
    Monthly_Charges: float
    Total_Charges: float

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/")
def home():
    return {"message": "Churn Prediction API is running"}

@app.post("/predict")
def predict(features: CustomerFeatures):
    try:
        df = pd.DataFrame([features.dict()])
        proba = model.predict_proba(df)[0, 1]
        threshold = 0.28
        prediction = int(proba >= threshold)
        risk = "High" if proba >= 0.7 else "Medium" if proba >= 0.4 else "Low"
        return {
            "churn_prediction": prediction,
            "churn_probability": float(round(proba, 4)),
            "risk_level": risk
        }
    except Exception as e:
        logger.error(f"Error in /predict: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global customers_df, model

    if customers_df is None or customers_df.empty:
        raise HTTPException(status_code=500, detail="Customer data not loaded")

    # 1. Extraction
    features = extract_features_from_query(request.message)

    # None = فشل الاستخراج تماماً (مش مفهوم الطلب)
    # {}   = مفيش فلتر = كل العملاء (زي "show all customers")
    if features is None:
        return ChatResponse(response="Sorry, I couldn't understand the request.")

    # 2. Filtering — لو {} هيرجع كل العملاء
    try:
        if features:
            filtered = filter_customers(customers_df, features)
        else:
            # طلب عام → شغّل على كل الداتا
            filtered = customers_df.copy()

        if filtered.empty:
            return ChatResponse(response="No customers match your criteria.")

        filtered_features = filtered[FEATURE_COLUMNS]

        # 3. Prediction
        probas = model.predict_proba(filtered_features)[:, 1]
        preds = (probas >= 0.28).astype(int)

        high_risk_count = int(preds.sum())
        total_filtered = len(filtered)

        # 4. Response
        if high_risk_count == 0:
            response_text = (
                f"None of the {total_filtered} customers matching your "
                f"description are predicted to churn."
            )
        else:
            churned_ids = (
                filtered[preds == 1]['customerID'].head(3).tolist()
                if 'customerID' in filtered.columns else []
            )
            example_str = f" Examples: {', '.join(churned_ids)}." if churned_ids else ""
            response_text = (
                f"There are {high_risk_count} customers likely to churn "
                f"out of {total_filtered} matching your criteria.{example_str}"
            )

        return ChatResponse(response=response_text)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")
