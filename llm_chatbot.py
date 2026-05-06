# llm_chatbot.py
from transformers import pipeline
import json
import re
import torch

FEATURE_DESCRIPTION = """
- gender: integer (0 for Female, 1 for Male)
- Senior_Citizen: integer (0 for No, 1 for Yes)
- Is_Married: integer (0 for No, 1 for Yes)
- Dependents: integer (0 for No, 1 for Yes)
- tenure: number (months)
- Phone_Service: integer (0 for No, 1 for Yes)
- Dual: string ('No phone service', 'No', 'Yes')
- Internet_Service: string ('DSL', 'Fiber optic', 'No')
- Online_Security: string ('No', 'Yes', 'No internet service')
- Online_Backup: string ('No', 'Yes', 'No internet service')
- Device_Protection: string ('No', 'Yes', 'No internet service')
- Tech_Support: string ('No', 'Yes', 'No internet service')
- Streaming_TV: string ('No', 'Yes', 'No internet service')
- Streaming_Movies: string ('No', 'Yes', 'No internet service')
- Contract: string ('Month-to-month', 'One year', 'Two year')
- Paperless_Billing: integer (0 for No, 1 for Yes)
- Payment_Method: string ('Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)')
- Monthly_Charges: number
- Total_Charges: number
"""

# Queries that mean "all customers — no filter needed"
ALL_CUSTOMERS_KEYWORDS = [
    "all customers", "all at-risk", "all at risk", "all churn",
    "every customer", "everyone", "show all", "list all",
    "full list", "all records", "entire database"
]

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

print(f"Loading model: {MODEL_NAME} on CPU... This may take a few minutes.")

pipe = pipeline(
    "text-generation",
    model=MODEL_NAME,
    device_map="auto",
    torch_dtype=torch.float32,
    trust_remote_code=True
)

print("Model ready!")


def extract_features_from_query(user_query: str):
    """
    Extract filter features from a natural-language query.

    Returns:
        dict   — feature filters to apply (can be empty {} = all customers)
        None   — query is incomprehensible; caller should return an error
    """
    q_lower = user_query.lower()

    # ── Shortcut: "all customers / show all / …" → no filter ──
    if any(kw in q_lower for kw in ALL_CUSTOMERS_KEYWORDS):
        return {}   # empty dict = run on whole dataset

    # ── Try LLM first ──
    system_message = (
        "You are a feature extractor. "
        "Output only valid JSON with the exact keys and values described."
    )

    user_content = f"""Extract the features mentioned in the user query. Return ONLY a JSON object.

Available features (use these keys and values):
{FEATURE_DESCRIPTION}

Examples:
User: show me senior citizens with monthly charges above 70 and fiber optic internet
Assistant: {{"Senior_Citizen": 1, "Monthly_Charges": ">70", "Internet_Service": "Fiber optic"}}

User: find female customers who are married, have dependents, and monthly charges below 50
Assistant: {{"gender": 0, "Is_Married": 1, "Dependents": 1, "Monthly_Charges": "<50"}}

User: customers with no internet service and no phone service
Assistant: {{"Internet_Service": "No", "Phone_Service": 0}}

Now process this query:
User: {user_query}
Assistant:"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_content}
    ]

    prompt = pipe.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    response = pipe(
        prompt,
        max_new_tokens=400,
        do_sample=False,
        temperature=0,
        pad_token_id=pipe.tokenizer.eos_token_id
    )[0]['generated_text']

    # Extract JSON after the last "Assistant:" marker
    json_part = response.split("Assistant:")[-1].strip() if "Assistant:" in response else response

    for match in re.findall(r'\{.*?\}', json_part, re.DOTALL):
        try:
            features = json.loads(match)
            if any(key in features for key in [
                'gender', 'Senior_Citizen', 'Monthly_Charges', 'Internet_Service',
                'tenure', 'Contract', 'Is_Married', 'Dependents', 'Payment_Method'
            ]):
                return features
        except json.JSONDecodeError:
            continue

    # ── Fallback: rule-based extraction ──
    return extract_features_rule_based(user_query)


def extract_features_rule_based(query: str):
    """
    Rule-based fallback feature extractor.

    Returns:
        dict  — extracted features (may be empty {} = all customers)
        None  — should not happen from this function; we always return a dict
    """
    features = {}
    q = query.lower()

    # ── "all customers" shortcut (double-check here too) ──
    if any(kw in q for kw in ALL_CUSTOMERS_KEYWORDS):
        return {}

    # Senior_Citizen
    if "senior" in q:
        features["Senior_Citizen"] = 1

    # Gender
    if "female" in q:
        features["gender"] = 0
    elif "male" in q:
        features["gender"] = 1

    # Is_Married
    if "married" in q and "not married" not in q:
        features["Is_Married"] = 1
    elif "single" in q or "not married" in q:
        features["Is_Married"] = 0

    # Dependents
    if "dependents" in q:
        features["Dependents"] = 0 if ("no dependents" in q or "without dependents" in q) else 1

    # Phone_Service
    if "phone service" in q:
        features["Phone_Service"] = 0 if ("no phone" in q or "without phone" in q) else 1

    # Internet_Service
    if "fiber optic" in q:
        features["Internet_Service"] = "Fiber optic"
    elif "dsl" in q:
        features["Internet_Service"] = "DSL"
    elif "no internet" in q:
        features["Internet_Service"] = "No"

    # Contract
    if "month-to-month" in q or "monthly contract" in q:
        features["Contract"] = "Month-to-month"
    elif "one year" in q or "1 year" in q:
        features["Contract"] = "One year"
    elif "two year" in q or "2 year" in q:
        features["Contract"] = "Two year"

    # Payment_Method
    if "electronic check" in q:
        features["Payment_Method"] = "Electronic check"
    elif "mailed check" in q:
        features["Payment_Method"] = "Mailed check"
    elif "bank transfer" in q:
        features["Payment_Method"] = "Bank transfer (automatic)"
    elif "credit card" in q:
        features["Payment_Method"] = "Credit card (automatic)"

    # Paperless_Billing
    if "paperless billing" in q:
        features["Paperless_Billing"] = 1 if ("yes" in q or "with" in q) else 0

    # Monthly_Charges comparisons
    for pattern, op in [
        (r'monthly charges?\s*(above|greater than|>)\s*(\d+)', '>'),
        (r'monthly charges?\s*(below|less than|<)\s*(\d+)', '<'),
        (r'monthly charges?\s*(>=|at least)\s*(\d+)', '>='),
        (r'monthly charges?\s*(<=|at most)\s*(\d+)', '<='),
    ]:
        m = re.search(pattern, q)
        if m:
            features["Monthly_Charges"] = f"{op}{m.group(2)}"
            break

    # Tenure comparisons
    for pattern, op in [
        (r'tenure\s*(above|greater than|>)\s*(\d+)', '>'),
        (r'tenure\s*(below|less than|<)\s*(\d+)', '<'),
        (r'tenure\s*(>=|at least)\s*(\d+)', '>='),
        (r'tenure\s*(<=|at most)\s*(\d+)', '<='),
    ]:
        m = re.search(pattern, q)
        if m:
            features["tenure"] = f"{op}{m.group(2)}"
            break

    # Online services
    for key, feature in {
        "online security": "Online_Security",
        "online backup": "Online_Backup",
        "device protection": "Device_Protection",
        "tech support": "Tech_Support",
        "streaming tv": "Streaming_TV",
        "streaming movies": "Streaming_Movies",
    }.items():
        if key in q:
            features[feature] = "No" if ("no " + key in q or "without" in q) else "Yes"

    # Return dict (may be empty → means "all customers")
    return features
