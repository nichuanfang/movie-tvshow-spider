# 通过ffmpeg处理音轨对调

# 通过环境变量确定哪些路径的文件需要音轨对调
import os
import re
import subprocess
import sys
from aligo import Aligo,EMailConfig
import time
import base64
import json
from aliyundrive.ali_drive import Alidrive
from loguru import logger
from pathlib import Path

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
    logger.info(f'距离上次登录已过去{days}天')
    if days >= 29:
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


def  handle_shows_audio_sub_track(ali_drive:Alidrive):
    # 获取阿里云盘tmm/shows_video_audio_subtitle下的所有文件夹
    shows_video_audio_subtitle_folder = ali_drive.get_folder_by_path(path='tmm/shows_video_audio_subtitle',create_folder=True)
    shows_video_audio_subtitles = ali_drive.get_file_list(parent_file_id=shows_video_audio_subtitle_folder.file_id)
    for shows_video_audio_subtitle in shows_video_audio_subtitles:
        if shows_video_audio_subtitle.type == 'folder':
            # 获取文件夹名称
            shows_video_audio_subtitle_name = shows_video_audio_subtitle.name
            # 提取剧集名称
            show_name = shows_video_audio_subtitle_name.split('_')[0]
            # 提取第几个视频轨道
            video_channel_num = shows_video_audio_subtitle_name.split('_')[1]
            # 提取第几个音频轨道
            audio_channel_num = shows_video_audio_subtitle_name.split('_')[2]
            # 提取第几个字幕轨道
            sub_channel_num = shows_video_audio_subtitle_name.split('_')[3]
            
            # 获取剧集文件夹
            show_folder = ali_drive.get_folder_by_path(path=f'TvShows/{show_name}',create_folder=True)
            file_list = ali_drive.get_file_list(parent_file_id=show_folder.file_id)
            for file in file_list:
                # 获取季文件夹
                if file.type == 'folder' and extract_season(file.name) != -1:
                    season_folder = file
                    # 获取季文件夹下的所有文件
                    season_file_list = ali_drive.get_file_list(parent_file_id=season_folder.file_id)
                    for season_file in season_file_list:
                        if season_file.type == 'file' and season_file.name.endswith(('mkv','mp4','avi','rmvb','wmv','mpeg','ts')):
                            # 下载视频文件
                            # 统计下载耗时
                            start_time = time.time()
                            logger.info('开始下载视频文件')
                            ali_drive.aligo.download_file(file_id=season_file.file_id,local_folder=f'./downloads/{show_name}/{season_folder.name}')
                            logger.info('视频文件下载完成')
                            end_time = time.time()
                            logger.info(f'下载视频文件耗时{(end_time-start_time)/60}分钟')
                            # 只下载第一个文件
                            break
                        
                            # 视频轨道+音轨+字幕轨道 才是完整的轨道 0:0保留动画 0:2 保留第二个音频轨道 0:3保留第一个字幕
                            
                            # 设置默认音轨与字幕轨道
                            # ffmpeg -i S01E01.mkv -map 0:0 -map 0:2  -map 0:3  -disposition:a:0 default -disposition:a:1 none -c copy -y output.mkv
 
 
                
                    pass
            
            pass
        pass



# 通过ffmpeg获取视频轨道数目
def get_video_channel_num(file_path):
    cmd = 'ffprobe -i {} -show_streams -select_streams v -loglevel quiet'.format(file_path)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = result.stdout.decode('utf-8')
    result = result.split('\n')
    
    count = 0
    for line in result:
        if 'codec_name' in line:
            count+=1
    return count


# 通过ffmpeg获取音频轨道数目
def get_audio_channel_num(file_path):
    cmd = 'ffprobe -i {} -show_streams -select_streams a -loglevel quiet'.format(file_path)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = result.stdout.decode('utf-8')
    result = result.split('\n')
    for line in result:
        if 'channels' in line:
            return int(line.split('=')[-1])
    return 0

# 通过ffmpeg获取字幕轨道数目
def get_subtitle_channel_num(file_path):
    cmd = 'ffprobe -i {} -show_streams -select_streams s -loglevel quiet'.format(file_path)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = result.stdout.decode('utf-8')
    result = result.split('\n')
    count = 0
    for line in result:
        if 'TAG:language' in line:
            count+=1
    return count


if __name__=='__main__':
    try:
        # Aligo的配置文件aligo.json的base64字符串
        base64_userdata = sys.argv[1]
        QQ_SMTP_PASSWORD = sys.argv[2]
        aligo = prepare_for_aligo(base64_userdata,QQ_SMTP_PASSWORD)
    except:
        # 本地环境直接扫码
        aligo = Aligo()
    ali_drive = Alidrive(aligo)
    handle_shows_audio_sub_track(ali_drive)
