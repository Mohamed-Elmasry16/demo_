# ─────────────────────────────────────────────
# Stage 1 — Download the LLM model
# (عشان لو أي حاجة في الكود اتغيرت الـ model cache ميتحملش تاني)
# ─────────────────────────────────────────────
FROM python:3.11-slim AS model-downloader

WORKDIR /model-cache

# تثبيت transformers بس عشان نحمّل الموديل
RUN pip install --no-cache-dir transformers huggingface_hub

# تحميل Qwen2.5-1.5B-Instruct وتخزينه في الـ image
RUN python -c "\
from transformers import AutoTokenizer, AutoModelForCausalLM; \
model_name = 'Qwen/Qwen2.5-1.5B-Instruct'; \
print('Downloading tokenizer...'); \
AutoTokenizer.from_pretrained(model_name, cache_dir='/model-cache'); \
print('Downloading model weights...'); \
AutoModelForCausalLM.from_pretrained(model_name, cache_dir='/model-cache'); \
print('Done!')"


# ─────────────────────────────────────────────
# Stage 2 — الـ Production image
# ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# متطلبات النظام
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# نسخ الـ requirements أولاً (Docker layer caching)
COPY requirements.txt .

# تثبيت Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الـ model cache من Stage 1
COPY --from=model-downloader /model-cache /model-cache

# نسخ الكود
COPY api.py .
COPY llm_chatbot.py .
COPY data_utils.py .

# نسخ الموديل والداتا (لازم يكونوا موجودين في الـ repo)
COPY churn_model.pkl .
COPY cleaned_data.csv .

# متغير البيئة عشان transformers يلاقي الـ cache
ENV HF_HOME=/model-cache
ENV TRANSFORMERS_CACHE=/model-cache
ENV PYTHONUNBUFFERED=1

# الـ port اللي الـ API بيشتغل عليه
EXPOSE 8000

# تشغيل الـ API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
