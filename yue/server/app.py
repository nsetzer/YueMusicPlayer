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
nginx_enable="YES"

uwsgi --socket 0.0.0.0:8000 --protocol=http -w wsgi:app
/usr/local/etc/rc.d/yueserver

/usr/local/www/yueserver:mkdir conf
/usr/local/www/yueserver:cp yueserver.ini conf
/usr/local/www/yueserver:cp /usr/local/etc/nginx/nginx.conf conf
/usr/local/www/yueserver:cp /usr/local/etc/rc.d/yueserver conf


"""

import logging
from logging.handlers import RotatingFileHandler

import json
import jinja2
import flask
from flask import send_file
import os
import ssl
from flask import request

from flask import jsonify, request, abort, render_template

from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from yue.core.history import History
from yue.core.song import Song
from yue.core.util import format_time
from yue.core.sync import FFmpegEncoder
import yue.core.yml as yml
import codecs

from jinja2 import TemplateNotFound, BaseLoader

from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required
from flask_security.utils import encrypt_password
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt

from collections import namedtuple

import binascii

def random_hash(nbytes=16):
    return binascii.hexlify(os.urandom(nbytes))

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
        api_key = db.Column(db.String(32))
        default_query = db.Column(db.String(255))
        roles = db.relationship('Role', secondary=roles_users,
                                backref=db.backref('users', lazy='dynamic'))

    # bcrypt = Bcrypt(app)
    # bcrypt.generate_password_hash(password)
    # bcrypt.check_password_hash(hash,password)
    app.db_role = Role
    app.db_user = User

def hello(app):
    return "hello world"

@login_required
def player(app):
    template = app.env.get_template('player.html')

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(str(current_user.id))
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

    return template.render(audio=audio,current_user=current_user)

def player2(app):
    template = app.env.get_template('player2.html')
    return template.render()

def media(app,uid):

    if not current_user.is_authenticated:
        abort(401)

    uid=int(uid)
    lib = app.library.reopen()
    song = lib.songFromId(uid)
    #media = "D:/Music/Discography/Desert Metal/Slo Burn/Slo Burn - Amusing The Amazing (1997)/Slo Burn - 03 - Pilot the Dune.mp3"
    path= song[Song.path]

    _,ext = os.path.splitext(path)
    if ext.lower() != ".mp3":
        path = app.getTranscodedPath(song)

    return send_file(path)

def rollPlaylist(app,lib,pl):
    """
    Manage the users current playlist

    """

    buf_a = 20 # buffer after current index
    buf_b = 10 # buffer before current index
    buf_h = 5  # hysteresis

    pl_len = len(pl)

    if pl_len < 1:
        query = current_user.default_query
        limit = buf_a + buf_b
        songs = lib.search(query, orderby=Song.random, limit=limit)
        keys = [ song[Song.uid] for song in songs ]
        if len(keys)==0:
            raise Exception("empty query result: %s"%query)
        pl.insert(len(pl),keys)
        pl.set_index(0)

        if len(pl)==0:
            raise Exception("empty list - a")

        return

    idx,uid = pl.current()

    app.app.logger.info("roll %d %d %d %d"%(idx,pl_len,buf_a,buf_b))
    if idx + buf_a > pl_len+buf_h:
        query = current_user.default_query
        limit = (idx + buf_a) - pl_len
        app.app.logger.info("limit %s %d"%(query,limit))

        songs = lib.search(query, orderby=Song.random, limit=limit)
        keys = [ song[Song.uid] for song in songs ]
        pl.insert(len(pl),keys)

    if idx > buf_b+buf_h:
        lst = list(range(0,idx-buf_b))
        pl.delete(lst)

    if len(pl)==0:
        raise Exception("empty list - a")

def media_next(app):
    """
    create a new playlist if at end of list
    """
    if not current_user.is_authenticated:
        abort(401)

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(str(current_user.id))

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
    pl = plmgr.openPlaylist(str(current_user.id))
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

def media_index(app):
    """
    return the first item if already at index 0
    """
    if not current_user.is_authenticated:
        abort(401)

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(str(current_user.id))
    try:
        before = 5 # number of songs to display before current
        idx,uid = pl.current()

        try:
            index=int(request.args.get("index",-1))
            index = idx - min(idx,before) + (index - 1)
            pl.set_index(index)
        except:
            pass

        idx,uid = pl.current()
        print(index,idx)

        song = lib.songFromId(uid)

        song[Song.path] = "/media/%07d"%uid
        song['playlist_index'] = idx
        song['playlist_length'] = len(pl)
        return jsonify(**song)
    except IndexError:
        pass
    return ""

def media_library(app):
    if not current_user.is_authenticated:
        abort(401)

    art=request.get("artist",-1)
    alb=request.get("album",-1)

def get_resource(app,pdir,path):
    if pdir == "js" and path.endswith(".js"):
        return flask.send_from_directory('static/js', path)
    if pdir == "css" and path.endswith(".css"):
        return flask.send_from_directory('static/css', path)
    else:
        abort(404)

def webroot(app,path):
    return flask.send_from_directory('.well-known', path)

@login_required
def user_api_key(app):
    if request.args.get('regen',"").lower()=="true" or current_user.api_key=="":
        current_user.api_key = binascii.hexlify(os.urandom(16))
        app.db.session.commit()
    return current_user.api_key

def api_history(app):

    try:
        username=request.args.get('username',None)
        apikey = request.args.get('key',None)
    except Exception as e:
        print("a",e)
        abort(401)

    history = app.history.reopen()

    if request.method == 'GET':
        try:
            page = int(request.args.get("page",0))
            page_size = int(request.args.get("page_size",50))
        except:
            abort(401)

        offset = page*page_size
        records = history.export(orderby="date",
                                 offset=offset,
                                 limit=page_size)
        result = {
            "page" : page,
            "num_pages" : (len(history)+page_size - 1) // page_size,
            "records" : records
        }
        return jsonify(result)
    elif request.method == 'PUT':
        print("history put")
        if request.headers.get("Content-Type","") != "text/x-yue-history":
            abort(406)
        records = json.loads(request.data.decode("utf-8"))
        history._import(records)
        print("imported %d records"%len(records))
    elif request.method == 'DELETE':
        history.clear()
        print("clear history",len(history))

    return "OK", 200

def api_download_song(app,uid):
    # urllib.request.urlretrieve(url_string,file_name)

    try:
        username=request.args.get('username',None)
        apikey = request.args.get('key',None)
    except Exception as e:
        print("a",e)
        abort(401)

    uid=int(uid)
    lib = app.library.reopen()
    song = lib.songFromId(uid)
    path= song[Song.path]
    return send_file(path)

def api_library(app):

    page_size = 50

    try:
        username=request.args.get('username',None)
        apikey = request.args.get('key',None)
    except Exception as e:
        abort(401)

    try:
        page = int(request.args.get("page",0))
        page_size = int(request.args.get("page_size",50))
    except:
        abort(401)

    lib = app.library.reopen()

    query = "ban = 0"
    offset = page*page_size
    orderby=[Song.artist,Song.album,Song.title]
    songs = lib.search(query,orderby=orderby,offset=offset,limit=page_size)

    for song in songs:
        _,song[Song.path] = os.path.split(song[Song.path])
        del song[Song.blocked]
    result = {
        "page" : page,
        "num_pages" : (len(lib)+page_size - 1) // page_size,
        "songs" : songs
    }
    return jsonify(result)

def register_user(app):

    if not current_user.is_authenticated:
        return "Error",401

    if not current_user.has_role("admin"):
        return "Error",401

    email = request.args.get('email',"")
    admin = bool(request.args.get('admin',""))

    print(email,admin,app.user_exists(email))

    if app.user_exists(email):
        return "Error",409

    role = "admin" if admin else "user"
    app.mkuser(email,"password",role)
    return "OK",201

PlayListRow = namedtuple('PlayListRow', ['artist', 'title','album','length','current'])

def media_current_playlist(app):

    if not current_user.is_authenticated:
        abort(401)

    before = 5 # number of songs to display before current
    after = 15 # number of songs to display after current

    lib = app.library.reopen()
    plmgr = app.plmanager.reopen()
    pl = plmgr.openPlaylist(str(current_user.id))

    try:
        drag=int(request.args.get("drag",-1))
        drop=int(request.args.get("drop",-1))
    except:
        drag = -1
        drop = -1

    try:
        delete=int(request.args.get("delete",-1))
    except:
        delete = -1

    if drag>=0 and drop >=0:
        idx,_ = pl.current()
        b = min(idx,before)
        print("dnd-a",drag,drop,b,idx)
        drag = idx - b + (drag - 1)
        drop = idx - b + (drop - 1)
        print("dnd-b",drag,drop)
        pl.reinsertList([drag,],drop)
    elif delete >= 0:
        idx,_ = pl.current()
        b = min(idx,before)
        delete = idx - b + (delete - 1)
        pl.delete(delete)
    else:
        rollPlaylist(app,lib,pl)
        idx,_ = pl.current()

    uids = list(pl.iter())
    songs = lib.songFromIds( uids )

    a = max(0,idx-before)
    b = min(idx+after,len(uids))

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

        self.config = yml.load("yueserver.cfg")
        print(self.config)

        addurl = self.app.add_url_rule
        def dummy(*args,**kwargs):
            print(args,kwargs)
            return addurl(*args,**kwargs)
        self.app.add_url_rule=dummy


        self.register("/",hello)
        self.register("/.well-known/<path:path>",webroot)
        self.register("/res/<string:pdir>/<path:path>",get_resource)
        self.register("/player",player)
        self.register("/player2",player2)
        self.register("/media/<uid>",media)
        self.register("/_media_next",media_next)
        self.register("/_media_prev",media_prev)
        self.register("/_media_index",media_index)
        self.register("/_media_current_playlist",media_current_playlist)
        self.register("/api/history",api_history,methods=['GET','PUT','DELETE'])
        self.register("/api/library/<uid>",api_download_song,methods=['GET'])
        self.register("/api/library",api_library,methods=['GET'])
        self.register("/user/api_key",user_api_key)
        self.register("/user/register",register_user)



        #db_path = r"D:/git/YueMusicPlayer/yue.db"
        db_path = os.path.abspath(self.config['yue']['db_path']).replace("\\","/")
        print(db_path)
        db_uri  = "sqlite:///" + db_path
        self.sqlstore = SQLStore(db_path)
        self.plmanager = PlaylistManager(self.sqlstore)
        self.library = Library(self.sqlstore)
        self.history = History(self.sqlstore)

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
        self.app.config['SECRET_KEY'] = self.config['security']['secret_key']
        self.app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['SECURITY_LOGIN_URL'] = "/user/login"
        self.app.config['SECURITY_LOGOUT_URL'] = "/user/logout"
        #self.app.config['SECURITY_RESET_URL'] = "/user/reset"
        self.app.config['SECURITY_CHANGE_URL'] = "/user/change"
        #self.app.config['SECURITY_REGISTER_URL'] = "/user/register"
        #self.app.config['SECURITY_CONFIRM_URL'] = "/user/confirm"
        self.app.config['SECURITY_POST_LOGIN_VIEW'] = "/player"
        self.app.config['SECURITY_POST_LOGOUT_VIEW'] = "/"
        self.app.config['SECURITY_RECOVERABLE'] = False
        self.app.config['SECURITY_CHANGEABLE'] = True
        self.app.config['SECURITY_REGISTERABLE'] = False
        self.app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
        self.app.config['SECURITY_PASSWORD_SALT'] = self.config['security']['password_salt'] #HMAC

        self.app.config['MAIL_SERVER']   = self.config['mail']['server']
        self.app.config['MAIL_PORT']     = self.config['mail']['port']
        self.app.config['MAIL_USE_SSL']  = self.config['mail']['use_ssl']
        self.app.config['MAIL_USE_TLS']  = self.config['mail']['use_tls']
        self.app.config['MAIL_USERNAME'] = self.config['mail']['username']
        self.app.config['MAIL_PASSWORD'] = self.config['mail']['password']

        self.app.config['BCRYPT_LOG_ROUNDS'] = 12
        self.app.config['BCRYPT_HANDLE_LONG_PASSWORDS'] = True # sha256 hash prior to bcrypt

        #msg = Message(
        #      'Hello',
        #       sender=self.config['mail']['username'],
        #       recipients=
        #           [self.config['mail']['username']])
        #msg.body = "This is the email body"
        #self.mail = Mail(self.app)
        #self.mail.send(msg)

        self.db = SQLAlchemy(self.app)

        setup_database(self,self.db)

        # Define models

        self.user_datastore = SQLAlchemyUserDatastore(self.db, self.db_user, self.db_role)
        self.security = Security(self.app, self.user_datastore)

        self.db.create_all()
        self.db.session.commit()

        self.mkrole("admin","admin")
        self.mkrole("user","user")
        with self.app.app_context():
            self.mkuser("admin","admin","admin")


        for user in self.db.session.query(self.db_user):
            print(user.email,user.roles,user.api_key)

        Application.__instance = self

    def mkrole(self,name,desc):
        # todo look into encrypt_password
        role = self.user_datastore.find_role(name)
        if role is None:
            self.user_datastore.create_role(name=name,description=desc)
            self.db.session.commit()

    def user_exists(self,username):
        user = self.user_datastore.find_user(email=username)
        return user is not None

    def mkuser(self,username,password,role):
        # todo look into encrypt_password
        user = self.user_datastore.find_user(email=username)
        print(user,username)
        if user is None:
            api_key = random_hash(16)
            #pw_hash = self.bcrypt.generate_password_hash(password)
            pw_hash = encrypt_password(password)
            query = "ban = 0"
            print("creating user: %s"%username)
            self.user_datastore.create_user(email=username,
                password=pw_hash,api_key=api_key,default_query=query)
            user = self.user_datastore.find_user(email=username)
            r = self.user_datastore.find_role(role)
            user.roles.append(r)
            self.db.session.commit()

    def getTranscodedPath(self,song):

        base = self.config['yue']['encoder_output_base']
        dir = os.path.join(base,song[Song.artist]);
        if not os.path.exists(dir):
            os.makedirs(dir)
        tgtpath = os.path.join(dir,"%s.mp3"%song[Song.uid])

        if not os.path.exists(tgtpath):
            self.transcode_song(song,tgtpath)

        return tgtpath

    def transcode_song(self,song,tgtpath):

        srcpath = song[Song.path]

        metadata=dict(
            artist=song[Song.artist],
            album=song[Song.album],
            title=song[Song.title]
        )

        if Song.eqfactor > 0:
            vol = song[Song.equalizer] / Song.eqfactor
        else:
            vol = 1.0

        bitrate = 320
        if srcpath.lower().endswith('mp3'):
            bitrate=0

        encoder = FFmpegEncoder(self.config['yue']['encoder'])
        encoder.transcode(srcpath,tgtpath,bitrate,vol=vol,metadata=metadata)

    def instance():
        return Application.__instance

    def register(self,rule,callback,**options):

        endpoint = callback.__name__
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

