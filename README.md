# deployphpcode
代码发布工具：web部署系统工具，配置简单、免安装、开箱即用。发布过程可视化，支持git版本管理，根据tag版本 增量发布，支持PHP，Python等各种web代码，一键发布。

### 功能特色
1. 配置化 （包括：git仓库、分支，服务器ip、目录、ssh账号）。
2. 发布过程可视化，有步骤进度展示，显示每个步骤的成功失败状态。
3. 记录发布历史，什么时间发布了什么版本，有版本发布校验 防止重复发布。
4. 增量发布，只发布有修改变动的文件，加快发布效率。
5. 使用简单、操作便捷，无需安装，修改好配置 即可投入使用，一键操作发布。
6. 实战检验，经过4-5个项目 频繁的日常发布使用验证，从内网发布到aliyun/aws等。

### 目的
> 1.ftp上传代码太low

> 2.搭建jenkins、walle等发布平台太繁杂

于是动手写个脚本工具，简单便捷，即配即用。

### 准备
需要准备的内容：
1. git仓库
2. 工具机，用于放置发布工具（也可以在本地开发机上）。
3. 目标服务器，代码将要发布到上面的机器，一般为正式环境。
4. 工具机与目标服务器间配置好ssh免密登录。

### 使用
1. 下载本项目放置到工具机上, 如 /home/tool/
2. 编辑配置文件conf.ini
3. 在git仓库上需要发布的版本打上tag（如:v1.1.0）
4. 进入工具机的放置目录 cd /home/tool/, 执行 sh deploy.sh v1.1.0

### 配置说明
```bash
[app]
"项目名称"
name=myapp

[git]
"git仓库地址"
repo=git@127.0.0.1:/home/git/repo/myapp.git
"git分支，master、develop等"
branch=develop

[ssh]
"目标服务器ssh登录账号"
user=www
"目录服务器ip"
host=192.168.1.101
"ssh账号public-key，没有的话留空"
key=

[prod]
"代码发布目录"
path=/home/www/webroot/myapp/
```

### 截图
[![发布成功](http://chuantu.xyz/t6/741/1611318073x1700468761.png "发布成功")](http://chuantu.xyz/t6/741/1611318073x1700468761.png "发布成功")


[![](http://chuantu.xyz/t6/741/1611318003x2073530386.png)](http://chuantu.xyz/t6/741/1611318003x2073530386.png)

[![发布失败](http://chuantu.xyz/t6/741/1611317933x2073530386.png "发布失败")](http://chuantu.xyz/t6/741/1611317933x2073530386.png "发布失败")
