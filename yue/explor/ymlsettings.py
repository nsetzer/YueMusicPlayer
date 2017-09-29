
import os

from yue.core.yml import dump as yml_dump, load as yml_load

class YmlSettings(object):
    """docstring for YmlSettings"""

    _instance = None

    def __init__(self, yml_path):
        super(YmlSettings, self).__init__()
        self.yml_path = yml_path
        self.load()

    def save(self):
        yml_dump(self.data,self.yml_path)

    def load(self):
        if os.path.exists(self.yml_path):
            self.data = yml_load(self.yml_path)
        else:
            self.data = {}

    @staticmethod
    def init( path ):
        YmlSettings._instance = YmlSettings(path);

    @staticmethod
    def instance():
        return YmlSettings._instance

