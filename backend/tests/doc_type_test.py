
import sys

from anyio import run

sys.path.append('../')

from backend.utils.upload_utils import get_file_type




async def init() -> None:
    res = get_file_type('.xlsx')
    print(res)
    

if __name__ == '__main__':
    run(init) 



