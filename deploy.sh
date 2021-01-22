#!/bin/bash

basepath=$(cd `dirname $0`; pwd)
conf=$basepath"/conf.ini"

function GetKey(){
    section=$(echo $1 | cut -d '.' -f 1)
    key=$(echo $1 | cut -d '.' -f 2)
    sed -n "/\[$section\]/,/\[.*\]/{  
     /^\[.*\]/d  
     /^[ \t]*$/d  
     /^$/d  
     /^#.*$/d  
     s/^[ \t]*$key[ \t]*=[ \t]*\(.*\)[ \t]*/\1/p  
    }" $conf
}


name=$(GetKey "app.name")
name=`echo $name | tr -d '\r'`

repo=$(GetKey "git.repo")
repo=`echo $repo | tr -d '\r'`
branch=$(GetKey "git.branch")
branch=`echo $branch | tr -d '\r'`

sshuser=$(GetKey "ssh.user")
sshuser=`echo $sshuser | tr -d '\r'`
sshhost=$(GetKey "ssh.host")
sshhost=`echo $sshhost| tr -d '\r'`
sshkey=$(GetKey "ssh.key")
sshkey=`echo $sshkey| tr -d '\r'`

ppath=$(GetKey "prod.path")
ppath=`echo $ppath | tr -d '\r'`


deploytag=$1
logfile=$basepath"/deploy.log"

echo -e "\n"
echo -e "\e[34m 开始发布 \e[0m"
echo -e "\e[34m --------------------------------------------------------- \e[0m"
echo -e "\e[34m 项目: $name \e[0m"
echo -e "\e[34m 仓库: $repo \e[0m"
echo -e "\e[34m 分支: $branch \e[0m"
echo -e "\e[34m --------------------------------------------------------- \e[0m"
echo -e "\e[34m 服务器: $sshhost \e[0m"
echo -e "\e[34m 目录: $ppath \e[0m"
echo -e "\e[34m --------------------------------------------------------- \e[0m"

echo -e "\e[34m 编排任务（1.拉取 >> 2.打包 >> 3.推送 >> 4.解压 >> 5.完成）\n \e[0m"

if [[ $deploytag = "" ]]
then
    echo -e "\e[34m 1.拉取    ---- \e[0m\e[41m 失败(tag号参数错误) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi

i=false
if [ -e $logfile ]
then
    history=`cat $logfile | awk -F '----' '{print $2}'`
    (echo $history | grep -w $name"("$deploytag")" >/dev/null) && i=true
fi

if [[ $i = true ]]
then
    echo -e "\e[34m 1.拉取    ---- \e[0m\e[41m 失败(该版本已发布) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi


if [ $repo = "" ]
then
    echo -e "\e[34m 1.拉取    ---- \e[0m\e[41m 失败(仓库错误) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi

tmpath='/tmp/deploy-'$name'/'

if [ -d $tmpath ]
then 
    rm -rf $tmpath
fi


git clone -b $branch $repo $tmpath >/dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "\e[34m 1.拉取    ---- \e[0m\e[41m 失败(clone代码仓库错误) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi

cd $tmpath

git pull >/dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "\e[34m 1.拉取    ---- \e[0m\e[41m 失败(分支拉取错误) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi

echo -e "\e[34m 1.拉取    ---- \e[0m\e[42m 成功 \e[0m"

lasttag=`git ls-remote --tags origin | awk '{sub("refs/tags/", ""); print $2"----"$1}' |sort -k1 -Vr | head -1`
pretag=`git ls-remote --tags origin | awk '{sub("refs/tags/", ""); print $2"----"$1}' |sort -k1 -Vr | head -2 | tail -1`

newtag=`echo $lasttag | awk -F'----' '{print $1}'`

if [[ $deploytag != $newtag ]]
then
    echo -e "\e[34m 2.打包    ---- \e[0m\e[41m 失败(tag号错误) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi

newtagid=`echo $lasttag | awk -F'----' '{print $2}'`
pretagid=`echo $pretag | awk -F'----' '{print $2}'`

if [ $newtagid = $pretagid -o $newtagid = "" -o $pretagid = "" ]
then
    echo -e "\e[34m 2.打包    ---- \e[0m\e[41m 失败(tag号错误) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi


if [ ! -d $tmpath"tar/" ]
then
    mkdir $tmpath"tar/"
fi


tarname=$tmpath"tar/"$name"-"$newtag".tar.gz"
git diff $pretagid $newtagid --name-only | xargs tar -czf $tarname

if [ $? -ne 0 ]; then
    echo -e "\e[34m 2.打包    ---- \e[0m\e[41m 失败(tag版本差异比较错误) \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0
fi

echo -e "\e[34m 2.打包    ---- \e[0m\e[42m 成功 \e[0m"


if [ $sshkey != '' ];then
    sshkey=" -i "$sshkey
fi


if [ -e $tarname ]
then
    scp $sshkey $tarname $sshuser@$sshhost:~  >/dev/null 

    if [ $? -ne 0 ]; then
        echo -e "\e[34m 3.推送    ---- \e[0m\e[41m 失败 \e[0m"
        echo -e "\r"
        echo -e "\e[41m 发布结束 \e[0m"
        echo -e "\n"
        exit 0
    fi

    echo -e "\e[34m 3.推送    ---- \e[0m\e[42m 成功 \e[0m"

    ssh $sshkey $sshuser"@"$sshhost >/dev/null 2>&1 << eeooff

    cd ~

    if [ -e /home/$sshuser/$name-$newtag".tar.gz" ]
    then
        tar -zxf /home/$sshuser/$name-$newtag".tar.gz" -C $ppath >/dev/null
        rm -f /home/$sshuser/$name-$newtag".tar.gz"
    fi

    exit

eeooff

    if [ $? -ne 0 ]; then
        echo -e "\e[34m 4.解压    ---- \e[0m\e[41m 失败 \e[0m"
        echo -e "\r"
        echo -e "\e[41m 发布结束 \e[0m"
        echo -e "\n"
        exit 0
    fi

    echo -e "\e[34m 4.解压    ---- \e[0m\e[42m 成功 \e[0m"

else
    echo -e "\e[34m 3.打包    ---- \e[0m\e[41m 失败 \e[0m"
    echo -e "\r"
    echo -e "\e[41m 发布结束 \e[0m"
    echo -e "\n"
    exit 0

fi

rm -rf $tmpath

echo -e "\e[34m 5.发布    ---- \e[0m\e[42m 成功 \e[0m"
echo -e "\r"
echo -e "\e[42m 发布完成 \e[0m"
echo -e "\n"
echo `date +%Y-%m-%d\ %H:%M:%S`" ---- "$name"("$deploytag")" >> $logfile
