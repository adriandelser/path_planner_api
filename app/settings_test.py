"""
isort:skip_file
"""

import os

os.environ["ENVIRONMENT"] = "development"
os.environ["SQS_QUEUES"] = '{"test": "test"}'
