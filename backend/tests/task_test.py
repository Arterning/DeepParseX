#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import sys

from anyio import run

sys.path.append('../')

from backend.app.task.service.task_service import task_service



async def init() -> None:
    # tasks = task_service.get_list()
    # print(tasks)

    res = task_service.run(
        name='upload_handle_file',
        args=[]
    )
    print(res)


if __name__ == '__main__':
    run(init) 
