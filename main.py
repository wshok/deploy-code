import time
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import json
import urllib
import urlparse
import socket
import commands
import sqlite3
import os
import shutil
import paramiko
import sys
from string import Template


class Worker():
    def __init__(self):
        self.project_name = ''
        self.project_ver = ''

        self.repo = ''
        self.branch = ''
        self.pullpath = '/tmp/deploy-%s'

        self.host = ''
        self.port = 22
        self.user = ''
        self.password = ''
        self.key = ''

        self.last_tag_id = ''
        self.second_last_tag_id = ''
        self.zip_path = ''

        self.db = Db('test.db')

        self.pwd = os.getcwd()

        self.config()


    def config(self):

        row = self.db.find("select value from config where name = 'repo'")
        self.repo = row[0] if row else ''

        row = self.db.find("select value from config where name = 'branch'")
        self.branch = row[0] if row else 'master'

        row = self.db.find("select value from config where name = 'host'")
        self.host = row[0] if row else ''

        row = self.db.find("select value from config where name = 'user'")
        self.user = row[0] if row else ''

        row = self.db.find("select value from config where name = 'password'")
        self.password = row[0] if row else ''

        row = self.db.find("select value from config where name = 'key'")
        self.key = row[0] if row else ''

        
    def seter(self, name, ver):
        self.project_name = name
        self.project_ver = ver


    # step 1
    def pull(self):

        os.chdir(self.pwd)

        pullpath = self.pullpath % self.project_name

        if os.path.exists(pullpath):
            shutil.rmtree(pullpath)


        projects = self.projects()

        if self.project_name not in projects.split(','):
            return {"code":0, "msg":"project error"} 

        sql = "select id from record where project='%s' and version='%s'" % (self.project_name, self.project_ver)
        has_deployed = self.db.find(sql)
        if has_deployed:
            return {"code":0, "msg":"deployed error"}


        repo = self.repo % self.project_name
        cmd = 'git clone -b %s %s %s >/dev/null' % (self.branch, repo, pullpath)
        status,output = commands.getstatusoutput(cmd)
        if status > 0:
            return {"code":0, "msg":"pull error"}

        os.chdir(pullpath)
        os.system('git pull >/dev/null')

        # last tag info
        cmd1 = '''git ls-remote --tags origin | awk '{sub("refs/tags/", ""); print $2","$1}' |sort -k1 -Vr | head -1'''
        # second-last tag info
        cmd2 = '''git ls-remote --tags origin | awk '{sub("refs/tags/", ""); print $2","$1}' |sort -k1 -Vr | head -2 | tail -1'''
        
        last_tag = commands.getoutput(cmd1)
        second_last_tag = commands.getoutput(cmd2)

        if last_tag == "" or second_last_tag == "":
            return {"code":0, "msg":"tag error not found"}

        cmd3 = "echo %s | awk -F',' '{print $1}'" % last_tag
        last_tag_ver = commands.getoutput(cmd3)

        if last_tag_ver != self.project_ver:
            return {"code":0, "msg":"tag error not eq"}


        # last tag id
        cmd4 = "echo %s | awk -F',' '{print $2}'" % last_tag
        # second last tag id
        cmd5 = "echo %s | awk -F',' '{print $2}'" % second_last_tag

        self.last_tag_id = commands.getoutput(cmd4)
        self.second_last_tag_id = commands.getoutput(cmd5)

        return {"code":1, "msg":""}


    # step 2
    def zip(self):
        pullpath = self.pullpath % self.project_name

        if os.path.exists(pullpath):
            os.chdir(pullpath)
        else:
            return {"code":0, "msg":"path error"}

        if self.second_last_tag_id == "" or self.last_tag_id == "":
            return {"code":0, "msg":"tag error"}

        self.zip_path = '%s/%s-%s.tar.gz' % (pullpath,self.project_name,self.project_ver)
        cmd = 'git diff %s %s --name-only | xargs tar -czf %s >/dev/null' % (self.second_last_tag_id, self.last_tag_id, self.zip_path)
        commands.getoutput(cmd)

        if os.path.exists(self.zip_path) == False:
            return {"code":0, "msg":"zip error"}

        return {"code":1, "msg":""}

    
    # step 3
    def push(self):
        key = ('-i %s' % self.key) if self.key else ''

        if os.path.exists(self.zip_path) == False:
            return {"code":0, "msg":"zip error"}

        if self.host == "" or self.user == "":
            return {"code":0, "msg":"ssh host|user error"}

        cmd = "scp %s %s %s@%s:~ >/dev/null" % (key,self.zip_path,self.user,self.host)
        status,output = commands.getstatusoutput(cmd)
        if status > 0:
            return {"code":0, "msg":"push error"}

        os.system('rm -f %s' % self.zip_path)

        return {"code":1, "msg":""}


    # step 4
    def unzip(self):

        row = self.db.find("select value from config where name = 'release_path'")
        release_path = row[0] if row else ''

        if self.host == "" or self.user == "":
            return {"code":0, "msg":"ssh host|user error"}

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            private_key = paramiko.RSAKey.from_private_key_file(self.key)
            ssh.connect(hostname=self.host, port=self.port, username=self.user, pkey=private_key)
        except:
            return {"code":0, "msg":"ssh error"}

        zip_file = '%s-%s.tar.gz'%(self.project_name,self.project_ver)

        ssh.exec_command('cd ~')
        stdin, stdout, stderr = ssh.exec_command('ls %s'%zip_file)
        res, err = stdout.read(), stderr.read()
        if err:
            return {"code":0, "msg":err}

        cmd = 'tar -zxf %s -C %s' % (zip_file, release_path)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        res, err = stdout.read(), stderr.read()
        if err:
            return {"code":0, "msg":err}

        ssh.exec_command('rm -f %s' % zip_file)
        ssh.close()

        sql = 'insert into record values(NULL, "%s", "%s", "%s")' % (self.project_name, self.project_ver, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        self.db.save(sql)

        return {"code":1, "msg":""}


    def projects(self):
        row = self.db.find("select value from config where name = 'projects'")
        data = row[0] if row else ''
        return data

    def setting(self):
        rows = self.db.select("select name,value from config")
        return rows

    def save(self, data):
        try:
            for x,y in data.items():
                self.db.save("update config set value='%s' where name='%s'" % (y, x))
        except Exception as e:
            return {"code":0, "msg":"update error: %s" % e}

        return {"code":1, "msg":""}


class Db(object):
    def __init__(self, dbpath):
        self.dbpath = dbpath


    def find(self, sql):
        conn = sqlite3.connect(self.dbpath)
        c = conn.cursor()

        cursor = c.execute(sql)
        row = cursor.fetchone()
        conn.close()

        return row

    def select(self, sql):
        conn = sqlite3.connect(self.dbpath)
        c = conn.cursor()

        cursor = c.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        return rows

    def save(self, sql):
        conn = sqlite3.connect(self.dbpath)
        c = conn.cursor()
        c.execute(sql)
        conn.commit()
        conn.close()        


class WebHandler(BaseHTTPRequestHandler):
    p = Worker()

    def do_GET(self):
        paths = self.path

        query = urllib.splitquery(paths)
        datas = query[1]

        # if datas != None:
        #     params = urlparse.parse_qs(datas)
        #     id = params['id'][0]

        result = ''
        if paths == '/favicon.ico':
            self.wfile.write(bytes(''))
        elif paths == '/bg.jpg':
            f = open('bg.jpg', 'r')
            result = f.read()
            f.close()
        elif paths == '/projects':
            result = WebHandler.p.projects()
        elif paths == '/setting':
            f = open('setting.html', 'r')
            result = f.read()
            f.close()

            setting = WebHandler.p.setting()
            setting = dict((x.encode('utf-8'), y.encode('utf-8')) for x, y in setting)

            tempTemplate  = Template(result)
            result = tempTemplate.substitute(setting)
        else:
            f = open('index.html', 'r')
            result = f.read()
            f.close()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(result))


    def do_POST(self):
        paths = self.path
        if paths == '/favicon.ico':
            self.wfile.write(bytes(''))

        req_datas = self.rfile.read(int(self.headers['content-length']))
        params = json.loads(req_datas.decode('utf-8'))
        
        project_name = params['project'] if 'project' in params else ''
        project_ver = params['ver'] if 'ver' in params else ''

        WebHandler.p.seter(project_name, project_ver)

        result = ''
        if paths == '/pull':
            result = WebHandler.p.pull()
        elif paths == '/zip':
            result = WebHandler.p.zip()
        elif paths == '/push':
            result = WebHandler.p.push()
        elif paths == '/unzip':
            result = WebHandler.p.unzip()
        elif paths == '/setting':
            result = WebHandler.p.save(params)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(result))


def start_server(port):
    httpd = HTTPServer(('0.0.0.0', port), WebHandler)
    httpd.serve_forever()

port = 8000
try:
    start_server(port)
except KeyboardInterrupt:
    sys.exit('exit')
