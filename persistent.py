import json
import os
import os.path as osp

from option import *


class Cache(object):
    def __init__(self, cache_root):
        self.cache_root = cache_root
        if not osp.exists(cache_root):
            os.mkdir(cache_root)

    def save(self, key, obj):
        path = osp.join(self.cache_root, key)
        with open(path, "w", encoding="UTF-8") as cache:
            json.dump(obj, cache)

    def load(self, key) -> Option[object]:
        path = osp.join(self.cache_root, key)
        if not osp.exists(path):
            return Non()
        with open(path, "r", encoding="UTF-8") as cache:
            return Some(json.load(cache))

    def purge(self, key):
        path = osp.join(self.cache_root, key)
        if not osp.exists(path):
            return False
        os.remove(path)
        return True
