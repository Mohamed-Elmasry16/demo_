# ─────────────────────────────────────────────────────────────
# Stage 1 — تحميل الـ LLM model files بس (مش محتاج PyTorch)
# snapshot_download بتجيب الملفات من Hugging Face زي curl بالظبط
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS model-downloader

WORKDIR /model-cache

# huggingface_hub بس — مش محتاجين torch هنا خالص
RUN pip install --no-cache-dir huggingface_hub hf_xet

# تحميل كل ملفات الموديل على الـ disk (مش بنحملهم في الذاكرة)
RUN python -c "\
from huggingface_hub import snapshot_download; \
print('Downloading Qwen2.5-1.5B-Instruct...'); \
snapshot_download( \
    repo_id='Qwen/Qwen2.5-1.5B-Instruct', \
    cache_dir='/model-cache', \
    ignore_patterns=['*.msgpack', '*.h5', 'flax_model*', 'tf_model*'] \
); \
print('Download complete!')"


# ─────────────────────────────────────────────────────────────
# Stage 2 — Production image
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps (بما فيهم torch) — layer منفصل عشان Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الـ model cache من Stage 1
COPY --from=model-downloader /model-cache /model-cache

# نسخ كود التطبيق
COPY api.py llm_chatbot.py data_utils.py ./

# نسخ الموديل والداتا
COPY churn_model.pkl cleaned_data.csv ./

# متغيرات البيئة
ENV HF_HOME=/model-cache \
    TRANSFORMERS_CACHE=/model-cache \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check — n8n بيستنى الـ API يجهز قبل ما يشتغل
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
