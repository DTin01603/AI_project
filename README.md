# AI Project

## Environment security

- `os.getenv("...")` trong code chỉ hiển thị **tên biến môi trường**, không phải giá trị secret.
- Secret thật phải nằm trong `.env` local (đã có trong `.gitignore`) hoặc secret manager của hạ tầng.
- File mẫu an toàn là `.env.example` (không chứa key thật).

Thiết lập nhanh:

```bash
cp .env.example .env
```

Sau đó thay các placeholder trong `.env` bằng key thật của bạn.

Khuyến nghị bảo mật:

- Không commit `.env`.
- Nếu key từng lộ ở screenshot/log/chat, hãy rotate ngay key tại nhà cung cấp (Gemini/Tavily).

## Run locally (Docker Compose)

```bash
docker compose up --build
```

Nếu muốn luôn dọn server cũ trước khi chạy lại (khuyến nghị để tránh trùng cổng/process cũ):

```bash
./scripts/docker-up-clean.sh
```

Services:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Prometheus metrics: `http://localhost:8000/metrics`

## Kubernetes deployment

Manifest cho production nằm tại:

- `deploy/k8s/advanced-agent.yaml`

Apply:

```bash
kubectl apply -f deploy/k8s/advanced-agent.yaml
```

Manifest đã bao gồm:

- Redis service (shared state)
- Backend Deployment + Service + HPA (horizontal scaling)
- Frontend Deployment + Service

## Advanced Agent configuration

Advanced Agent load config từ:

1. Environment variables (ưu tiên cao nhất)
2. JSON config file qua `ADVANCED_CONFIG_FILE`
3. Default values trong code

Ví dụ dùng config file:

```bash
export ADVANCED_CONFIG_FILE=./backend/config/advanced.local.json
```

Ví dụ `backend/config/advanced.local.json`:

```json
{
  "enabled": true,
  "reflection_score_threshold": 72,
  "max_retries": 3,
  "redis_enabled": true,
  "redis_url": "redis://localhost:6379/0",
  "monitoring_enabled": true,
  "alerts_enabled": true
}
```

### Configuration reference

| Variable | Default | Description |
|---|---:|---|
| `ADVANCED_AGENT_ENABLED` | `true` | Bật/tắt toàn bộ Advanced Agent |
| `ADVANCED_REFLECTION_ENABLED` | `true` | Bật Self Reflection |
| `ADVANCED_PLANNER_ENABLED` | `true` | Bật Multi-step planner |
| `ADVANCED_CODE_EXECUTION_ENABLED` | `false` | Bật sandbox thực thi code |
| `ADVANCED_REFLECTION_THRESHOLD` | `70` | Ngưỡng Reflection score pass (0-100) |
| `ADVANCED_MAX_RETRIES` | `3` | Số lần retry tối đa |
| `ADVANCED_CODE_TIMEOUT_SECONDS` | `30` | Timeout code execution |
| `ADVANCED_CODE_MEMORY_MB` | `512` | Memory limit cho code execution |
| `ADVANCED_STREAM_BUFFER_SIZE` | `100` | Số chunk buffer cho stream resume |
| `ADVANCED_MEMORY_ENABLED` | `true` | Bật long-term memory |
| `ADVANCED_MEMORY_RELEVANCE_THRESHOLD` | `0.6` | Ngưỡng relevance retrieval (0-1) |
| `ADVANCED_MEMORY_RETRIEVAL_LIMIT` | `10` | Số memory entries tối đa trả về |
| `ADVANCED_MEMORY_SUMMARY_TOKENS` | `10000` | Ngưỡng token để auto-summarize |
| `ADVANCED_REDIS_ENABLED` | `false` | Bật Redis cho session memory chia sẻ |
| `ADVANCED_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `ADVANCED_VECTOR_DB_ENABLED` | `false` | Bật vector DB dependency |
| `ADVANCED_VECTOR_DB_BACKEND` | `inmemory` | Backend vector DB (`inmemory`, `qdrant`, ...) |
| `ADVANCED_VECTOR_DB_URL` | _empty_ | URL health endpoint của vector DB |
| `ADVANCED_MEMORY_ENCRYPTION_KEY` | _auto generated fallback_ | Fernet key để mã hóa memory at rest |
| `ADVANCED_TOOL_REGISTRY_ENABLED` | `true` | Bật dynamic tool registry |
| `ADVANCED_TOOL_TIMEOUT_SECONDS` | `60` | Timeout tool execution |
| `ADVANCED_TOOL_FAILURE_THRESHOLD` | `10` | Số lỗi liên tiếp trước khi disable tool |
| `ADVANCED_TOOL_RATE_LIMIT_PER_MINUTE` | `100` | Rate limit tool calls/user/phút |
| `ADVANCED_MONITORING_ENABLED` | `true` | Bật thu thập Prometheus metrics |
| `ADVANCED_ALERTS_ENABLED` | `true` | Bật tạo cảnh báo runtime |
| `ADVANCED_CODE_TIMEOUT_ALERT_THRESHOLD` | `0.1` | Ngưỡng alert timeout rate của code execution |
| `ADVANCED_STREAM_FAILURE_ALERT_THRESHOLD` | `0.05` | Ngưỡng alert stream connection failure rate |

## Health, metrics, alerts

- `GET /health`: trả về status `ok` hoặc `degraded` + dependency health (`redis`, `vector_database`, `code_execution_sandbox`)
- `GET /ready`: readiness check
- `GET /metrics`: Prometheus metrics
- `GET /alerts`: runtime alerts (reflection, timeout-rate, stream-failure-rate)

## Long-term memory migration

Migration scripts nằm tại `backend/migrations`.

Chạy migration:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_create_long_term_memory_schema.sql
```
