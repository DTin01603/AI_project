# composeResponse()

## Trach nhiem
- Tao response cuoi cung cho UI.

## Mo ta chi tiet
- Ket hop model output va execution results thanh thong diep cho nguoi dung.
- Ap dung quy tac format va post-processing (tone, length, structure).
- Dam bao response co correlation id va tom tat trang thai.

## Ghi chu trien khai
- Backend: Python response composer tao payload cuoi.
- UI layer: React render response an toan va nhat quan.
- LangGraph: node compose response tu state outputs.

## Dau vao
- Model output
- Execution results
- Context

## Dau ra
- Response payload

## Phu thuoc
- Response formatter

## Loi co the xay ra
- Missing model output

## Kiem thu don vi
- Formats response for typical output.
- Handles missing model output with fallback message.
- Ensures response includes request id.
