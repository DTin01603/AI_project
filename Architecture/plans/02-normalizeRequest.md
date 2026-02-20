# normalizeRequest()

## Trach nhiem
- Chuyen doi input tu UI thanh request da chuan hoa cho orchestrator.

## Mo ta chi tiet
- Map cac truong rieng cua UI sang schema thong nhat su dung trong pipeline.
- Kiem tra truong bat buoc va gan request id, channel, locale mac dinh.
- Tao cau truc on dinh de cac thanh phan phia sau khong can logic rieng cho UI.

## Ghi chu trien khai
- UI layer: React tao payload toi thieu kem metadata.
- Backend: Python chuan hoa va validate schema server-side bang Pydantic.
- LangGraph: node chuan hoa ghi state da chuan hoa.

## Dau vao
- Question payload

## Dau ra
- Normalized request (intent hint, constraints, metadata)

## Phu thuoc
- Input schema validator

## Loi co the xay ra
- Invalid schema
- Unsupported channel

## Bao mat va gioi han
- Validate request schema tai ranh gioi API.
- Gioi han kich thuoc cac truong co the phong to.

## Kiem thu don vi
- Normalizes a valid request with expected fields.
- Rejects missing required fields.
- Validates supported channels and locales.
- Preserves request id and metadata.
