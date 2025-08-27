# Multi-stage Docker build for Repo Patcher
# Production-ready container with security hardening and resource limits

# Build stage - install dependencies and build package
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir -e .

# Production stage - minimal runtime environment
FROM python:3.11-slim as production

# Create non-root user for security
RUN groupadd --gid 1000 repopatcher && \
    useradd --uid 1000 --gid repopatcher --shell /bin/bash --create-home repopatcher

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory and copy application
WORKDIR /workspace
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . .

# Install the application in production mode
RUN pip install --no-cache-dir -e .

# Create directories with proper permissions
RUN mkdir -p /workspace/logs /workspace/backups /workspace/tmp && \
    chown -R repopatcher:repopatcher /workspace

# Security hardening
RUN chmod -R 755 /workspace && \
    find /workspace -type f -name "*.py" -exec chmod 644 {} \;

# Set environment variables
ENV PYTHONPATH=/workspace/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import repo_patcher; print('OK')" || exit 1

# Resource limits and security
USER repopatcher

# Expose no ports by default (not a web service)

# Default command - can be overridden
ENTRYPOINT ["repo-patcher"]
CMD ["--help"]

# Labels for metadata
LABEL maintainer="Fernando TN <fertorresnavarrete@gmail.com>" \
      version="0.1.0" \
      description="AI-powered test fixing agent" \
      org.opencontainers.image.source="https://github.com/FernandoTN/repo-patcher"