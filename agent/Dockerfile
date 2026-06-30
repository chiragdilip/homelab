# Agent image. Multi-arch friendly: kubectl is fetched for the build arch, so this
# builds correctly on the arm64 Jetson (or amd64 workers).
FROM python:3.11-slim

# kubectl (for the cluster tools) + ping (network tool) + curl/ca-certs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates iputils-ping bash \
    && ARCH="$(dpkg --print-architecture)" \
    && curl -fsSL "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/${ARCH}/kubectl" -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# In-cluster these are set via the Deployment env / ConfigMap.
ENV AGENT_WORKSPACE=/workspace
EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
