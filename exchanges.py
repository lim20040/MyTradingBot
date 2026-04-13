import hmac
import hashlib
import time
import aiohttp
from datetime import datetime, timedelta

# --- API 설정 ---
BINGX_ACC1_KEY    = "YAXc8PKbKMHafqyl353ViY2XLBZGEIDyz883bxvHegR6nc5Vfvf2Wye5QqGtC4DnEZAnZH98S1y9TByk0Tsg"
BINGX_ACC1_SECRET = "IDvLrNomyhrJspNnMBiJT4T7INJCXJ7cS7Ej39m0oipjDaHsoQEGrJq2C08F1UnN1WBUInIW4WDPC1zawwspA"

BINGX_ACC2_KEY    = "3NZaUYyrIMiO0RcKk4m5lyq83HFQnUrLnd381uKhDfN0jfp2TOvdQfVEuk5Ge5zECVsrsKxm6AZ11Azw"
BINGX_ACC2_SECRET = "qsQ2hDBahCrFBuvZr7BxlUm7ja7uYijdunvZxG7zXGIQM7aiEApzK41A8mVahKqUc3NIKTXaZQypWMg43g"

def bingx_sign(params, secret):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

async def get_bingx_trades(session, api_key, secret, days):
    # 무기한 선물(Perp)의 실제 체결 내역(User Trade History) 경로
    url = "https://open-api.bingx.com/openApi/swap/v2/user/tradeHistory"
    
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    params = {
        "timestamp": int(time.time() * 1000),
        "startTime": start_time,
        "limit": 500  # 최대한 많이 긁어옵니다.
    }
    params["signature"] = bingx_sign(params, secret)
    headers = {"X-BX-APIKEY": api_key}
    
    async with session.get(url, params=params, headers=headers) as response:
        res_json = await response.json()
        if res_json.get("code") == 0:
            return res_json.get("data", [])
        return []

async def get_combined_report(days):
    async with aiohttp.ClientSession() as session:
        acc1 = await get_bingx_trades(session, BINGX_ACC1_KEY, BINGX_ACC1_SECRET, days)
        acc2 = await get_bingx_trades(session, BINGX_ACC2_KEY, BINGX_ACC2_SECRET, days)
        all_trades = acc1 + acc2

        # 실제로 손익(realizedPnl)이 발생한 기록만 필터링
        final_trades = []
        for t in all_trades:
            pnl = float(t.get('realizedPnl', 0))
            if pnl != 0: # 0이 아닌 것(수익이나 손실이 확정된 것)만 수집
                final_trades.append(pnl)

        if not final_trades:
            return f"📊 **최근 {days}일간 실제 체결된 손익 내역이 없습니다.**\n(포지션 종료 시 발생하는 실현 손익 기준)"

        wins = [p for p in final_trades if p > 0]
        losses = [p for p in final_trades if p < 0]
        
        total_pnl = sum(final_trades)
        win_rate = (len(wins) / len(final_trades)) * 100 if final_trades else 0
        
        report = f"📊 **성과 리포트 — 최근 {days}일 (실체결 기준)**\n"
        report += "━━━━━━━━━━━━━━━━━━\n"
        report += f"• **총 거래:** {len(final_trades)}건 (승 {len(wins)} / 패 {len(losses)})\n"
        report += f"• **승률:** {win_rate:.1f}%\n"
        report += f"• **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.4f} USDT\n"
        report += f"• **최대 수익:** {max(final_trades):+.4f} USDT\n"
        report += f"• **최대 손실:** {min(final_trades):+.4f} USDT\n"
        
        return report
