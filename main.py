#!/usr/local/bin/python
# coding=utf-8
from time import sleep
from aligo import Aligo
from aliyundrive.ali_drive import Alidrive
from loguru import logger
import base64
from aligo.types.BaseFile import BaseFile
from aligo.response.CreateFileResponse import CreateFileResponse
from pathlib import Path
import json
import sys
import subprocess
import os

# 准备aligo需要的配置文件
def prepare_for_aligo(base64_userdata:str):
    # Path.home():   /home/runner/.aligo
    # wd: /home/runner/work/movie-tvshow-spider/movie-tvshow-spider

    # 1. mkdir -p /home/runner/.aligo
    # 2. 将密钥信息base64解密 转为aligo.json 追加到/home/runner/.aligo目录中
    subprocess.call('mkdir -p /home/runner/.aligo',shell=True)
    aligo_config_str = base64.b64decode(base64_userdata).decode(encoding='utf-8')
    aligo_config:dict = json.loads(aligo_config_str)
    try:
        with open(f'/home/runner/.aligo/aligo.json','w+',encoding='utf-8') as aligo_file:
            json.dump(aligo_config,aligo_file)
    except:
        pass

def crawling():
    ali_drive = Alidrive(Aligo())
    
    crawl_movie(ali_drive)
    
    crawl_shows(ali_drive)
    
    # 2. 获取剧集文件夹 TODO
    
    pass


 
def crawl_movie(ali_drive:Alidrive):
    # 获取电影文件
      # 获取tmm-movies下面的所有电影文件 最大支持两级目录(即有两种可能: a.tmm/tmm-movies/电影文件夹/电影名.mkv  b.tmm/tmm-movies/电影集/电影文件夹/电影名.mkv)
      # 通过电影名在kodi-tmdb/movies下创建一个临时空文件 '文件名.mkv'
      # 等待刮削完成
      # 将生成的nfo文件和海报 艺术图 上传至阿里云盘
      # 根据tmdb文件夹的 文件名.movie.json 读取演员图片链接  下载演员图片 上传至当前电影文件夹下的.actors文件夹下
      # 刮削电影文件的中文字幕 上传到同文件夹下
    tmm_movies = ali_drive.get_folder_by_path('tmm/tmm-movies')
    movie_names = []
    if type(tmm_movies) == BaseFile:
        
        movie_folders = ali_drive.get_file_list(tmm_movies.file_id)
        for movie_folder in movie_folders:
            
            movie_folder_files = ali_drive.get_file_list(movie_folder.file_id)
            for movie_folder_file in movie_folder_files:
                if movie_folder_file.type == 'file':
                    if movie_folder_file.name.lower().endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')):
                        # 电影mkv等视频文件名
                        movie_video = movie_folder_file.name
                        # 电影名(不带扩展名)
                        movie_name = movie_video.rsplit('.',1)[0]
                        movie_names.append(movie_name)
                        
                        # 判断该电影文件夹是否存在nfo文件
                        if not bool(ali_drive.get_file_by_path(f'tmm/tmm-movies/{movie_folder.name}/{movie_name}.nfo')):
                            os.system(f'touch ./kodi-tmdb/movies/"{movie_video}"')
                            # 等待刮削完成
                            sleep(3)
                            # 上传电影图片与nfo
                            for dirpath, dirnames, filenames in os.walk(f'./kodi-tmdb/movies'): # type: ignore
                                # 上传图片
                                for file_name in filenames:
                                    if file_name.startswith(f'{movie_name}') and file_name.endswith(('.jpg','.nfo')):
                                        logger.info(f'开始上传{dirpath}/{file_name}图片...')
                                        ali_drive.aligo.upload_file(f'{dirpath}/{file_name}',movie_folder.file_id)
                                # 上传演员图片
                                
                                # 创建.actors文件夹
                                ali_drive.aligo.create_folder(name='.actors',parent_file_id=movie_folder.file_id,check_name_mode='refuse')
                                # 获取演员图片链接
                                movie_actors(movie_video)
                else:
                    # 电影集
                    pass
            


def crawl_shows(ali_drive:Alidrive):
    pass 
    

def movie_actors(movie_video:str):
    with open(f'./kodi-tmdb/movies/tmdb/{movie_video}.movie.json','r+',encoding='utf-8') as movie_json_file:
        logger.info(movie_json_file.read())


if __name__=='__main__':
    try:
        base64_userdata = sys.argv[1]
    except:
        base64_userdata = open(f'aliyundrive/token','r+',encoding='utf-8').read()
    prepare_for_aligo(base64_userdata) # type: ignore
    
    crawling()
    pass
