# executeSearchJob()

## Trach nhiem
- Thuc thi retrieval/search dua tren job request.

## Mo ta chi tiet
- Chay truy van search bang retrieval service va loc ket qua thuan.
- Ap dung ranking, dedup, va kiem tra relevance toi thieu.
- Tao danh sach ket qua da chuan hoa de lay du lieu KB.

## Ghi chu trien khai
- Backend: Python retrieval worker thuc thi truy van va chuan hoa ket qua.
- LangGraph: node thuc thi search va ghi ket qua vao state.

## Dau vao
- Job request

## Dau ra
- Retrieved document ids or results

## Phu thuoc
- Search service (mocked)

## Loi co the xay ra
- Empty results
- Search error

## Kiem thu don vi
- Returns results for valid query.
- Handles no-results with empty list.
- Surfaces search errors with clear error code.
