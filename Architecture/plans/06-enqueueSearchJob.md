# enqueueSearchJob()

## Trach nhiem
- Gui search job vao queue/scheduler.

## Mo ta chi tiet
- Serialize search job theo format cua queue kem priority va timeout.
- Tra ve job id de theo doi va tuong quan ket qua.
- Xu ly loi tam thoi bang chinh sach retry/backoff.

## Ghi chu trien khai
- Backend: Python queue client gui search job.
- LangGraph: node enqueue va luu job id vao state.

## Dau vao
- Search job request

## Dau ra
- Job id

## Phu thuoc
- Queue client (mocked)

## Loi co the xay ra
- Queue unavailable
- Timeout

## Kiem thu don vi
- Enqueues job and returns job id.
- Retries or surfaces timeout on queue failure.
- Validates job payload schema.
