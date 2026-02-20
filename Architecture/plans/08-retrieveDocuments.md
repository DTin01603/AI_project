# retrieveDocuments()

## Trach nhiem
- Lay tai lieu/context tu knowledge base.

## Mo ta chi tiet
- Lay noi dung va metadata theo id hoac query.
- Gop context bundle co provenance de trich dan sau nay.
- Xu ly kha dung tung phan ma khong chan flow chinh.

## Ghi chu trien khai
- Backend: Python knowledge-base client lay va dong goi tai lieu.
- LangGraph: node lay tai lieu va them context vao state.

## Dau vao
- Document ids hoac query

## Dau ra
- Context bundle (documents, embeddings, metadata)

## Phu thuoc
- Knowledge base client (mocked)

## Loi co the xay ra
- Missing docs
- Read timeout

## Kiem thu don vi
- Returns context for valid ids.
- Handles partial missing docs gracefully.
- Retries or returns error on timeout.
