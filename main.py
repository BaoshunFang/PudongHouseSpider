#! /usr/bin/python3.6
from __future__ import unicode_literals
import subprocess
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import json
from interval import Interval

# for estate in blacklist, no need to get details
estate_blacklist = ["千汇路198弄（公元2040）", "航亭环路399弄（东方鸿璟园）", "宣黄公路2585弄（惠南宝业华庭）", 
"秋亭路88弄（朗诗未来树）", "渡桥路78弄（中骏柏景湾）", "周东南路388弄（丰和雅苑）", "永泰路136弄",
"鹤驰路88弄（南馨佳苑）", "鹤永路259弄（瑞雅苑）", "勤政路88弄（华发四季苑）"]
static_totalnum = 0
static_intere_num = 0


def get_house_detail():
    current_intere_num = 0
    houses_detail = {}
    url = 'https://select.pdgzf.com/houseLists'

    option=webdriver.ChromeOptions()
    option.add_argument('headless') # 设置option
    browser = webdriver.Chrome(chrome_options=option)  # 调用带参数的谷歌浏览器
    browser.implicitly_wait(1)
    browser.get(url)
    time.sleep(2)

    houses_num_str = browser.find_element_by_xpath('//*[@id="app"]/div[2]/div/section/h4/span')
    houses_num = int(houses_num_str.text)
    if houses_num == static_totalnum:
        print("No new house, return")
        return houses_detail,current_intere_num
    else:
        print("{num} house added".format(num = houses_num - static_totalnum))
 
    houses_detail["房源总数"] = houses_num
    estate_list = {}
    id = 2 # 1 for "不限", form 2 is the real estate
    while houses_num > 0:
        estate_xpath = '//*[@id="app"]/div[2]/div/section/div[1]/div[2]/div[2]/ul/li[{index}]'.format(index=str(id))
        searchButton = browser.find_element_by_xpath(estate_xpath) #获取搜索按钮
        searchButton.click()
        time.sleep(2)
        house_num = int(browser.find_element_by_xpath('//*[@id="app"]/div[2]/div/section/h4/span').text)
        houses_num -= house_num
        id += 1
        estate_title = "{estate_name}({num})".format(estate_name = searchButton.text, num=str(house_num))
        print(estate_title)
        if searchButton.text in estate_blacklist:
            estate_list[estate_title] = "不感兴趣小区"
        else:
            current_intere_num += house_num
            content = browser.page_source.encode('utf-8')
            soup = BeautifulSoup(content, 'lxml')
            house_list = soup.find_all('h4', class_="c-6 fs26")
            house_detail_list = {}
            for house in house_list:
                house_detail = {}
                for sibling in house.find_next_siblings():
                    details = sibling.find_all('span')
                    house_detail[details[0].string] = details[1].string
                house_detail_list[house.string] = house_detail
            estate_list[estate_title] = house_detail_list

    houses_detail["小区列表"] = estate_list
    browser.quit()
    return houses_detail, current_intere_num


def dict_to_html(dd, level=0):
    """
    Convert dict to html using basic html tags
    """
    text = ''
    for k, v in dd.items():
        text += '<br>' + '&nbsp;'*(4*level) + '<b>%s</b>: %s' % (k, dict_to_html(v, level+1) if isinstance(v, dict) else (json.dumps(house_detail,ensure_ascii=False) if isinstance(v, list) else v))
    return text


def send_mail(house_detail, current_intere_num):
    mail_host = "smtp.163.com"
    mail_pass = "password"  #邮箱登录密码
    sender = "username@163.com"  # 发件人

    receivers = ['fangbaos@163.com']  # 收件人
    today = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    detail_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
    global static_totalnum
    global static_intere_num
    if static_totalnum != house_detail["房源总数"]:
        send_header = "[更新{intere_num}/{num}]".format(intere_num = current_intere_num - static_intere_num, num = house_detail["房源总数"] - static_totalnum) + "公租房信息汇总" + today + " " + detail_time  # 邮件标题
        static_totalnum = house_detail["房源总数"]
    else:
        send_header = "[无更新]" + "公租房信息汇总" + today + " " + detail_time  # 邮件标题
    msg = MIMEMultipart('alternative')
    msg['Subject'] =Header(send_header, 'utf-8') 
    msg['From'] = sender
    msg['To'] = ",".join(receivers)
    html = dict_to_html(house_detail,0)

    # 发送html格式正文
    part = MIMEText(html, "html")
    msg.attach(part)

    try:
        server = smtplib.SMTP_SSL(mail_host, 465)
        server.login(sender, mail_pass)
        server.sendmail(sender, receivers, msg.as_string())
        server.close()
        print('邮件发送成功')
        return True
    except Exception as e:
        print('邮件发送失败', str(e))
        return False


reset_flag = False

if __name__ == '__main__':
    command = 'echo pudong_spider start'
    wait = 30*60
    process = subprocess.Popen(command, shell=True)

    while True:
        # 当前时间
        now_localtime = time.strftime("%H:%M:%S", time.localtime())
        # 当前时间（以时间区间的方式表示）
        now_time = Interval(now_localtime, now_localtime)
        print(now_time)

        # 不在睡觉时间打扰
        working_interval = Interval("08:30:00", "22:50:00")
        # 每天9：30到10：00房源会被重置
        reseting_interval = Interval("09:23:00", "10:23:00")
    
        if now_time in working_interval:
            print("时间允许执行")
            if now_time in reseting_interval:
                print("正在重置房源，不执行")
                reset_flag = True
            else:
                if reset_flag:
                    static_totalnum = 0
                    static_intere_num = 0
                    reset_flag = False
                try:
                    house_detail,current_intere_num = get_house_detail()
                except Exception as e:
                    print('获取房源信息失败', str(e))
                    house_detail = {}
                # if no new house, don't send email
                if house_detail:
                    send_succ = False
                    while not send_succ:
                        send_succ = send_mail(house_detail, current_intere_num)
                        if not send_succ:
                            time.sleep(180)
        else:
            print("sleeping")

        time.sleep(wait)

