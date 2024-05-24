# 阿里云盘自动签到
import base64
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import qrcode
from aligo import Aligo
from loguru import logger
from telebot import TeleBot

from aliyundrive import aliyundriveAutoCheckin

bot = TeleBot(token=os.environ['TG_TOKEN'])


def show_qrcode(qr_link: str):
	# 将qr_link生成二维码
	logger.info('正在生成二维码')
	qr_img = qrcode.make(qr_link)
	qr_img.get_image()
	qr_img_path = tempfile.mktemp()
	qr_img.save(qr_img_path)
	qr_data = open(qr_img_path, 'rb').read()
	logger.info('二维码生成成功')
	bot.send_photo(chat_id=os.environ['TG_CHAT_ID'],
	               photo=qr_data, caption='请扫码登录阿里云盘')


def format_date():
	"""获取今天的字符串格式化日期 格式为: 2021-09-01

	Args:
		date (datetime.date): 日期

	Returns:
		[str]: 格式化后的日期
	"""
	return datetime.date.today().strftime('%Y-%m-%d')


def days_between(old_date: str):
	"""计算字符串日期与今天的天数差 格式为: 2021-09-01

	Args:
		old_date (str): _description_
	"""
	old_date = time.strptime(old_date, '%Y-%m-%d')
	old_date = time.mktime(old_date)
	now = time.time()
	days = (now - old_date) / (24 * 60 * 60)
	return days


def sign_in(refresh_token: str, bot: TeleBot):
	tg_content = ""
	
	if refresh_token != "":
		logger.info('阿里云盘自动签到开始')
		response_data = aliyundriveAutoCheckin.get_token(refresh_token.strip())
		if isinstance(response_data, str):
			tg_content += response_data
		
		access_token = response_data.get('access_token')
		user_name = response_data.get("user_name")
		
		if access_token is None:
			tg_content += f"令牌错误: 请检查您的令牌值。\n"
		
		response_data = aliyundriveAutoCheckin.sign_in(access_token)
		if isinstance(response_data, str):
			tg_content += response_data
		
		logger.info(f'签到成功结果: {response_data}')
		# signin_count = response_data['result']['signInCount']
		# tg_content += f"账号: {user_name} - 成功签到, 本月累计签到: {signin_count}天\n"
		
		response_data = aliyundriveAutoCheckin.get_reward(
			access_token, signin_count)
		if isinstance(response_data, str):
			tg_content += response_data
		
		logger.info(f'签到奖励结果: {response_data}')
		# tg_content += f"本次签到的奖励: {response_data['result']['name']}, {response_data['result']['description']}\n"
		
		# bot.send_message(chat_id=os.environ['TG_CHAT_ID'], text=tg_content)
		logger.info('阿里云盘自动签到成功!')


# 准备aligo需要的配置文件
def prepare_for_aligo(base64_userdata: str):
	subprocess.call('mkdir -p /home/runner/.aligo', shell=True)
	aligo_config_folder = Path.home().joinpath('.aligo') / 'aligo.json'
	try:
		aligo_config_str = base64.b64decode(
			base64_userdata).decode(encoding='utf-8')
		aligo_config: dict = json.loads(aligo_config_str)
		refresh_token = aligo_config['refresh_token']
		aligo = Aligo(refresh_token=refresh_token, re_login=False)
		# 更新session的x-device-id
		aligo_config = json.loads(
			aligo_config_folder.read_text(encoding='utf8'))
		device_id = aligo_config['device_id']
		x_device_id = aligo_config['x_device_id']
		aligo._auth.token.device_id = device_id
		aligo._auth.token.x_device_id = x_device_id
		aligo._session.headers.update({'x-device-id': x_device_id, 'x-signature': aligo._auth._X_SIGNATURE})
		# 将配置信息base64编码更新到github的secrets中
		aligo_config_str = json.dumps(aligo_config)
		aligo_config_code = base64.b64encode(aligo_config_str.encode(
			encoding='utf-8')).decode(encoding='utf-8')
		# 执行linux命令
		os.system(f'echo "aligo_token={aligo_config_code}" >> "$GITHUB_OUTPUT"')
		
		sign_in(refresh_token, bot)
		return aligo
	except Exception as e:
		#  登录失败:string indices must be integers, not 'str',重新通过扫码登录
		logger.info(f'登录失败:{e},重新通过扫码登录')
		# 登录失败 重新通过扫码登录
		if aligo_config_folder.exists():
			aligo_config_folder.unlink()
		aligo = Aligo(show=show_qrcode)
		bot.send_message(chat_id=os.environ['TG_CHAT_ID'], text='阿里云盘登录成功!')
		aligo_config = json.loads(
			aligo_config_folder.read_text(encoding='utf8'))
		aligo_config['last_updated'] = format_date()
		device_id = aligo_config['device_id']
		x_device_id = aligo_config['x_device_id']
		# 更新session的x-device-id
		aligo._session.headers.update({'x-device-id': x_device_id, 'x-signature': aligo._auth._X_SIGNATURE})
		aligo._auth.token.device_id = device_id
		aligo._auth.token.x_device_id = x_device_id
		# 将配置信息base64编码更新到github的secrets中
		aligo_config_str = json.dumps(aligo_config)
		aligo_config_code = base64.b64encode(aligo_config_str.encode(
			encoding='utf-8')).decode(encoding='utf-8')
		# 执行linux命令
		os.system(f'echo "aligo_token={aligo_config_code}" >> "$GITHUB_OUTPUT"')
		# 签到
		refresh_token = aligo_config['refresh_token']
		sign_in(refresh_token, bot)
		return aligo


if __name__ == '__main__':
	try:
		# Aligo的配置文件aligo.json的base64字符串
		base64_userdata = sys.argv[1]
		aligo = prepare_for_aligo(base64_userdata)
	except:
		# 本地环境直接扫码
		logger.info(f'本地环境直接扫码')
		aligo = Aligo()
