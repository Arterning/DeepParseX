
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.service.upload_service import upload_service

async def init() -> None:
    file_location = 'uploads/test.eml'
    file_bytes = None
    try:
        with open(file_location, 'rb') as file:
            file_bytes = file.read()
            result_dict = upload_service.do_read_email(file_bytes)
            # print(result_dict)
            await upload_service.save_email(result_dict=result_dict)
            return result_dict
    except Exception as e:
        print(f"读取文件时发生错误：{e}")
        raise e


if __name__ == '__main__':
    run(init) 