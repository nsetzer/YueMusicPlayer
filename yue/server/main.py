
import os
import logging
from logging.handlers import RotatingFileHandler
from app import Application
from flask import send_file
"""
flask + flasksecurity
{% if current_user.has_role('admin') %}
    <li><a href="#">Manage Site</a></li>
{% endif %}

authenticate automagically if request is from
localhost, otherwise -- need something more complicated

ssl enable
    http://flask.pocoo.org/snippets/111/
ssl redirect
    http://flask.pocoo.org/snippets/93/

for the playlist, always display the last 5 songs,
the current song, and the next 14 songs.

disable port 80, listen only on 443, https
"""


def main():

    logging.basicConfig(level=logging.DEBUG)
    handler = RotatingFileHandler('yue-server.log', maxBytes=2*1024*1024, backupCount=10)
    handler.setLevel(logging.DEBUG)

    app_name="yue"
    template_dir = os.path.join(os.getcwd(),"templates")
    app = Application(app_name,template_dir)


    # attach the handler to the root instance
    #app.app.logger.addHandler(self.handler)
    logging.getLogger().addHandler(handler)

    app.run()

if __name__ == '__main__':
    main()
