
import posixpath
import stat
import traceback
import time
import calendar
import os, sys

from .source import DataSource,DirectorySource,SourceNotImplemented
try:
    from paramiko.client import SSHClient
    import paramiko
    from  paramiko.ssh_exception import BadHostKeyException
except ImportError:
    paramiko = None
    SSHClient = None
    BadHostKeyException = None


# client
#'close', 'connect', 'exec_command', 'get_host_keys', 'get_transport',
#'invoke_shell', 'load_host_keys', 'load_system_host_keys', 'open_sftp',
#'save_host_keys', 'set_log_channel', 'set_missing_host_key_policy']

#ftp
#'chdir', 'chmod', 'chown', 'close', 'file', 'from_transport', 'get',
#'get_channel', 'getcwd', 'getfo', 'listdir', 'listdir_attr',
#'listdir_iter', 'logger', 'lstat', 'mkdir', 'normalize', 'open',
#'put', 'putfo', 'readlink', 'remove', 'rename', 'request_number',
#'rmdir', 'sock', 'stat', 'symlink', 'truncate', 'ultra_debug', 'unlink',
#'utime']

#  listdirattr: 'attr', 'filename', 'from_stat', 'longname', 'st_atime', 'st_gid', 'st_mode', 'st_mtime', 'st_size', 'st_uid'


#connect(hostname, port=22, username=None, password=None, pkey=None,
#    key_filename=None, timeout=None, allow_agent=True, look_for_keys=True,
#    compress=False, sock=None, gss_auth=False, gss_kex=False,
#    gss_deleg_creds=True,
#    gss_host=None, banner_timeout=None)
# ssh ["root@127.0.0.1", "-p", "2222", "-o", "Compression=yes",
#      "-o", "DSAAuthentication=yes", "-o", "LogLevel=FATAL", "-o",
#      "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=no", "-o",
#      "UserKnownHostsFile=/dev/null", "-i",
#      "/Users/nsetzer/git/vagrant/cogito/.vagrant/machines/default/virtualbox/private_key"]


def getSSHConfig(config_path, host):
    """
        config_path : path to the ssh config
        host: host name to lookup

        returns the user config suitable for
        connecting to the given host
    """
    ssh_config = paramiko.SSHConfig()

    if config_path is None:
        user_config_file = os.path.expanduser("~/.ssh/config")
    else:
       user_config_file = os.path.expanduser(config_path)

    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            ssh_config.parse(f)

    user_config = ssh_config.lookup(host)

    return user_config


