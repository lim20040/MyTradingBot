import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta, timezone

# --- OKX API 설정 (본인 키로 다시 확인!) ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "Lim1004!"

def okx_sign(timestamp, method, request_path, secret):
    message = timestamp + method + request_path
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

async def get_combined_report(query, current_seed, is_summary=False):
    method = "GET"
    # 최근 100건까지 조회 범위를 늘렸습니다.
    request_path = "/api/v5/account/positions-history?instType=SWAP&limit=100"
    
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    timestamp_okx = now_utc.isoformat()[:-9] + "Z"
    
    # 시간 범위 설정
    try:
        days = int(query)
        start_dt = (now_kst - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now_kst + timedelta(hours=2) # 미래 시간 오차 방지
    except ValueError:
        target_date = datetime.strptime(str(query), "%Y-%m-%d")
        start_dt = target_date.replace(hour=0, minute=0, second=0)
        end_dt = target_date.replace(hour=23, minute=59, second=59)
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)

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
            total_pnl = 0.0
            trades_count = 0
            pnls = []

            for item in data:
                # 정산 완료 시점(uTime) 기준 필터링
                uTime = int(item.get('uTime') or item.get('cTime') or 0)
                
                if start_ts <= uTime <= end_ts:
                    try:
                        pnl = float(item.get('realizedPnl') or 0.0)
                        total_pnl += pnl
                        trades_count += 1
                        pnls.append(pnl)
                    except:
                        continue

            if trades_count == 0:
                last_info = ""
                if data:
                    last_ts = int(data[0].get('uTime') or data[0].get('cTime', 0))
                    last_kst = datetime.fromtimestamp(last_ts/1000, timezone(timedelta(hours=9)))
                    last_info = f"\n(최근 거래 내역 시각: {last_kst.strftime('%m-%d %H:%M')})"
                return f"📊 {start_dt.strftime('%m-%d')} 이후 매매 내역이 없습니다.{last_info}"

            roi = (total_pnl / current_seed) * 100

            if is_summary:
                return (f"📈 **자산 현황 요약**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"💰 기준 시드: `{current_seed}` USDT\n"
                        f"💵 총 손익: {total_pnl:+.2f} USDT\n"
                        f"📊 수익률: **{roi:+.2f}%**")

            return (f"📊 **성과 리포트**\n"
                    f"📅 {start_dt.strftime('%m-%d')} ~ 현재\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"• 거래 건수: {trades_count}건\n"
                    f"• 총 손익: **{total_pnl:+.2f}** USDT\n"
                    f"• 수익률(ROI): **{roi:+.2f}%**\n"
                    f"• 최대 익/손: {max(pnls):+.2f} / {min(pnls):+.2f}")
