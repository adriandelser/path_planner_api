from functools import partial

from celery import shared_task

default_shared_task = partial(
    shared_task, ignore_result=True, store_errors_even_if_ignored=True
)
