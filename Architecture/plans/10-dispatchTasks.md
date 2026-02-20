# dispatchTasks()

## Trach nhiem
- Gui task list den executor/workers.

## Mo ta chi tiet
- Gui tasks va context kem correlation id va priority.
- Tach tasks neu can cho thuc thi song song.
- Theo doi execution request id de aggregation va retry.

## Ghi chu trien khai
- Backend: Python orchestrator dispatch tasks den workers.
- LangGraph: node dispatch tasks va luu execution id vao state.

## Dau vao
- Task list
- Context

## Dau ra
- Execution request id

## Phu thuoc
- Executor client (mocked)

## Loi co the xay ra
- Executor unavailable

## Kiem thu don vi
- Dispatches tasks with context and gets request id.
- Handles executor failure with retry/backoff.
- Validates task schema before dispatch.
