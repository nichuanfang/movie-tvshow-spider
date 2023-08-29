#!/usr/local/bin/python
# coding=utf-8
from time import sleep
from aligo import Aligo,EMailConfig
from aligo.types.Enum import CheckNameMode
from pathlib import Path
import time
import random
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
import re
import requests
# 剧集正则
SEASON_PATTERN = r'((S\s*[\d]+)|(s\s*[\d]+)|(season\s*[\d]+)|(Season\s*[\d]+)|(第\s*[\d]+\s*季)|(第\s*[一|二|三|四|五|六|七|八|九|十]\s*季))'

# 季
SEASON_DICT = {
    '一': '01',
    '二': '02',
    '三': '03',
    '四': '04',
    '五': '05',
    '六': '06',
    '七': '07',
    '八': '08',
    '九': '09',
    '十': '10'
}
# 季图片url地址前缀
SEASON_BASE_URL = 'https://image.tmdb.org/t/p/original'

# 准备aligo需要的配置文件
def prepare_for_aligo(base64_userdata:str,QQ_SMTP_PASSWORD:str):
    # Path.home():   /home/runner/.aligo
    # wd: /home/runner/work/movie-tvshow-spider/movie-tvshow-spider

    # 1. mkdir -p /home/runner/.aligo
    # 2. 将密钥信息base64解密 转为aligo.json 追加到/home/runner/.aligo目录中
    subprocess.call('mkdir -p /home/runner/.aligo',shell=True)
    aligo_config_str = base64.b64decode(base64_userdata).decode(encoding='utf-8')
    aligo_config:dict = json.loads(aligo_config_str)
    expire_time:str = aligo_config['expire_time']
    # 计算距离今天的天数
    expire_time = time.strptime(expire_time,'%Y-%m-%dT%H:%M:%SZ')
    expire_time = time.mktime(expire_time)
    now = time.time()
    days = (now - expire_time) / (24 * 60 * 60)
    if days >= 30:
        # 重新通过扫码登录
        email_config = EMailConfig(
        email='1290274972@qq.com',
        host='smtp.qq.com',
        port=465,
        user='1290274972@qq.com',
        password=QQ_SMTP_PASSWORD,
        )
        # 删除aligo_config_folder = Path.home().joinpath('.aligo') / 'aligo.json文件
        aligo_config_folder = Path.home().joinpath('.aligo') / 'aligo.json'
        if aligo_config_folder.exists():
            aligo_config_folder.unlink()
        aligo = Aligo(email=email_config)
        aligo_config = json.loads(aligo_config_folder.read_text(encoding='utf8'))
        # 将配置信息base64编码更新到github的secrets中
        aligo_config_str = json.dumps(aligo_config)
        aligo_config_str = base64.b64encode(aligo_config_str.encode(encoding='utf-8')).decode(encoding='utf-8')
        # 执行linux命令
        os.system(f'echo "aligo_token={aligo_config_str}" >> "$GITHUB_OUTPUT"')
        return aligo
    else:
        try:
            with open(f'/home/runner/.aligo/aligo.json','w+',encoding='utf-8') as aligo_file:
                json.dump(aligo_config,aligo_file)
                return Aligo()
        except:
            return Aligo()

