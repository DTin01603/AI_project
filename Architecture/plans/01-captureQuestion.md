# captureQuestion()

## Trach nhiem
- Tiep nhan cau hoi nguoi dung tu diem vao UI.

## Mo ta chi tiet
- Thu thap cau hoi thuan tu API/UI/CLI va gan metadata co ban.
- Chuan hoa toi thieu (cat khoang trang, chuan hoa dau dong) ma khong doi nghia.
- Ap dung gioi han dau vao som de tranh payload qua lon.

## Ghi chu trien khai
- UI layer: React component thu nhan input va kiem tra co ban.
- Backend: Python API nhan payload neu UI gui qua HTTP.
- LangGraph: entrypoint tao state ban dau tu payload.

## Dau vao
- Raw user input (string)
- Optional metadata (locale, channel)

## Dau ra
- Question payload (string + metadata)

## Phu thuoc
- None

## Loi co the xay ra
- Empty input
- Oversized input

## Bao mat va gioi han
- Enforce UI-side input size limits va validation co ban.
- Tu choi input vi pham policy truoc khi gui den API.

## Kiem thu don vi
- Accepts typical question string.
- Rejects empty or whitespace-only input.
- Trims or normalizes input when required.
- Handles very long input with validation error.
