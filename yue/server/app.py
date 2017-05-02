#! python main.py
"""
certbot certonly --webroot -w $PWD -d windy.duckdns.org
certbot renew


echo url="https://www.duckdns.org/update?domains=windy&token=798527be-4ff0-4262-bb89-3f9e03e98e23&ip=" | curl -k -o ~/duckdns/duck.log -K -


/usr/local/etc/lighttpd/lighttpd.conf
/usr/local/etc/nginx
/usr/local/www/owncloud
/usr/local/www/yueserver -> /mnt/commont/YueMusicPlayer/yue/server

/usr/local/etc/letsencrypt/live/windy.duckdns.org/privkey.pem
/usr/local/etc/letsencrypt/live/windy.duckdns.org/fullchain.pem


in /etc/rc.conf
php_fpm_enable="YES"

"""

import logging
from logging.handlers import RotatingFileHandler

import jinja2
import flask
from flask import send_file
import os
import ssl
from flask import request

from flask import jsonify, request, abort

from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from yue.core.song import Song
from yue.core.util import format_time
import codecs

from jinja2 import TemplateNotFound, BaseLoader

from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required

from collections import namedtuple

def setup_database(app,db):

    roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

    class Role(db.Model, RoleMixin):
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(80), unique=True)
        description = db.Column(db.String(255))

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(255), unique=True)
        password = db.Column(db.String(255))
        active = db.Column(db.Boolean())
        confirmed_at = db.Column(db.DateTime())
        roles = db.relationship('Role', secondary=roles_users,
                                backref=db.backref('users', lazy='dynamic'))

    app.db_role = Role
    app.db_user = User

def hello(app):
    return "hello world"

@login_required
def player(app):
    template = app.env.get_template('player.html')

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(current_user.email)
    rollPlaylist(app,lib,pl)
    idx,uid = pl.current()


    song = lib.songFromId(uid)

    audio = lambda:None
    audio.source = r"/media/%07d"%uid
    audio.type = "audio/mp3"
    audio.uid = uid
    audio.index = idx
    audio.length = len(pl)
    audio.artist = song[Song.artist]
    audio.album  = song[Song.album]
    audio.title  = song[Song.title]

    return template.render(audio=audio)

def player2(app):
    template = app.env.get_template('player2.html')
    return template.render()

#def login(app):
#    template = app.env.get_template('login.html')
#    return template.render()

def media(app,uid):

    if not current_user.is_authenticated:
        abort(401)

    uid=int(uid)
    lib = app.library.reopen()
    song = lib.songFromId(uid)
    #media = "D:/Music/Discography/Desert Metal/Slo Burn/Slo Burn - Amusing The Amazing (1997)/Slo Burn - 03 - Pilot the Dune.mp3"
    media= song[Song.path]
    return send_file(media)

def rollPlaylist(app,lib,pl):
    """
    Manage the users current playlist

    """

    buf_a = 20 # buffer after current index
    buf_b = 10 # buffer before current index
    buf_h = 5  # hysteresis

    pl_len = len(pl)

    if pl_len < 1:
        query = ""
        limit = buf_a + buf_b
        songs = lib.search(query, orderby=Song.random, limit=limit)
        keys = [ song[Song.uid] for song in songs ]
        pl.insert(len(pl),keys)
        pl.set_index(0)
        return

    idx,uid = pl.current()


    app.app.logger.info("roll %d %d %d %d"%(idx,pl_len,buf_a,buf_b))
    if idx + buf_a > pl_len+buf_h:
        query = ""
        limit = (idx + buf_a) - pl_len
        print(query,limit)
        app.app.logger.info("limit %s %d"%(query,limit))

        songs = lib.search(query, orderby=Song.random, limit=limit)
        keys = [ song[Song.uid] for song in songs ]
        pl.insert(len(pl),keys)

    if idx > buf_b+buf_h:
        lst = list(range(0,idx-buf_b))
        pl.delete(lst)

def media_next(app):
    """
    create a new playlist if at end of list
    """
    if not current_user.is_authenticated:
        abort(401)

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(current_user.email)

    app.app.logger.info("roll begin")
    rollPlaylist(app,lib,pl)
    app.app.logger.info("roll end")
    try:
        idx,uid = pl.next()

        song = lib.songFromId(uid)

        song[Song.path] = "/media/%07d"%uid
        song['playlist_index'] = idx
        song['playlist_length'] = len(pl)
        return jsonify(**song)
    except IndexError:
        pass
    return ""

def media_prev(app):
    """
    return the first item if already at index 0
    """
    if not current_user.is_authenticated:
        abort(401)

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(current_user.email)
    try:
        idx,uid = pl.prev()

        song = lib.songFromId(uid)

        song[Song.path] = "/media/%07d"%uid
        song['playlist_index'] = idx
        song['playlist_length'] = len(pl)
        return jsonify(**song)
    except IndexError:
        pass
    return ""