def crawling(aligo:Aligo):
    ali_drive = Alidrive(aligo)
    # 刮削电影
    crawl_movie(ali_drive)
    # 刮削剧集
    crawl_shows(ali_drive)
 
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
            if movie_folder.type == 'file':
                continue
            # 判断该文件夹下面是否直接有视频文件 来区分电影和电影集
            movie_folder_files = ali_drive.get_file_list(movie_folder.file_id)
            if bool(list(filter(lambda x: x.name.endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')),movie_folder_files))): # type: ignore
                # 电影文件夹
                # 只保留最大的视频文件
                max_size = 0
                movie_folder_file:BaseFile = None # type: ignore
                dp = []
                for item in movie_folder_files:
                    if item.type=='file' and item.name.endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')):
                        dp.append(item)
                        if max_size < item.size:
                            max_size = item.size
                            movie_folder_file = item
                if len(dp)>1:
                    dp.remove(movie_folder_file)
                    # 移除其他视频文件
                    for dpi in dp:
                        ali_drive.aligo.move_file_to_trash(dpi.file_id)
                
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
                                extract_res = extract_movie_new_name(f'./kodi-tmdb/movies/tmdb/{movie_video}.movie.json')
                                new_name = extract_res[0]
                                dest_id = movies.file_id
                                # 如果电影集文件夹存在 则新增至电影集
                                if extract_res[1] != None:
                                    collection_res:BaseFile = ali_drive.get_folder_by_path(f'movies/{extract_res[1]}') # type: ignore
                                    if collection_res != None:
                                        dest_id = collection_res.file_id
                                    else:
                                        # 创建电影集
                                        create_res = ali_drive.aligo.create_folder(f'{extract_res[1]}',movies.file_id)
                                        dest_id = create_res.file_id
                                move_res = ali_drive.aligo.move_file(file_id=movie_folder.file_id,to_parent_file_id=dest_id,new_name=new_name)
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
                        # 只保留最大的视频文件
                        max_size = 0
                        collection_file:BaseFile = None # type: ignore
                        dp = []
                        for item in movie_collection_files:
                            if item.type=='file' and item.name.endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')):
                                dp.append(item)
                                if max_size < item.size:
                                    max_size = item.size
                                    collection_file = item
                        if len(dp)>1:
                            dp.remove(collection_file)
                            # 移除其他视频文件
                            for dpi in dp:
                                ali_drive.aligo.move_file_to_trash(dpi.file_id)
                        
                        for movie_collection_file in movie_collection_files:
                            
                            if movie_collection_file.name.lower().endswith(('mkv','mp4','avi','rmvb','wmv','mpeg')):
                                # 只保留最大的视频文件
                                
                                
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
                                                    logger.info(f'电影集: {extract_result[1]}不存在,直接创建')
                                                    # movies下面没有这个电影集 直接创建新的影集
                                                    create_res = ali_drive.aligo.create_folder(f'{extract_result[1]}',movies.file_id)
                                                    movie_collection_id = create_res.file_id
                                                else:
                                                    logger.info(f'已存在电影集: {find_res.name}')
                                                    movie_collection_id = find_res.file_id
                                            else:
                                                # 当前电影文件夹不属于任何电影集 直接移动到movies下
                                                logger.warning(f'当前电影集文件夹不属于任何影集,已移动至movies中')
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
                
# 解析电影和电影集名字
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


# 刮削剧集
def crawl_shows(ali_drive:Alidrive):
    # !强制的规范元数据结构
    
    # 剧季文件夹：Season1 / Season 1 / s1 / S1 / S01 /s01
    # 媒体源文件：SxxExx (.mkv / .mp4 等常见视频格式)
    # 剧集元数据：SxxExx.nfo / SxxEPxx.nfo
    # 外置字幕源：SxxExx.zh (.ass / .ssa / .srt)
    # 剧集缩略图：SxxExx-thumb (.jpg / .png)
    # 剧季元数据：season.nfo
    
    # 要刮削的根文件夹
    tmm_tvshows:BaseFile = ali_drive.get_folder_by_path('tmm/tmm-tvshows')  # type: ignore
    # 刮削好的文件夹
    tvshows:BaseFile = ali_drive.get_folder_by_path('TvShows') # type: ignore
    # 获取所有剧集文件合集
    show_folders = ali_drive.get_file_list(tmm_tvshows.file_id)
    
    # 遍历剧集文件夹合集
    for show_folder in show_folders:
        seasons = ali_drive.get_file_list(show_folder.file_id)
        # 如果剧集文件夹下面直接有mkv文件(单季剧集) 将mkv文件移动到Season1中
        videos = list(filter(lambda x:(x.type=='file') and (x.file_extension in (('mkv','mp4','avi','rmvb','wmv','mpeg'))),seasons))
        if len(videos)!=0:
            # 创建Season1文件夹
            create_res = ali_drive.aligo.create_folder('Season1',show_folder.file_id,check_name_mode='refuse')
            # 将所有文件移动到Season1
            ali_drive.aligo.batch_move_files(list(map(lambda x:x.file_id,seasons)),create_res.file_id)
            seasons.clear()
            seasons.append(ali_drive.get_file(create_res.file_id))
        
        # 判断是否需要刮削 有nfo文件的不需要
        if len(list(filter(lambda x:x.name=='tvshow.nfo',seasons))) != 0:
            logger.info(f'剧集: {show_folder.name}无需刮削,跳过')
            continue
        
        
        # show_folder.name非常重要! 刮削剧集主海报图片和横幅主要靠这个剧集根文件夹 标准格式(TMDB): 剧集名称 (年份)   如 雷神3：诸神黄昏 (2017) , 教父 (1972) 
        
        # 在./kodi-tmdb/shows创建剧集目录  让守护进程kodi-tmdb刮削
        os.system(f'mkdir -p ./kodi-tmdb/shows/"{show_folder.name}"')
        # 将fanart.jpg poster.jpg tvshow.nfo 上传到show_folder中
        sleep(3)
        try:
            ali_drive.aligo.upload_file(f'kodi-tmdb/shows/{show_folder.name}/fanart.jpg',show_folder.file_id,check_name_mode='refuse')
            ali_drive.aligo.upload_file(f'kodi-tmdb/shows/{show_folder.name}/poster.jpg',show_folder.file_id,check_name_mode='refuse')
            ali_drive.aligo.upload_file(f'kodi-tmdb/shows/{show_folder.name}/tvshow.nfo',show_folder.file_id,check_name_mode='refuse')
            logger.info(f'剧集: {show_folder.name}同人画,海报,nfo抓取成功')
            
            # 修改剧集文件夹名  根据tv.json生成季海报图
            with open(f'kodi-tmdb/shows/{show_folder.name}/tmdb/tv.json') as shows_f:
                shows_data = json.load(shows_f)
                ali_drive.aligo.rename_file(show_folder.file_id,f'{shows_data["name"]} ({shows_data["first_air_date"].split("-")[0]})',check_name_mode='refuse')
                seasons_json_data:list = shows_data['seasons']
                for seasons_json_data_item in seasons_json_data:
                    s_index = seasons_json_data_item['season_number']
                    # 生成季海报图片
                    with open(f'kodi-tmdb/shows/{show_folder.name}/season{str(s_index).zfill(2)}-poster.jpg','wb') as sjdi:
                        img_res = requests.get(f'{SEASON_BASE_URL}{seasons_json_data_item["poster_path"]}')
                        sjdi.write(img_res.content)
            
        except Exception as e:
            logger.error(f'剧集信息刮削失败: {e},请检查剧集名称!')
            continue
        
        for season in seasons:
            if not season.type == 'folder':
                continue
            # 提取第几季
            which_season = extract_season(season.name)
            if which_season == -1:
                continue
            
            # 上传季图片
            try:
                ali_drive.aligo.upload_file(f'kodi-tmdb/shows/{show_folder.name}/season{str(which_season).zfill(2)}-poster.jpg',show_folder.file_id,check_name_mode='refuse')
            except:
                continue
            episodes = ali_drive.get_file_list(season.file_id)
            # 保证剧集是能排序的 不用重命名
            episode_videos = []
            # 对字幕重命名 从季文件夹开始寻找字幕文件
            episode_folders = []
            
            subtitles = []
            for episode in episodes: 
                if episode.type == 'file'  and episode.file_extension in ['mkv','mp4','avi','rmvb','wmv','mpeg']: 
                    episode_videos.append(episode)
                elif episode.type == 'file' and episode.file_extension in ['ass','srt','smi','ssa','sub']:
                    subtitles.append(episode)
                elif episode.type == 'folder' and episode.name!= '.actors':
                    episode_folders.append(episode)
                    
            if len(episode_videos)==0:
                # 没有视频文件停止这一季的刮削
                continue
            # 对视频文件排序
            episode_videos.sort(key=lambda x: x.name,reverse=False)
            
            # 重命名视频文件
            for index_,episode_video in enumerate(episode_videos):
                episode_video.name = f'S{str(which_season).zfill(2)}E{str(index_+1).zfill(2)}'
                ali_drive.aligo.rename_file(episode_video.file_id,f'S{str(which_season).zfill(2)}E{str(index_+1).zfill(2)}',check_name_mode=False)
            
            if len(subtitles) >= len(episode_videos):
                # 季文件夹下已有字幕文件且数量和视频文件一致
                # 对字幕文件排序
                subtitles.sort(key=lambda x: x.name,reverse=False)
                # 取前几个字幕
                subtitles = subtitles[:len(episode_videos)]
                
                # 重命名字幕文件
                for index,subtitle in enumerate(subtitles):
                    # 获取当前扩展名
                    subtitle_extension = subtitle.file_extension
                    new_sub_title = f'{episode_videos[index].name.rsplit(".",1)[0]}.{subtitle_extension}'
                    # 判断是否需要重命名
                    if new_sub_title == subtitle.name:
                        # 如果是已处理好的字幕文件无需调用重命名接口
                        break
                    # 重命名
                    ali_drive.rename(subtitle.file_id,new_sub_title)
            else:
                # 从剩下的文件夹寻找字幕文件 如果扩展名正确+数量正确就移动到季目录
                
                for episode_folder in episode_folders:
                    folder_file_list = ali_drive.get_file_list(episode_folder.file_id)
                    # 当前文件夹的字幕文件
                    subtitles = list(filter(lambda x: (x!=None) and (x.type == 'file') and (x.file_extension in ['ass','srt','smi','ssa','sub']) ,folder_file_list))
                    if len(subtitles)==0:
                        continue
                    else:
                        subtitle_parent_folder_id = subtitles[0].parent_file_id
                    # 对字幕文件排序
                    subtitles.sort(key=lambda x: x.name,reverse=False)
                    if len(subtitles) >= len(episode_videos):
                        # 季文件夹下已有字幕文件且数量和视频文件一致
                        subtitles = subtitles[:len(episode_videos)]
                        # 重命名字幕文件
                        for index,subtitle in enumerate(subtitles):
                            # 获取当前扩展名
                            subtitle_extension = subtitle.file_extension
                            new_sub_title = f'{episode_videos[index].name.rsplit(".",1)[0]}.{subtitle_extension}'
                            # 判断是否需要重命名
                            if new_sub_title == subtitle.name:
                                # 如果是已处理好的字幕文件无需调用重命名接口
                                break
                            # 移动并重命名
                            ali_drive.move(file_id=subtitle.file_id,to_parent_file_id=episode_videos[index].parent_file_id,new_name=new_sub_title)
                        # 一旦有合适的字幕文件 处理完就停止处理 并删除字幕文件父文件夹
                        ali_drive.move_to_trash(subtitle_parent_folder_id)
                        break
            
            # 在./kodi-tmdb/shows创建名称为{which_episode}的空视频文件
            for index,episode_video in enumerate(episode_videos):
                os.system(f'touch ./kodi-tmdb/shows/"{show_folder.name}"/S{str(which_season).zfill(2)}E{str(index+1).zfill(2)}.mkv')
                # 休眠3s等待kodi-tmdb进程刮削完成
                sleep(3)
                # 将生成单集的缩略图和nfo文件上传到剧集文件夹  缩略图: SXXEXX-thumb.jpg  nfo: SXXEXX.nfo
                try:
                    ali_drive.aligo.upload_file(f'kodi-tmdb/shows/{show_folder.name}/S{str(which_season).zfill(2)}E{str(index+1).zfill(2)}-thumb.jpg',season.file_id)
                    ali_drive.aligo.upload_file(f'kodi-tmdb/shows/{show_folder.name}/S{str(which_season).zfill(2)}E{str(index+1).zfill(2)}.nfo',season.file_id)
                except:
                    continue
        
        # 移动整个剧集文件夹
        try:
            res = ali_drive.aligo.move_file(show_folder.file_id,tvshows.file_id)
            shows_id = res.file_id
        except:
            logger.info(f'剧集:  {show_folder.name}已存在,无需新增')
            continue
    
def extract_season(season_name:str):
    """提取季信息

    Args:
        season_name (str): 季名

    Returns:
        _type_: _description_
    """    
    # 获取季
    re_result = re.search(SEASON_PATTERN,season_name)
    if re_result:
        season_info = re_result.group()
        # 提取数字
        search = re.search(r'(\d+)|(一|二|三|四|五|六|七|八|九|十)',season_info)
        if search:
            season_tag = search.group()
            if season_tag in ('一','二','三','四','五','六','七','八','九','十'):
                return int(SEASON_DICT[season_tag])
            else:
                return int(season_tag)    
    return -1

if __name__=='__main__':
    try:
        # Aligo的配置文件aligo.json的base64字符串
        base64_userdata = sys.argv[1]
        QQ_SMTP_PASSWORD = sys.argv[2]
        aligo = prepare_for_aligo(base64_userdata,QQ_SMTP_PASSWORD)
    except:
        # 本地环境直接扫码
        aligo = Aligo()
        
    crawling(aligo)
    
    # 随机生成一个文件 保持仓库处于活跃
    open('dist-version','w+').write(time.strftime("%Y-%m-%d",time.localtime(time.time()))+'-'+''.join(random.sample('abcdefghigklmnopqrstuvwxyz1234567890',20)))
