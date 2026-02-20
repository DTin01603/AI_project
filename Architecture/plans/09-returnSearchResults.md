# returnSearchResults()

## Trach nhiem
- Tra search results ve cho orchestrator.

## Mo ta chi tiet
- Dinh dang context da lay thanh payload phu hop cho orchestrator.
- Giu lai metadata nguon, timestamp, va ranking scores.
- Dam bao payload khong vuot gioi han kich thuoc.

## Ghi chu trien khai
- Backend: Python formatter dinh dang ket qua cho orchestrator.
- LangGraph: node format context cho cac node tiep theo.

## Dau vao
- Search results

## Dau ra
- Normalized context payload

## Phu thuoc
- Result formatter

## Loi co the xay ra
- Malformed results

## Kiem thu don vi
- Formats results to expected schema.
- Rejects malformed result items.
- Preserves source metadata.
