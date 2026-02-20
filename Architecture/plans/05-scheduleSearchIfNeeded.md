# scheduleSearchIfNeeded()

## Trach nhiem
- Quyet dinh co can goi retrieval/search hay khong.

## Mo ta chi tiet
- Danh gia neu task list can kien thuc ben ngoai.
- Chi tao search job request khi retrieval co gia tri cao.
- Tranh search khong can thiet de giam chi phi va do tre.

## Ghi chu trien khai
- Backend: Python policy module quyet dinh khi nao enqueue retrieval.
- LangGraph: routing edge quyet dinh co di qua nhanh retrieval hay khong.

## Dau vao
- Task list
- Constraints

## Dau ra
- Search job hoac null

## Phu thuoc
- Policy rules (mocked)

## Loi co the xay ra
- Rule evaluation error

## Kiem thu don vi
- Schedules search when tasks require external context.
- Skips search when tasks are self-contained.
- Handles policy evaluation failure with safe default.
