#!/usr/local/bin/python
# coding=utf-8

from aligo import Aligo
from loguru import logger
import base64
from pathlib import Path
import json
import sys
import subprocess

# 准备aligo需要的配置文件
def prepare_for_aligo(base64_userdata:str):
    # Path.home():   /home/runner/.aligo
    # wd: /home/runner/work/movie-tvshow-spider/movie-tvshow-spider

    # 1. mkdir -p /home/runner/.aligo
    # 2. 将密钥信息base64解密 转为aligo.json 追加到/home/runner/.aligo目录中
    subprocess.call('mkdir -p /home/runner/.aligo',shell=True)
    aligo_config_str = base64.b64decode(base64_userdata).decode(encoding='utf-8')
    aligo_config:dict = json.loads(aligo_config_str)
    with open(f'/home/runner/.aligo/aligo.json','w+',encoding='utf-8') as aligo_file:
        json.dump(aligo_config,aligo_file)
    
    pass

def crawling():
    aligo = Aligo()   
    personal_info = aligo.get_personal_info() 
    logger.info(f'个人信息:{personal_info}')


if __name__=='__main__':
    try:
        base64_userdata = sys.argv[1]
    except:
        base64_userdata = ''
    prepare_for_aligo(base64_userdata)
    
    crawling()
    pass
