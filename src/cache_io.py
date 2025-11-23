import os
from pickle import dump, load

from src.config import SETTINGS


def local_disk_cache(f_in):
    if str(SETTINGS.MODE) == "PRODUCTION":
        # Short circuiting
        return f_in

    os.makedirs(".data", exist_ok=True)
    cache_file = f".data/{f_in.__name__}.pkl"

    def f_out():
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as file:
                r = load(file)
        else:
            r = f_in()
            with open(cache_file, "wb") as file:
                dump(r, file)
        return r

    return f_out
