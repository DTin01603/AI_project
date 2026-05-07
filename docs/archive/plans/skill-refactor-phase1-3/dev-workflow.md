# Dev Workflow

Hướng dẫn cách chạy/test dự án nhanh nhất khi làm refactor skills.

---

## Quy tắc vàng

> **1 container chạy suốt session.** Mọi lệnh đi vào container đó bằng `docker exec`, không dùng `docker compose run --rm`.

---

## Khởi động session

Mỗi sáng (hoặc sau khi reboot):
```bash
docker compose up -d
```

Backend sẽ chạy ở `http://localhost:8000`, frontend `http://localhost:5173`.

Kiểm tra:
```bash
docker ps --filter "name=ai-"
curl http://localhost:8000/health
```

---

## Thao tác hay dùng

### Chạy test

```bash
# Test riêng skills framework (~2s):
docker exec ai-backend python -m pytest backend/tests/unit/test_skills_framework.py backend/tests/unit/test_complexity_classifier_skill.py -v

# Toàn bộ unit test (trừ rag tests pre-existing failure):
docker exec ai-backend python -m pytest backend/tests/unit --ignore=backend/tests/unit/rag_tests
```

### Manual smoke test chat

```bash
curl -X POST http://localhost:8000/api/v2/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"Xin chào","model":"gemini/gemini-2.5-flash"}'
```

### Xem log realtime

```bash
docker logs -f ai-backend
```

### Khi sửa code

| Loại sửa | Lệnh | Thời gian |
|---|---|---|
| `prompt.md` hoặc `skill.yaml` trong skill folder | **Không cần làm gì** (Tầng 2 tự reload) | <1s |
| `.py` files trong `skills/`, `research_agent/`, `rag/` | `docker compose restart backend` | ~10s |
| `requirements.txt` | `docker compose build backend && docker compose up -d` | 2-5 phút |
| `Dockerfile.backend` | Như trên | 2-5 phút |

---

## Tại sao KHÔNG dùng `docker compose run --rm`

Mỗi lệnh đó tạo container mới:
- Pull/create filesystem ~3s
- Start container + network setup ~3s
- Python interpreter init ~2s
- Load dependencies ~3s
- **Tổng overhead: ~10-15s mỗi lệnh**

`docker exec` chỉ fork process vào container đang chạy → **~1-2s**.

---

## Khi Docker Desktop bị lỗi

Nếu gặp `error 500 Internal Server Error` khi gọi docker:
1. Restart Docker Desktop (tray icon → Restart)
2. Hoặc PowerShell:
```powershell
taskkill /F /IM "Docker Desktop.exe"
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

---

## Tầng 2 — Prompt auto-reload (đã implement)

Khi `BaseSkill.invoke` được gọi, framework tự check mtime của `prompt.md`:
- File chưa đổi → dùng template đã cache
- File đổi → reload template, cache lại

→ Sửa `prompt.md` → lưu (Ctrl+S) → curl/test ngay không cần restart.

Lưu ý:
- Chỉ áp dụng cho `prompt.md`, **KHÔNG** cho `skill.yaml` (config đọc 1 lần lúc startup). Nếu đổi `skill.yaml` phải `docker compose restart backend`.
- Overhead: ~0.01ms/invoke (1 syscall `stat`). Không đáng kể.
