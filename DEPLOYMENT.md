# 🚀 Deployment Guide - Phase 2 Multi-Language Platform

This guide covers deploying Repo Patcher Phase 2 with multi-language support, advanced safety features, and performance optimization in production.

## 📋 Prerequisites

### Required Secrets

Configure these secrets in your GitHub repository:

```bash
# AI Service
OPENAI_API_KEY          # OpenAI API key for AI-powered fixes

# GitHub Integration  
GITHUB_TOKEN            # GitHub token with repo and PR permissions

# Optional: Monitoring
JAEGER_ENDPOINT         # Jaeger tracing endpoint (if using external)
```

### Required Permissions

The GitHub token needs these permissions:
- `repo` - Full repository access
- `pull_requests:write` - Create and update pull requests
- `issues:write` - Comment on issues
- `checks:read` - Read workflow status

## 🐳 Docker Deployment

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/FernandoTN/repo-patcher.git
cd repo-patcher

# 2. Run Phase 2 verification (CRITICAL - Test before deployment)
python verify_phase2.py

# 3. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 4. Build and run
docker-compose up --build
```

### Production Deployment

```bash
# Build production image
docker build -t repo-patcher:latest .

# Run with production settings
docker run --rm \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e GITHUB_TOKEN="$GITHUB_TOKEN" \
  -e OTEL_ENABLED=true \
  -v /var/repo-patcher/logs:/workspace/logs \
  -v /var/repo-patcher/backups:/workspace/backups \
  --memory=2g \
  --cpus=2 \
  --security-opt=no-new-privileges:true \
  repo-patcher:latest \
  fix-repo /path/to/repo --create-pr
```

### Docker Compose Stack

For production monitoring stack:

```bash
# Start full stack with monitoring
docker-compose --profile monitoring up -d

# Access monitoring UIs
open http://localhost:16686  # Jaeger UI
open http://localhost:9090   # Prometheus UI
open http://localhost:8000   # Repo Patcher metrics
```

## 🔧 GitHub Actions Setup

### 1. Enable the Action

The main workflow (`.github/workflows/fix-tests.yml`) automatically triggers when:
- The `fix-me` label is applied to issues or PRs
- The workflow has access to required secrets

### 2. Repository Configuration

Add these repository secrets:
1. Go to Settings → Secrets and Variables → Actions
2. Add the required secrets listed above

### 3. Workflow Permissions

Ensure GitHub Actions has appropriate permissions:
1. Go to Settings → Actions → General
2. Set "Workflow permissions" to "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests"

### 4. Test the Integration

1. Create a repository with failing tests
2. Create an issue describing the problem
3. Apply the `fix-me` label
4. Watch the action run and create a PR with fixes

## 🔧 Phase 2 Components

### Multi-Language Support

Phase 2 adds support for multiple programming languages. Ensure your deployment environment supports:

```bash
# Language runtime requirements
python >= 3.9      # Python projects
node >= 16         # JavaScript/TypeScript projects  
go >= 1.19         # Go projects
```

### New Environment Variables

Phase 2 introduces additional configuration options:

```bash
# Performance Optimization
CACHE_SIZE=1000                    # Intelligent cache size
CACHE_TTL=3600                    # Cache TTL in seconds
OPTIMIZATION_LEVEL=balanced        # conservative|balanced|aggressive

# Safety & Security
SAFETY_ENABLED=true               # Enable advanced safety features
APPROVAL_REQUIRED_THRESHOLD=high  # Auto-approval threshold
AUDIT_LOGGING=true               # Enable audit logging

# Cost Management
MAX_COST_PER_SESSION=0.50        # Maximum cost per session
MAX_COST_PER_FIX=0.25           # Maximum cost per fix
PREFERRED_MODEL=gpt-4o-mini      # Default AI model
```

### Safety Configuration

Configure safety rules for your organization:

```yaml
# config/safety.yaml
file_protection:
  critical_patterns:
    - ".github/workflows/"
    - "Dockerfile*"
    - "*.env*"
    - "docker-compose*.yml"
  
  sensitive_patterns:
    - "package.json"
    - "pyproject.toml" 
    - "go.mod"
    - "**/config/*"

risk_assessment:
  max_lines_changed: 100
  require_approval_threshold: "medium"
  block_threshold: "critical"
```

### ⚠️ Pre-Deployment Testing

**CRITICAL**: Run comprehensive testing before production deployment:

```bash
# 1. Run Phase 2 verification
python verify_phase2.py

# 2. Run all unit tests
python -m pytest tests/ -v

# 3. Test multi-language scenarios
python scripts/evaluate.py --scenarios scenarios/E002_js_missing_import
python scripts/evaluate.py --scenarios scenarios/E003_go_missing_import

# 4. Performance testing
python -m pytest tests/test_phase2_performance.py -v

# 5. Safety feature testing
python -m pytest tests/test_phase2_safety.py -v
```

## 📊 Monitoring & Observability

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `http://localhost:8000/health` | Comprehensive health status |
| `http://localhost:8000/health/live` | Kubernetes liveness probe |
| `http://localhost:8000/health/ready` | Kubernetes readiness probe |
| `http://localhost:8000/metrics` | Prometheus metrics |

### Key Metrics

Monitor these metrics for production health:

