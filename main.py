#!/usr/local/bin/python
# coding=utf-8
from time import sleep
from aligo import Aligo
from aligo.types.Null import Null
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
    movies:BaseFile = ali_drive.get_folder_by_path('movies') # type: ignore
    if type(tmm_movies) == BaseFile:
        
        movie_folders = ali_drive.get_file_list(tmm_movies.file_id)
        for movie_folder in movie_folders:
            # 判断该文件夹下面是否直接有视频文件 来区分电影和电影集
            movie_folder_files = ali_drive.get_file_list(movie_folder.file_id)
            if bool(list(filter(lambda x: x.name.endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')),movie_folder_files))):
                # 电影文件夹
                for movie_folder_file in movie_folder_files:
                    if movie_folder_file.type == 'file':
                        if movie_folder_file.name.lower().endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')):
                            # 电影mkv等视频文件名
                            movie_video = movie_folder_file.name
                            # 电影名(不带扩展名)
                            movie_name = movie_video.rsplit('.',1)[0]
                            
                            # 判断该电影文件夹是否存在nfo文件
                            if not bool(ali_drive.get_file_by_path(f'tmm/tmm-movies/{movie_folder.name}/{movie_name}.nfo')):
                                os.system(f'touch ./kodi-tmdb/movies/"{movie_video}"')
                                # 等待刮削完成
                                logger.info(f'开始刮削电影:  {movie_name}...')
                                sleep(5)
                                # 上传电影图片与nfo
                                for dirpath, dirnames, filenames in os.walk(f'./kodi-tmdb/movies'): # type: ignore
                                    # 上传图片
                                    for file_name in filenames:
                                        if file_name.startswith(f'{movie_name}') and file_name.endswith(('.jpg','.nfo')):
                                            logger.info(f'开始上传{dirpath}/{file_name}图片...')
                                            ali_drive.aligo.upload_file(f'{dirpath}/{file_name}',movie_folder.file_id)
                                if bool(ali_drive.get_file_by_path(f'tmm/tmm-movies/{movie_folder.name}/{movie_name}.nfo')):
                                    logger.success(f'电影:  {movie_name}刮削成功!')
                                    # 上传成功就将该文件夹移动到movies文件夹中 如果movies有同名文件夹 直接覆盖
                                    logger.info(f'开始移动tmm电影文件夹: {movie_folder.name}至movies')
                                    new_name = extract_movie_new_name(f'./kodi-tmdb/movies/tmdb/{movie_video}.movie.json')[0]
                                    move_res = ali_drive.aligo.move_file(file_id=movie_folder.file_id,to_parent_file_id=movies.file_id,new_name=new_name)
                                    try:
                                        file_id = move_res.file_id
                                        logger.success(f'tmm电影文件夹: {new_name}-{file_id}已成功移动至movies')
                                    except:
                                        logger.warning(f'tmm电影文件夹: {new_name}移动至movies失败,movies存在相同的文件夹!')
                                        ali_drive.aligo.move_file_to_trash(movie_folder.file_id)
                                    
                                else:
                                    logger.warning(f'电影:  {movie_name}刮削失败! 请检查电影文件名是否正确')
                                
                                
            else:
                # 电影集文件夹
                # 获取电影集下面的电影
                logger.info(f'开始刮削电影集:  {movie_folder.name}...')    
                movie_collection_id = None
                for movie_collection_folder in movie_folder_files:
                    if movie_collection_folder.type == 'folder':
                        movie_collection_files = ali_drive.get_file_list(movie_collection_folder.file_id)
                        for movie_collection_file in movie_collection_files:
                            if movie_collection_file.name.lower().endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')):
                                # 电影mkv等视频文件名
                                movie_video = movie_collection_file.name
                                # 电影名(不带扩展名)
                                movie_name = movie_video.rsplit('.',1)[0]
                                
                                # 判断该电影文件夹是否存在nfo文件
                                if not bool(ali_drive.get_file_by_path(f'tmm/tmm-movies/{movie_folder.name}/{movie_collection_folder.name}/{movie_name}.nfo')):
                                    os.system(f'touch ./kodi-tmdb/movies/"{movie_video}"')
                                    # 等待刮削完成
                                    logger.info(f'开始刮削电影集电影:  {movie_folder.name}--{movie_name}...')
                                    sleep(5)
                                    # 上传电影图片与nfo
                                    for dirpath, dirnames, filenames in os.walk(f'./kodi-tmdb/movies'): # type: ignore
                                        # 上传图片
                                        for file_name in filenames:
                                            if file_name.startswith(f'{movie_name}') and file_name.endswith(('.jpg','.nfo')):
                                                logger.info(f'开始上传{dirpath}/{file_name}图片...')
                                                ali_drive.aligo.upload_file(f'{dirpath}/{file_name}',movie_collection_folder.file_id)
                                                
                                    # 查看nfo文件是否存在
                                    if bool(ali_drive.get_file_by_path(f'tmm/tmm-movies/{movie_folder.name}/{movie_collection_folder.name}/{movie_name}.nfo')):
                                        logger.success(f'电影集电影:  {movie_folder.name}--{movie_name}刮削成功!')
                                        logger.info(f'开始移动tmm电影集文件夹: {movie_folder.name}/{movie_collection_folder.name}至movies')
                                        extract_result = extract_movie_new_name(f'./kodi-tmdb/movies/tmdb/{movie_video}.movie.json')
                                        # 重命名电影文件夹以及电影集文件夹
                                        new_name = extract_result[0]
                                        
                                        if movie_collection_id == None:
                                            if not extract_result[1]==None and not extract_result[1] == '' :
                                                # 根据解析的结果查找目标电影集文件夹
                                                find_res:BaseFile = ali_drive.get_folder_by_path(f'movies/{extract_result[1]}') # type: ignore
                                                if find_res == None:
                                                    # movies下面没有这个电影集 直接创建新的影集
                                                    create_res = ali_drive.aligo.create_folder(f'{extract_result[1]}',movies.file_id)
                                                    movie_collection_id = create_res.file_id
                                                else:
                                                    movie_collection_id = find_res.file_id
                                            else:
                                                # 当前电影文件夹不属于任何电影集 直接移动到movies下
                                                movie_collection_id = movies.file_id
                                        # 移动电影文件夹
                                        move_res = ali_drive.aligo.move_file(file_id=movie_collection_folder.file_id,to_parent_file_id=movie_collection_id,new_name=new_name)  # type: ignore
                                        try:
                                            file_id = move_res.file_id
                                            logger.success(f'tmm电影集文件夹: {new_name}-{file_id}已成功移动至movies')
                                        except:
                                            logger.warning(f'tmm电影集文件夹: {new_name}移动至movies失败,movies存在相同的文件夹!')
                                            ali_drive.aligo.move_file_to_trash(movie_collection_folder.file_id)
                                    else:
                                        logger.warning(f'电影:  {movie_name}刮削失败! 请检查电影文件名是否正确')
                                    
                logger.success(f'电影集:  {movie_folder.name}刮削成功!')
                # 检查电影集文件夹数量 如果为0 删除该文件夹
                collection_file_list = ali_drive.get_file_list(parent_file_id=movie_folder.file_id)
                if len(list(filter(lambda x: x.type=='folder',collection_file_list)))==0:
                    ali_drive.move_to_trash(movie_folder.file_id)
                

def extract_movie_new_name(movie_json_path:str):
    with open(f'{movie_json_path}','r+',encoding='utf-8') as movie_json_file:
        movie_json_data = json.load(movie_json_file)
    # 中文名 年代
    movie_new_name = f'{movie_json_data["title"]} ({movie_json_data["release_date"].split("-")[0]})'
    logger.info(f'解析电影中文名称:{movie_new_name}')
    try:
        movie_collection_new_name = movie_json_data['belongs_to_collection']['name']
        logger.info(f'解析电影集中文名称:{movie_collection_new_name}')
    except:
        movie_collection_new_name = None
    return (movie_new_name,movie_collection_new_name)



def crawl_shows(ali_drive:Alidrive):
    pass 
    
if __name__=='__main__':
    try:
        base64_userdata = sys.argv[1]
    except:
        base64_userdata = open(f'aliyundrive/token','r+',encoding='utf-8').read()
        
        
    prepare_for_aligo(base64_userdata) # type: ignore
    
    crawling()
    pass