class SSHClientSource(DataSource):

    """SSHClientSource uses paramiko to establish an ssh/sftp connection.

    http://docs.paramiko.org/en/2.1/api/sftp.html
    """

    @staticmethod
    def fromPrivateKey(host,port=22,username=None,password=None,private_key=None):
        """deprecated see connect_v2 """

        #ssh -i /path/to//private_key user@localhost -p 2222
        #ssh -i /path/to//private_key username@host -p port

        if SSHClient is None:
            raise Exception("Paramiko not installed")

        src = SSHClientSource()
        print(host,port,username,password,private_key)

        pkey = None
        if private_key: # non-null, non-empty
            passphrase = "" # TODO: support passphrases
            pkey=paramiko.RSAKey.from_private_key_file(\
                private_key,passphrase)

        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print("\n---\nConnect With: host=%s:%s user=%s privatekey=`%s`\n"%(\
              host,port,username,private_key))

        try:
            if pkey:
                client.connect(host,port=port,
                               username=username,
                               pkey=pkey,timeout=1.0,compress=True)
            else:
                client.connect(host,port=port,
                               username=username,password=password,
                               timeout=1.0,compress=True)
        except BadHostKeyException as e:
            sys.stderr.write("got:      %s\n"%e.key.asbytes());
            sys.stderr.write("expected: %s\n"%e.expected_key.asbytes());

            msg = "Connection error on %s:%s using privatekey=%s\n"%(\
                host,port,private_key)
            msg += "you may need to clear ~/.ssh/known_hosts "+\
                "for entries related to %s:%s\n"%(host,port);
            sys.stderr.write(msg);
            raise Exception(msg);
        src.client = client
        src.ftp = client.open_sftp()

        src.host=host
        src.port=port

        return src

    @staticmethod
    def connect_v2(host,port,username,password=None,private_key=None,config_path=None):

        """
        Note:
            it may be possible to escalate root priveleges
            stdin,stdout,stderr = ssh.exec_command("sudo su; whoami", get_pty=True)
            various strategies exist for entering the password.
        """
        # build a configuration from the options
        cfg = {"hostname":host,
               "port":port,
               "username":username,
               "timeout":10.0,"compress":True,
               "allow_agent":False,
               "look_for_keys":False}
        if password is not None:
            cfg["password"] = password

        user_config = getSSHConfig(config_path,host)

        # copy the settings from the userconfig, overwriting the cfg.
        for k in ('hostname', 'username', 'port'):
            if k in user_config:
                cfg[k] = user_config[k]

        # proxy command allows for two factor authentication
        if 'proxycommand' in user_config:
            cfg['sock'] = paramiko.ProxyCommand(user_config['proxycommand'])
            cfg['timeout'] = 45.0; # give extra time for two factor

        print(cfg)

        cfg['pkey'] = None
        if private_key: # non-null, non-empty
            passphrase = "" # TODO: support passphrases
            cfg['pkey']=paramiko.RSAKey.from_private_key_file(\
                        private_key,passphrase)

        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #client.set_missing_host_key_policy(paramiko.WarningPolicy())

        try:
            client.connect(**cfg)
        except BadHostKeyException as e:
            sys.stderr.write("got:      %s\n"%e.key.asbytes());
            sys.stderr.write("expected: %s\n"%e.expected_key.asbytes());

            msg = "Connection error on %s:%s using privatekey=%s\n"%(\
                host,port,private_key)
            msg += "you may need to clear ~/.ssh/known_hosts "+\
                "for entries related to %s:%s\n"%(host,port);
            sys.stderr.write(msg);
            raise Exception(msg);

        src = SSHClientSource()
        src.client = client
        src.ftp = client.open_sftp()

        src.host=host
        src.port=port
        src.config=cfg

        return src


    def __init__(self):
        super(SSHClientSource, self).__init__()

    def name(self):
        b = self.__class__.__name__.replace("Source","")

        return "%s_%s_%s"%(b,self.host,self.port)

    def islocal(self):
        return False

    def isOpenSupported(self):
        return False

    def isGetPutSupported(self):
        return True

    def root(self):
        return "/"

    def join(self,*args):
        return posixpath.join(*args)

    def relpath(self,path,base):
        return posixpath.relpath(path,base)

    def normpath(self,path,root=None):
        #path = posixpath.expanduser(path)
        # todo replace with /home/$user or /Users/$user
        if root and not path.startswith("/"):
            path = posixpath.join(root,path)
        return posixpath.normpath( path )

    def listdir(self,path):
        return self.ftp.listdir(path)

    def parent(self,path):
        p,_ = posixpath.split(path)
        return p

    def getfo(self,path,fo,callback=None):
        """

        """
        self.ftp.getfo(path,fo,callback=callback)


    def putfo(self,path,fo,callback=None):
        """
        """
        self.ftp.putfo(fo,path,callback=callback,confirm=False)

    def move(self,oldpath,newpath):
        self.ftp.rename(oldpath,newpath)

    def delete(self,path):
        if self.isdir(path):
            self.ftp.rmdir( path )
        elif self.islink(path):
            self.ftp.unlink(path)
        else:
            self.ftp.remove( path )

    def open(self,path,mode):
        raise SourceNotImplemented("files cannot be opened natively by ssh")

    def exists(self,path):
        try:
            self.ftp.stat(path)
        except FileNotFoundError:
            return False
        return True

    def isdir(self,path):
        try:
            return stat.S_ISDIR(self.ftp.stat(path).st_mode)
        except:
            return False

    def islink(self,path):
        try:
            return stat.S_ISLNK(self.ftp.stat(path).st_mode)
        except:
            return False

    def mkdir(self,path):
        # TODO: this model should be used everywhere...
        if not self.exists(path):
            self.ftp.mkdir(path,0o755)
            return
        elif not self.isdir(path):
            raise SourceException("path exists and is not directory")

    def mklink(self,target,path):
        self.ftp.symlink(target,path)

    def readlink(self,path):
        return self.ftp.readlink(path)

    def split(self,path):
        return posixpath.split(path)

    def splitext(self,path):
        return posixpath.splitext(path)

    def stat(self,path):

        st = self.ftp.lstat(path)

        isLink = DirectorySource.IS_REG
        if stat.S_ISLNK(st.st_mode):
            # only links are stated twice. we first need to know
            # if it is a link, and if it is, what does it point to.
            try:
                st = self.ftp.stat(path)
            except FileNotFoundError:
                isLink = DirectorySource.IS_LNK_BROKEN
            else:
                isLink = DirectorySource.IS_LNK

        result = {
            "isDir" : stat.S_ISDIR(st.st_mode),
            "isLink" : isLink,
            # TODO: always store time without timezone info....?
            "mtime" : calendar.timegm(time.localtime(st.st_mtime)),
            "ctime" : 0,
            "size"  : st.st_size,
            "mode"  : stat.S_IMODE(st.st_mode)
        }

        return result

    def stat_fast(self,path):
        """ there is no such thing as a "fast" stat
        for this file system so just call stat
        """
        return self.stat(path)

    def chmod(self,path,mode):
        print("chmod not implemented")

    def getExportPath(self,path):
        return path # nothing to do

    def close(self):

        self.ftp.close()
        self.ftp = None
        self.client.close()
        self.client = None

        super().close()
