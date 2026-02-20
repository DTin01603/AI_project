# logMetrics()

## Trach nhiem
- Gui logs/metrics den he thong monitoring.

## Mo ta chi tiet
- Phat sinh log co cau truc cho vong doi request, latency, va error codes.
- Su dung goi bat dong bo de khong anh huong flow chinh.
- Ho tro sampling va redaction de bao ve du lieu nhay cam.

## Quan sat
- Metrics: p95 latency, error rate, queue depth, model latency, retrieval hit rate.
- Logs: JSON co cau truc voi request_id va trace_id.
- Tracing: span theo tung ranh gioi ham chinh.

## Ghi chu trien khai
- Backend: Python logging/metrics client gui su kien.
- LangGraph: node hoac callback log state transitions va timings.

## Dau vao
- Event data
- Latency
- Status

## Dau ra
- None (fire-and-forget)

## Phu thuoc
- Monitoring client (mocked)

## Loi co the xay ra
- Logging failure (should not break flow)

## Kiem thu don vi
- Emits log event with required fields.
- Does not throw on logging failure.
