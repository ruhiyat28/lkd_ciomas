FROM python:3.11-slim

LABEL maintainer="BUM Desa Bersama UPK Ciomas LKD"

# psycopg2 needs libpq + build tools (we use psycopg2-binary so no compile, but libpq is still useful)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libffi-dev libssl-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Buat folder upload dan instance, set permission
RUN find . -name "{*" -delete 2>/dev/null || true && \
    mkdir -p \
        app/static/uploads/foto \
        app/static/uploads/ktp \
        app/static/uploads/kk \
        app/static/uploads/sku \
        app/static/uploads/penghasilan \
        app/static/uploads/jaminan \
        app/static/uploads/jaminan_docs \
        app/static/uploads/tanda_tangan \
        instance && \
    chmod -R 777 app/static/uploads instance && \
    sed -i 's/\r//' entrypoint.sh && \
    chmod +x entrypoint.sh && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=5 \
    CMD curl -sf http://localhost:5000/login > /dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
