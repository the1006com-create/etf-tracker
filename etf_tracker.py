import requests
import pandas as pd
import json
import os
import smtplib
import time
from email.mime.text import MIMEText
from datetime import datetime

ETF_LIST = ['00981A', '00982A', '00987A', '00992A', '00980A', '00991A']

DATA_FILE = 'holdings.json'
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASS = os.environ.get('GMAIL_PASS')
NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL')

def fetch_holdings(etf_code):
    try:
        url = f'https://openapi.twse.com.tw/v1/ETF/etfPortfolio?stockNo={etf_code}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        stocks = []
        for item in data:
            code = item.get('component_security_code', '').strip()
            if code and len(code) == 4 and code.isdigit():
                stocks.append(code)
        print(f'{etf_code}: 抓到 {len(stocks)} 檔')
        return list(set(stocks))
    except Exception as e:
        print(f'{etf_code} 抓取失敗: {e}')
        return []

def load_yesterday():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_today(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def send_email(subject, body):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = NOTIFY_EMAIL
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

def main():
    yesterday = load_yesterday()
    today = {}
    all_new = []

    for etf_code in ETF_LIST:
        print(f'正在抓取 {etf_code}...')
        stocks = fetch_holdings(etf_code)
        today[etf_code] = stocks
        old = set(yesterday.get(etf_code, []))
        new = set(stocks) - old
        if old:
            for s in new:
                all_new.append({'ETF': etf_code, '新增股票': s})
        time.sleep(1)

    save_today(today)

    if all_new:
        df = pd.DataFrame(all_new)
        consensus = df.groupby('新增股票').count()
        consensus = consensus[consensus['ETF'] >= 2]

        body = f'【ETF成分股異動偵測】{datetime.now().strftime("%Y-%m-%d")}\n\n'
        body += '=== 所有新增持股 ===\n'
        body += df.to_string(index=False)
        if not consensus.empty:
            body += '\n\n=== ⚠️ 多家同步新增訊號 ===\n'
            body += consensus.to_string()

        send_email('🔔 ETF新增持股偵測通知', body)
        print('已發送通知信！')
    else:
        print('今日無異動')

if __name__ == '__main__':
    main()
