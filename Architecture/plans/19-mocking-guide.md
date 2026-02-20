# Huong dan mocking

## Mo ta chi tiet
- Liet ke cac phu thuoc ben ngoai can mock trong unit tests.
- Khuyen khich hanh vi xac dinh va mo phong loi ro rang.
- Giup tach moi ham khoi bien dong network/service.

## Ghi chu trien khai
- Backend: Python tests thay the network clients bang fakes hoac mocks.

## Doi tuong mock
- Queue client: enqueue, poll results.
- Search service: query, return results, throw errors.
- Knowledge base: get documents, return missing/partial.
- External APIs: success, rate-limit, timeout.
- Model client/tool router: success, error, empty output.
- Monitoring client: accept log, throw error.
