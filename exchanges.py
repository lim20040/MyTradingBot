import os
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

# --- 공통 유틸 ---
def bingx_sign(params, secret):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

async def get_bingx_data(session, api_key, secret, days):
    url = "https://open-api.bingx.com/openApi/swap/v2/user/getClosedProfit"
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    params = {
        "timestamp": int(time.time() * 1000),
        "startTime": start_time,
        "limit": 100
    }
    params["signature"] = bingx_sign(params, secret)
    headers = {"X-BX-APIKEY": api_key}
    
    async with session.get(url, params=params, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("data", [])
        return []

# --- 통합 리포트 생성 ---
async def get_combined_report(days):
    async with aiohttp.ClientSession() as session:
        # 두 계정 데이터 동시 호출
        acc1_trades = await get_bingx_data(session, BINGX_ACC1_KEY, BINGX_ACC1_SECRET, days)
        acc2_trades = await get_bingx_data(session, BINGX_ACC2_KEY, BINGX_ACC2_SECRET, days)
        
        # 수익 계산
        pnl1 = sum(float(t.get("closedProfit", 0)) for t in acc1_trades)
        pnl2 = sum(float(t.get("closedProfit", 0)) for t in acc2_trades)
        
        total_pnl = pnl1 + pnl2
        total_count = len(acc1_trades) + len(acc2_trades)
        
        report = f"📊 **최근 {days}일 BingX 통합 리포트**\n\n"
        report += f"💰 **계정 1 수익:** {pnl1:.2f} USDT ({len(acc1_trades)}건)\n"
        report += f"💰 **계정 2 수익:** {pnl2:.2f} USDT ({len(acc2_trades)}건)\n"
        report += "---" * 5 + "\n"
        report += f"🔥 **총 합계:** {total_pnl:.2f} USDT\n"
        report += f"📈 **총 거래:** {total_count}건"
        
        return report
