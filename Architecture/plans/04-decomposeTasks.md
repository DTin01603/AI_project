# decomposeTasks()

## Trach nhiem
- Tao danh sach buoc/cong viec tu intent va constraints.

## Mo ta chi tiet
- Chuyen intent thanh cac buoc co thu tu, co dau vao/dau ra ro rang.
- Chen buoc bao ve (validation, sanity checks) khi constraints nghiem ngat.
- Giu tasks du nho de executor co the song song va retry.

## Ghi chu trien khai
- Backend: Python planner module tao task list co thu tu.
- LangGraph: planner node ghi task list vao state cho cac node tiep theo.

## Dau vao
- Intent
- Constraints

## Dau ra
- Ordered task list

## Phu thuoc
- Planner module (mocked)

## Loi co the xay ra
- Empty plan
- Incompatible constraints

## Kiem thu don vi
- Produces ordered steps for typical intent.
- Returns validation error on conflicting constraints.
- Handles empty constraints with default plan.
