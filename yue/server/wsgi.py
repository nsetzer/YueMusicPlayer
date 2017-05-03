
import os,sys
path=os.path.split(__file__)[0]
sys.path.insert(0,path)
os.chdir(path)
sys.stderr.write("%s\n"%os.getcwd())
import logging
from logging.handlers import RotatingFileHandler
from app import Application
from flask import send_file

logging.basicConfig(level=logging.DEBUG)
handler = RotatingFileHandler('yue-server.log', maxBytes=2*1024*1024, backupCount=10)
handler.setLevel(logging.DEBUG)

app_name="yue"
template_dir = os.path.join(os.getcwd(),"templates")
yue_app = Application(app_name,template_dir)
logging.getLogger().addHandler(handler)

app = yue_app.app

if __name__ == "__main__":
  app.run()
