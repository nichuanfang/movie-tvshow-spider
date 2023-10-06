import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

def get_user_input():
    # 如果文件不存在，则询问用户输入
    if not os.path.exists('user_data.json'):
        refresh_tokens = input("请输入您的刷新令牌，多个令牌用逗号分隔: ").split(',')
        is_get_reward = input("是否要获取奖励? (输入 'y' 或 'n'): ").lower() == 'y'
        is_send_email = input("是否要发送邮件? (输入 'y' 或 'n'): ").lower() == 'y'
        is_custom_email = input("是否要使用自定义电子邮件? (输入 'y' 或 'n'): ").lower() == 'y'
        to_addr = input("请输入要发送到的电子邮件地址: ")

        # 将用户输入保存到文件中以供将来使用
        with open('user_data.json', 'w') as f:
            json.dump({
                'refresh_tokens': refresh_tokens,
                'is_get_reward': is_get_reward,
                'is_send_email': is_send_email,
                'is_custom_email': is_custom_email,
                'to_addr': to_addr
            }, f)

    # 如果文件存在，从中加载数据
    else:
        with open('user_data.json', 'r') as f:
            data = json.load(f)
        refresh_tokens = data['refresh_tokens']
        is_get_reward = data['is_get_reward']
        is_send_email = data['is_send_email']
        is_custom_email = data['is_custom_email']
        to_addr = data['to_addr']

    return refresh_tokens, is_get_reward, is_send_email, is_custom_email, to_addr

def get_token(refresh_token):
    try:
        response = requests.post(
            "https://auth.aliyundrive.com/v2/account/token",
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        return f"HTTP错误: {e.response.status_code}"
    except requests.RequestException as e:
        return f"请求错误: {str(e)}"

def sign_in(access_token):
    headers = {'Authorization': 'Bearer ' + access_token}
    try:
        response = requests.post(
            "https://member.aliyundrive.com/v1/activity/sign_in_list",
            json={"_rx-s": "mobile"},
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        return f"HTTP错误: {e.response.status_code}"
    except requests.RequestException as e:
        return f"请求错误: {str(e)}"

def get_reward(access_token, signin_count):
    headers = {'Authorization': 'Bearer ' + access_token}
    try:
        response = requests.post(
            "https://member.aliyundrive.com/v1/activity/sign_in_reward?_rx-s=mobile",
            json={"signInDay": signin_count},
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        return f"HTTP错误: {e.response.status_code}"
    except requests.RequestException as e:
        return f"请求错误: {str(e)}"

def send_email(smtp_server, smtp_port, smtp_user, smtp_password, to_addr, email_content):
    subject = "阿里云盘签到通知"
    additional_content = """
    This project is built by xiaohan17.
    Feedback methods:
    1. TG群组:https://t.me/ikun9882
    2. TG联系人:https://t.me/xiaohan17s
    3. Github:https://github.com/zzh0107/aliyundriveAutoCheckin
    """
    full_email_content = email_content + additional_content

    msg = MIMEText(full_email_content)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_addr

    try:
        server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_addr], msg.as_string())
        server.quit()
    except smtplib.SMTPException as e:
        print(f"SMTP错误: {str(e)}")

def main():
    refresh_tokens, is_get_reward, is_send_email, is_custom_email, to_addr = get_user_input()
    email_content = ""

    for refresh_token in refresh_tokens:
        if refresh_token != "":
            response_data = get_token(refresh_token.strip())
            if isinstance(response_data, str):
                email_content += response_data
                continue

            access_token = response_data.get('access_token')
            user_name = response_data.get("user_name")

            if access_token is None:
                email_content += f"令牌错误: 请检查您的令牌值。\n"
                continue

            response_data = sign_in(access_token)
            if isinstance(response_data, str):
                email_content += response_data
                continue

            signin_count = response_data['result']['signInCount']
            email_content += f"账号: {user_name} - 成功签到, 本月累计签到: {signin_count}天\n"

            if is_get_reward:
                response_data = get_reward(access_token, signin_count)
                if isinstance(response_data, str):
                    email_content += response_data
                    continue

                email_content += f"本次签到的奖励: {response_data['result']['name']}, {response_data['result']['description']}\n"

    if is_send_email:
        if is_custom_email:
            smtp_server = input("请输入SMTP服务器: ")
            smtp_port = input("请输入SMTP端口: ")
            smtp_user = input("请输入SMTP用户: ")
            smtp_password = input("请输入SMTP密码: ")
        else:
            smtp_server, smtp_port, smtp_user, smtp_password = "smtp.qq.com", 465, "2799153122@qq.com", "fctchwjhkdjvdgie"

        send_email(smtp_server, smtp_port, smtp_user, smtp_password, to_addr, email_content)

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('output.txt', 'a', encoding='utf-8') as f:
        f.write(f'{current_time}\n{email_content}\n')

    print("结果可以在 'output.txt' 文件或您的电子邮件中查看。")
    input("按回车键退出...")

if __name__ == "__main__":
    main()
