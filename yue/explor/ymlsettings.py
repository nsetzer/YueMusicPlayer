
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

    def setKey(self,section,key,obj):
        if section not in self.data:
            self.data[section] = {}
        self.data[section][key] = obj

    def getKey(self, section, key, default=None):
        if section not in self.data:
            return default
        if key not in self.data[section]:
            return default
        return self.data[section][key]

    @staticmethod
    def init( path ):
        YmlSettings._instance = YmlSettings(path);

    @staticmethod
    def instance():
        return YmlSettings._instance