```prometheus
# Success rate over time
rate(repo_patcher_fix_successes_total[5m]) / rate(repo_patcher_fix_attempts_total[5m])

# Average cost per fix
rate(repo_patcher_cost_dollars[1h]) / rate(repo_patcher_fix_successes_total[1h])

# 95th percentile execution time
histogram_quantile(0.95, rate(repo_patcher_duration_seconds_bucket[5m]))

# Error rate
rate(repo_patcher_errors_total[5m])
```

### Grafana Dashboard

Example dashboard panels:

```json
{
  "dashboard": {
    "title": "Repo Patcher Monitoring",
    "panels": [
      {
        "title": "Fix Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(repo_patcher_fix_successes_total[1h]) / rate(repo_patcher_fix_attempts_total[1h]) * 100"
          }
        ]
      },
      {
        "title": "Average Cost per Fix",
        "type": "stat", 
        "targets": [
          {
            "expr": "rate(repo_patcher_cost_dollars[1h]) / rate(repo_patcher_fix_successes_total[1h])"
          }
        ]
      }
    ]
  }
}
```

## 🔐 Security Configuration

### Container Security

The Docker container implements these security measures:
- Non-root user execution (`repopatcher:1000`)
- Read-only filesystem where possible
- Resource limits (memory, CPU)
- No new privileges flag
- Minimal attack surface with distroless base

### Network Security

- No exposed ports by default (metrics optional)
- Network isolation with custom bridge
- Secrets passed via environment variables only

### File System Security

- Workspace isolation with proper permissions
- Blocked paths protection for sensitive files
- Automatic backup creation for rollback
- Size limits on file modifications

## 🚨 Troubleshooting

### Common Issues

**1. "OpenAI API key not configured"**
```bash
# Check environment variable
echo $OPENAI_API_KEY

# Verify in container
docker run --rm -e OPENAI_API_KEY="$OPENAI_API_KEY" repo-patcher:latest --version
```

**2. "GitHub token permissions insufficient"**
- Ensure token has `repo` and `pull_requests:write` scopes
- Check token hasn't expired
- Verify repository access permissions

**3. "Health checks failing"**
```bash
# Check health status
curl http://localhost:8000/health

# Check logs
docker logs repo-patcher
```

**4. "Tests still failing after fixes"**
- Check agent logs for error details
- Verify test framework detection
- Review diff size and complexity limits

### Debug Mode

Enable debug logging:

```bash
docker run --rm \
  -e REPO_PATCHER_LOG_LEVEL=DEBUG \
  -e DEBUG=true \
  repo-patcher:latest
```

### Log Analysis

Monitor these log patterns:

```bash
# Successful fix attempts
grep "fix_attempt_completed.*success.*true" logs/agent.log

# Rate limiting events
grep "rate_limited" logs/agent.log

# Error patterns
grep "ERROR" logs/agent.log | tail -20
```

## 📈 Scaling Considerations

### Horizontal Scaling

For high-volume deployments:

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  repo-patcher:
    deploy:
      replicas: 3
    environment:
      - OTEL_RESOURCE_ATTRIBUTES=service.name=repo-patcher,service.instance=${HOSTNAME}
```

### Resource Planning

Per container recommendations:
- **Memory**: 2GB limit, 512MB reservation
- **CPU**: 2 cores limit, 0.5 core reservation  
- **Disk**: 10GB for workspace and backups
- **Network**: Minimal bandwidth requirements

### Cost Optimization

Monitor and optimize:
- OpenAI API usage and model selection
- Container resource utilization
- Success rate vs. cost tradeoffs

## 🔄 Maintenance

### Regular Tasks

1. **Weekly**: Review success rates and error patterns
2. **Monthly**: Update dependencies via Dependabot PRs
3. **Quarterly**: Review and update monitoring thresholds

### Updates and Rollbacks

```bash
# Update to latest version
docker pull ghcr.io/fernandotn/repo-patcher:latest
docker-compose up -d

# Rollback if needed
docker pull ghcr.io/fernandotn/repo-patcher:previous-tag
docker-compose up -d
```

### Backup Strategy

Important data to backup:
- Configuration files and secrets
- Logs for audit and debugging
- Metrics data for trend analysis

## 📚 Advanced Configuration

### Custom Monitoring Stack

For enterprise deployments, consider:

```yaml
# monitoring/docker-compose.monitoring.yml
version: '3.8'
services:
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3000:3000"
  
  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"
```

### Integration with CI/CD

Example Jenkins pipeline:

```groovy
pipeline {
    agent any
    stages {
        stage('Deploy') {
            steps {
                script {
                    docker.build("repo-patcher:${env.BUILD_NUMBER}")
                    docker.withRegistry('https://ghcr.io', 'github-token') {
                        docker.image("repo-patcher:${env.BUILD_NUMBER}").push()
                        docker.image("repo-patcher:${env.BUILD_NUMBER}").push('latest')
                    }
                }
            }
        }
    }
}
```

---

## 🎯 Success Metrics

Track these KPIs to measure deployment success:

- **Availability**: >99.5% uptime
- **Success Rate**: >85% within 3 attempts  
- **Average Fix Time**: <10 minutes
- **Cost per Fix**: <$0.50
- **Error Rate**: <5% of attempts

For support or questions about deployment, see the main [README.md](README.md) or create an issue in the repository.