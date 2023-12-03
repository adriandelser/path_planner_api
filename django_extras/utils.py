import ast
import json
import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)


def debug(msg):
    msg = f"\n\n======================[ {msg} ]=======================\n\n"
    logger.info(msg=msg)


def get_failure_msg(key, default, var, validation, allow_none):
    return "\n".join(
        [
            f"Failed to load env var with key:{key},",
            f" default:{default}, ",
            f"loaded val: {var}",
            f"validation:{validation} ",
            f"allow_none:{allow_none}",
        ]
    )


def load_env_val(key: str, default=None, allow_none=False, validation: Callable = None):
    """

    Parameters
    ----------
    key
    default: default value if not defined
    allow_none: is it ok for val not to be defined
    validation: validation function for loaded variable, e.g. lamda x: isinstance(x,dict)

    Returns
    -------

    """
    var = os.environ.get(key, default=default)
    if var is not None and isinstance(var, str):
        if var.startswith("_json_"):
            try:
                var = json.loads(var[6:])
            except json.JSONDecodeError:
                raise RuntimeError(
                    get_failure_msg(key, default, var, validation, allow_none)
                )
    elif var is None and not allow_none:
        raise RuntimeError(get_failure_msg(key, default, var, validation, allow_none))
    if validation and not validation(var):
        raise RuntimeError(
            f"Validation error: "
            f"{get_failure_msg(key, default, var, validation, allow_none)}"
        )
    return var


def decode_ast(val):
    return ast.literal_eval(val)


class FixtureGenerator:
    def __init__(self, fixture_path):
        self.fixture_path = fixture_path
        self.db = []

    def add_model(self, app_name: str, model_name: str, pk=None, **values):
        d = {"model": ".".join([app_name, model_name]), "fields": values}
        if pk is not None:
            d["pk"] = pk

        self.db.append(d)

    def save(self):
        f = open(self.fixture_path, "w")
        f.write(json.dumps(self.db, indent=4))
        f.close()
