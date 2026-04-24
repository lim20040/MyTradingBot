import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta, timezone

# --- [필독] OKX API 설정 (본인의 키로 반드시 수정하세요) ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "Lim1004!"

# 사용자 기준 시점 (2026-04-23 00:00 KST)
APP_START_DATE = datetime(2026, 4, 23, 0, 0, 0, tzinfo=timezone(timedelta(hours=9)))

def okx_sign(timestamp, method, request_path, secret):
    message = timestamp + method + request_path
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

async def get_combined_report(period_type, current_seed):
    method = "GET"
    request_path = "/api/v5/account/positions-history?instType=SWAP&limit=100"
    
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    
    # --- 기간 설정 로직 ---
    if period_type == 'today':
        start_dt = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_type == '2days':
        start_dt = (now_kst - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_type == 'week':
        start_dt = (now_kst - timedelta(days=now_kst.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_type == 'month':
        start_dt = now_kst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period_type == 'year':
        start_dt = now_kst.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_dt = APP_START_DATE

    # [핵심] 어제(04-23) 이전 데이터는 필터링
    actual_start_dt = max(start_dt, APP_START_DATE)
    start_ts = int(actual_start_dt.timestamp() * 1000)
    end_ts = int((now_kst + timedelta(hours=1)).timestamp() * 1000)

    # API 요청 준비
    now_utc = datetime.now(timezone.utc)
    timestamp_okx = now_utc.isoformat()[:-9] + "Z"
    
    headers = {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": okx_sign(timestamp_okx, method, request_path, OKX_API_SECRET),
        "OK-ACCESS-TIMESTAMP": timestamp_okx,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        url = f"https://www.okx.com{request_path}"
        async with session.get(url, headers=headers) as response:
            res = await response.json()
            if res.get("code") != "0":
                return f"❌ OKX 에러: {res.get('msg')}"
                
            data = res.get("data", [])
            total_pnl, wins, losses = 0.0, [], []

            for item in data:
                # uTime이나 cTime 중 큰 값을 정산 시간으로 사용
                item_time = max(int(item.get('uTime') or 0), int(item.get('cTime') or 0))
                if start_ts <= item_time <= end_ts:
                    pnl = float(item.get('realizedPnl') or 0.0)
                    total_pnl += pnl
                    if pnl > 0: wins.append(pnl)
                    elif pnl < 0: losses.append(pnl)

            trades_count = len(wins) + len(losses)
            if trades_count == 0:
                return f"📊 {actual_start_dt.strftime('%Y-%m-%d')} 이후 내역이 없습니다."

            # 지표 계산
            win_rate = (len(wins) / trades_count * 100) if trades_count > 0 else 0
            avg_win = sum(wins)/len(wins) if wins else 0.0
            avg_loss = sum(losses)/len(losses) if losses else 0.0
            max_win = max(wins) if wins else 0.0
            max_loss = min(losses) if losses else 0.0

            # 리포트 구성
            report = f"📊 **성과 리포트 (KST)**\n"
            report += f"📅 {actual_start_dt.strftime('%Y-%m-%d')} ~ 현재\n"
            report += "━━━━━━━━━━━━━━━━━━\n\n"
            report += f"1️⃣ **총 거래:** {trades_count}건 (승 {len(wins)} / 패 {len(losses)})\n"
            report += f"2️⃣ **승률:** {win_rate:.1f}%\n"
            report += f"3️⃣ **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.2f} USDT\n"
            report += f"4️⃣ **평균 익/손:** {avg_win:+.2f} / {avg_loss:.2f} USDT\n"
            report += f"5️⃣ **최대 익/손:** {max_win:+.2f} / {max_loss:.2f} USDT"
            
            return report
