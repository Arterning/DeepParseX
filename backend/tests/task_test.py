#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import sys

from anyio import run

sys.path.append('../')

from backend.app.task.service.task_service import task_service
import time


async def init() -> None:
    # tasks = task_service.get_list()
    # print(tasks)

    # res = task_service.run(
    #     name='upload_handle_file',
    #     args=[],
    #     kwargs={
    #         'id': 13,
    #     }
    # )

    # uid = str(res)
    # print("uid", uid)
    result = task_service.get_result(uid='7284fde8-240b-4535-bd1a-836c752769da')

    # a2ea6fdb-444e-4230-a8f8-0f6d68281d4f
    # result = task_service.get_result('a2ea6fdb-444e-4230-a8f8-0f6d68281d4f')
    print(result.info)
    # print(str(res), type(str(res)))



if __name__ == '__main__':
    run(init) 
