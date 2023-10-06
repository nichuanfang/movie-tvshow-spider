# 阿里云盘自动签到
import base64
import json
import os
import subprocess
import sys
import time
from aligo import Aligo,EMailConfig
from loguru import logger
from pathlib import Path
from aliyundrive import aliyundriveAutoCheckin

def sign_in(refresh_token:str,QQ_SMTP_PASSWORD:str):
    email_content = ""
    
    if refresh_token != "":
        logger.info('阿里云盘自动签到开始')
        response_data = aliyundriveAutoCheckin.get_token(refresh_token.strip())
        if isinstance(response_data, str):
            email_content += response_data

        access_token = response_data.get('access_token')
        user_name = response_data.get("user_name")

        if access_token is None:
            email_content += f"令牌错误: 请检查您的令牌值。\n"

        response_data = aliyundriveAutoCheckin.sign_in(access_token)
        if isinstance(response_data, str):
            email_content += response_data

        signin_count = response_data['result']['signInCount']
        email_content += f"账号: {user_name} - 成功签到, 本月累计签到: {signin_count}天\n"

        response_data = aliyundriveAutoCheckin.get_reward(access_token, signin_count)
        if isinstance(response_data, str):
            email_content += response_data

        email_content += f"本次签到的奖励: {response_data['result']['name']}, {response_data['result']['description']}\n"

        smtp_server, smtp_port, smtp_user, smtp_password = "smtp.qq.com", 465, "1290274972@qq.com", QQ_SMTP_PASSWORD
        aliyundriveAutoCheckin.send_email(smtp_server, smtp_port, smtp_user, smtp_password, smtp_user, email_content)
        logger.info('阿里云盘自动签到成功')



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
    logger.info(f'距离上次登录已过去{days}天')
    email_config = EMailConfig(
        email='1290274972@qq.com',
        host='smtp.qq.com',
        port=465,
        user='1290274972@qq.com',
        password=QQ_SMTP_PASSWORD,
        )
    if days >= 29:
        # 重新通过扫码登录
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
        
        # 自动签到
        refresh_token = aligo_config['refresh_token']
        sign_in(refresh_token,QQ_SMTP_PASSWORD)
        return aligo
    else:
        try:
            with open(f'/home/runner/.aligo/aligo.json','w+',encoding='utf-8') as aligo_file:
                json.dump(aligo_config,aligo_file)
                # 自动签到
                refresh_token = aligo_config['refresh_token']
                sign_in(refresh_token,QQ_SMTP_PASSWORD)
                return Aligo()
        except:
            return Aligo(email=email_config)

if __name__=='__main__':
    try:
        # Aligo的配置文件aligo.json的base64字符串
        base64_userdata = sys.argv[1]
        QQ_SMTP_PASSWORD = sys.argv[2]
        aligo = prepare_for_aligo(base64_userdata,QQ_SMTP_PASSWORD)
    except:
        # 本地环境直接扫码
        aligo = Aligo()