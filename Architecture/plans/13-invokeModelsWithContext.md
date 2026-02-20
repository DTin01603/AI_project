# invokeModelsWithContext()

## Trach nhiem
- Goi models/tools su dung context da lay.

## Mo ta chi tiet
- Xay prompt cho model/tool kem context, constraints, task outputs.
- Ap dung safety/policy check truoc khi gui den model.
- Tra ve model output co cau truc de compose response.

## Ghi chu trien khai
- Backend: Python model client/tool router xu ly invocation.
- LangGraph: node xay prompt tu state va luu model output.

## Dau vao
- Context
- Request
- Task outputs

## Dau ra
- Model output

## Phu thuoc
- Model client/tool router (mocked)

## Loi co the xay ra
- Model error
- Empty output

## Kiem thu don vi
- Sends context and gets output.
- Handles model error with retry or fallback.
- Validates output structure.
