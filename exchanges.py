import hmac
import hashlib
import time
import aiohttp
from datetime import datetime, timedelta

# --- API 설정 (본인의 키를 입력하세요) ---
BINGX_ACC1_KEY    = "YAXc8PKbKMHafqyl353ViY2XLBZGEIDyz883bxvHegR6nc5Vfvf2Wye5QqGtC4DnEZAnZH98S1y9TByk0Tsg"
BINGX_ACC1_SECRET = "IDvLrNomyhrJspNnMBiJT4T7INJCXJ7cS7Ej39m0oipjDaHsoQEGrJq2C08F1UnN1WBUInIW4WDPC1zawwspA"

BINGX_ACC2_KEY    = "3NZaUYyrIMiO0RcKk4m5lyq83HFQnUrLnd381uKhDfN0jfp2TOvdQfVEuk5Ge5zECVsrsKxm6AZ11Azw"
BINGX_ACC2_SECRET = "qsQ2hDBahCrFBuvZr7BxlUm7ja7uYijdunvZxG7zXGIQM7aiEApzK41A8mVahKqUc3NIKTXaZQypWMg43g"

def bingx_sign(params, secret):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

async def get_bingx_data(session, api_key, secret, days):
    url = "https://open-api.bingx.com/openApi/swap/v2/user/getClosedProfit"
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    params = {"timestamp": int(time.time() * 1000), "startTime": start_time, "limit": 100}
    params["signature"] = bingx_sign(params, secret)
    headers = {"X-BX-APIKEY": api_key}
    async with session.get(url, params=params, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("data", [])
        return []

async def get_combined_report(days):
    async with aiohttp.ClientSession() as session:
        acc1 = await get_bingx_data(session, BINGX_ACC1_KEY, BINGX_ACC1_SECRET, days)
        acc2 = await get_bingx_data(session, BINGX_ACC2_KEY, BINGX_ACC2_SECRET, days)
        all_trades = acc1 + acc2

        # 지표 계산 로직
        total_trades = len(all_trades)
        if total_trades == 0:
            return f"📊 **최근 {days}일간 거래 내역이 없습니다.**"

        wins = [float(t['closedProfit']) for t in all_trades if float(t['closedProfit']) > 0]
        losses = [float(t['closedProfit']) for t in all_trades if float(t['closedProfit']) <= 0]
        
        total_pnl = sum(wins) + sum(losses)
        win_rate = (len(wins) / total_trades) * 100
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        max_win = max(wins) if wins else 0
        max_loss = min(losses) if losses else 0
        pf = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')

        # 양식 적용 출력
        now_str = datetime.now().strftime('%Y-%m-%d')
        start_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        report = f"📊 **성과 리포트 — 최근 {days}일 ({start_str} ~ {now_str})**\n"
