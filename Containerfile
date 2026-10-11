# Works with both apple/container (`container build`) and Docker (`docker build -f Containerfile`).
# Note: containers can't use the Mac's GPU, so this image ships the mock + cloud providers only.
# Run the `local` provider natively on macOS instead (see README).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KINORA_HOST=0.0.0.0 \
    KINORA_PORT=8000 \
    KINORA_OUTPUT_DIR=/data/outputs \
    KINORA_PROVIDERS=mock,replicate

RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY kinora ./kinora
COPY frontend ./frontend
RUN pip install --no-cache-dir . \
 && useradd --create-home kinora && mkdir -p /data/outputs && chown -R kinora /data

USER kinora
EXPOSE 8000
VOLUME ["/data"]
CMD ["python", "-m", "kinora"]
