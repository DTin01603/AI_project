# aggregateExecutionResults()

## Trach nhiem
- Ket hop ket qua executor thanh payload cho orchestrator.

## Mo ta chi tiet
- Gop ket qua nhieu buoc thanh cau truc thong nhat.
- Danh dau loi tung phan nhung van giu ket qua thanh cong.
- Chuan hoa schema de model invocation on dinh.

## Ghi chu trien khai
- Backend: Python aggregation utility gop execution outputs.
- LangGraph: node gop ket qua vao state.

## Dau vao
- Execution results

## Dau ra
- Aggregated results

## Phu thuoc
- Result aggregator

## Loi co the xay ra
- Partial results
- Inconsistent schemas

## Kiem thu don vi
- Aggregates multi-step results in order.
- Tolerates partial failures with flags.
- Rejects incompatible schemas.
