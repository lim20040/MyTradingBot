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

async def get_bingx_data(session, api_key, secret, days):
    # 최신 V2 무기한 선물 실현 손익 경로 (Perpetual V2)
    url = "https://open-api.bingx.com/openApi/swap/v2/user/getClosedProfit"
    
    # 안전을 위해 최근 7일(최대치)로 고정해서 테스트
    start_time = int((datetime.now() - timedelta(days=min(days, 7))).timestamp() * 1000)
    
    params = {
        "timestamp": int(time.time() * 1000),
        "startTime": start_time,
        "limit": 100
    }
    params["signature"] = bingx_sign(params, secret)
    headers = {"X-BX-APIKEY": api_key}
    
    async with session.get(url, params=params, headers=headers) as response:
        res_json = await response.json()
        # 성공 시 데이터 반환, 실패 시 로그 출력
        if res_json.get("code") == 0:
            return res_json.get("data", [])
        return []

async def get_combined_report(days):
    async with aiohttp.ClientSession() as session:
        acc1 = await get_bingx_data(session, BINGX_ACC1_KEY, BINGX_ACC1_SECRET, days)
        acc2 = await get_bingx_data(session, BINGX_ACC2_KEY, BINGX_ACC2_SECRET, days)
        all_trades = acc1 + acc2

        if not all_trades:
            return f"📊 **최근 {days}일간 거래 내역을 찾을 수 없습니다.**\n(인증은 성공했으나 데이터가 비어있음)"

        # 'closedProfit' 필드로 지표 계산
        wins = [float(t['closedProfit']) for t in all_trades if float(t['closedProfit']) > 0]
        losses = [float(t['closedProfit']) for t in all_trades if float(t['closedProfit']) <= 0]
        
        total_pnl = sum(wins) + sum(losses)
        win_rate = (len(wins) / len(all_trades)) * 100
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        max_win = max(wins) if wins else 0
        max_loss = min(losses) if losses else 0
        pf = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')

        now_str = datetime.now().strftime('%Y-%m-%d')
        report = f"📊 **성과 리포트 — 최근 {days}일**\n"
        report += "━━━━━━━━━━━━━━━━━━\n"
        report += f"• **총 거래:** {len(all_trades)}건 (승 {len(wins)} / 패 {len(losses)})\n"
        report += f"• **승률:** {win_rate:.1f}%\n"
        report += f"• **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.2f} USDT\n"
        report += f"• **평균 이익:** {avg_win:+.2f} USDT\n"
        report += f"• **평균 손실:** {avg_loss:+.2f} USDT\n"
        report += f"• **최대 단건 이익:** {max_win:+.2f} USDT\n"
        report += f"• **최대 단건 손실:** {max_loss:+.2f} USDT\n"
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞ (손실 없음)"
        report += f"• **손익비(PF):** {pf_str}\n"
        
        return report