def get_resource(app,pdir,path):
    if pdir == "js" and path.endswith(".js"):
        return flask.send_from_directory('static/js', path)
    if pdir == "css" and path.endswith(".css"):
        return flask.send_from_directory('static/css', path)
    else:
        abort(404)

def webroot(app,path):
    return flask.send_from_directory('.well-known', path)


PlayListRow = namedtuple('PlayListRow', ['artist', 'title','album','length','current'])

def media_current_playlist(app):

    print(current_user.email)
    if not current_user.is_authenticated:
        abort(401)

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(current_user.email)
    idx,_ = pl.current()

    uids = list(pl.iter())
    songs = lib.songFromIds( uids )

    a = max(0,idx-5)
    b = min(idx+15,len(uids))

    playlist = []
    for i in range(a,b):
        song = songs[i]

        row = PlayListRow(song[Song.artist],song[Song.title],song[Song.album],
                          format_time(song[Song.length]),idx == i)
        playlist.append(row)

    template = app.env.get_template('playlist.html')
    return template.render(playlist=playlist)

class DirectoryLoader(BaseLoader):
    """Loads a template from a python dict.  It's passed a dict of unicode
    strings bound to template names.  This loader is useful for unittesting:

    >>> loader = DictLoader({'index.html': 'source here'})

    Because auto reloading is rarely useful this is disabled per default.
    """

    def __init__(self, template_dir):
        self.template_dir = template_dir

    def get_source(self, environment, template):

        path = os.path.join(self.template_dir,template)
        if not os.path.exists(path):
            raise TemplateNotFound(template)
        _,filename = os.path.split(path)

        with codecs.open(path,"r","utf-8") as rf:
            source = rf.read()

        return source, filename, lambda: True

    def list_templates(self):
        return sorted(self.mapping)

class Application(object):
    """docstring for Application"""
    __instance = None

    def __init__(self,app_name,template_dir):
        super(Application, self).__init__()

        if Application.__instance is not None:
            raise Exception("Application already initialized")
        self.app_name = app_name
        self.template_dir = template_dir
        self.app = flask.Flask(self.app_name,root_path=".")

        self.env = jinja2.Environment(
                    loader=DirectoryLoader(self.template_dir),
                    #loader=jinja2.PackageLoader(self.app_name, self.template_dir),
                    autoescape = True
                )

        self.register("/",'hello',hello)
        self.register("/.well-known/<path:path>",'webroot',webroot)
        self.register("/res/<string:pdir>/<path:path>",'get_resource',get_resource)
        self.register("/player",'player',player)
        self.register("/player2",'player2',player2)
        self.register("/media/<uid>",'media',media)
        self.register("/_media_next",'media_next',media_next)
        self.register("/_media_prev",'media_prev',media_prev)
        self.register("/_media_current_playlist",'media_current_playlist',media_current_playlist)

        #db_path = r"D:/git/YueMusicPlayer/yue.db"
        db_path = os.path.join(os.getcwd(),"yue.db")
        db_uri  = "sqlite:///" + db_path
        self.sqlstore = SQLStore(db_path)
        self.plmanager = PlaylistManager(self.sqlstore)
        self.library = Library(self.sqlstore)

        private_key = "/usr/local/etc/letsencrypt/live/windy.duckdns.org/privkey.pem"
        certificate = "/usr/local/etc/letsencrypt/live/windy.duckdns.org/fullchain.pem"

        print(private_key)
        if os.path.exists(private_key):
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            self.context.load_cert_chain(certificate,private_key)
        else:
            print("no ssl support")
            self.context = None

        self.app.config['DEBUG'] = self.context is None
        self.app.config['SECRET_KEY'] = 'super-secret'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        self.db = SQLAlchemy(self.app)

        setup_database(self,self.db)

        # Define models

        self.user_datastore = SQLAlchemyUserDatastore(self.db, self.db_user, self.db_role)
        self.security = Security(self.app, self.user_datastore)

        self.db.create_all()

        def mkuser(username):
            user = self.user_datastore.find_user(email=username)
            if user is None:
                password=input(username + ":")
                self.user_datastore.create_user(email=username, password=password)

        mkuser("nicksetzer@gmail.com")
        mkuser("bsetzer")
        self.db.session.commit()


        Application.__instance = self

    def instance():
        return Application.__instance

    def register(self,rule,endpoint,callback,**options):

        f=lambda *x,**y : callback(self,*x,**y)
        self.app.add_url_rule(rule, endpoint, f, **options)

    def run(self):

        if self.context is not None:
            port = 5001
            debug = False
            host = "0.0.0.0"
        else:
            port = 5000
            debug = True
            host = "127.0.0.1"

        self.app.run(host=host,port=port,debug=debug,ssl_context=self.context)

