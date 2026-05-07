import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

ETF_LIST = {
    '00981A': 'https://www.sitca.org.tw/ROC/Industry/IN2421.aspx?pid=00981A',
    '00982A': 'https://www.sitca.org.tw/ROC/Industry/IN2421.aspx?pid=00982A',
    '00987A': 'https://www.sitca.org.tw/ROC/Industry/IN2421.aspx?pid=00987A',
    '00992A': 'https://www.sitca.org.tw/ROC/Industry/IN2421.aspx?pid=00992A',
    '00980A': 'https://www.sitca.org.tw/ROC/Industry/IN2421.aspx?pid=00980A',
    '00991A': 'https://www.sitca.org.tw/ROC/Industry/IN2421.aspx?pid=00991A',
}

DATA_FILE = 'holdings.json'

GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASS = os.environ.get('GMAIL_PASS')
NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL')

def fetch_holdings(etf_code, url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        tables = soup.find_all('table')
        stocks = []
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if cols and len(cols) >= 2:
                    code = cols[0].text.strip()
                    if code.isdigit() and len(code) == 4:
                        stocks.append(code)
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

    for etf_code, url in ETF_LIST.items():
        print(f'正在抓取 {etf_code}...')
        stocks = fetch_holdings(etf_code, url)
        today[etf_code] = stocks
        old = set(yesterday.get(etf_code, []))
        new = set(stocks) - old
        for s in new:
            all_new.append({'ETF': etf_code, '新增股票': s})

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
