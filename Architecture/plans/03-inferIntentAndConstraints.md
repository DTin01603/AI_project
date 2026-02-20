# inferIntentAndConstraints()

## Trach nhiem
- Suy luan intent va constraints cho giai doan lap ke hoach.

## Mo ta chi tiet
- Trich xuat intent cap cao va constraints (time, format, safety, cost, latency).
- Dung rule hoac classifier nhe de tranh phu thuoc nang o buoc nay.
- Dua ra confidence va fallback intent khi confidence thap.

## Ghi chu trien khai
- Backend: Python service suy luan bang rules hoac light model wrapper.
- LangGraph: node doc state da chuan hoa va ghi intent/constraints.

## Dau vao
- Normalized request

## Dau ra
- Intent
- Constraints

## Phu thuoc
- Rules or lightweight classifier (mocked)

## Loi co the xay ra
- Unknown intent
- Low confidence

## Kiem thu don vi
- Returns intent/constraints for common request.
- Handles low-confidence intent (fallback intent).
- Handles missing optional metadata gracefully.
