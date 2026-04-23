import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta, timezone

# --- OKX API 설정 ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "Lim1004!"

def okx_sign(timestamp, method, request_path, secret):
    message = timestamp + method + request_path
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

async def get_combined_report(query, current_seed, is_summary=False):
    method = "GET"
    request_path = "/api/v5/account/positions-history?instType=SWAP&limit=100"
    
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    timestamp_okx = now_utc.isoformat()[:-9] + "Z"
    
    # --- 시간 범위 설정 ---
    try:
        target_date = datetime.strptime(str(query), "%Y-%m-%d")
        start_dt = target_date.replace(hour=0, minute=0, second=0)
        end_dt = target_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        days = int(query)
        # 시작 시점: 오늘(1일)이면 오늘 00:00부터, n일이면 n일 전 00:00부터
        start_dt = (now_kst - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        # 종료 시점: 현재 시간보다 넉넉하게 미래로 잡아 누락 방지
        end_dt = now_kst + timedelta(hours=2)
    
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
            data = res.get("data", [])
            
            total_realized_pnl = 0
            total_payback = 0
            trades_count = 0

            for item in data:
                # OKX는 cTime(생성시간)이나 uTime(수정시간)을 기준으로 잡는데, 둘 중 하나라도 범위 안에 있으면 포함
                item_time = int(item.get('uTime') or item.get('cTime', 0))
                
                if start_ts <= item_time <= end_ts:
                    pnl = float(item.get('realizedPnl') or 0.0)
                    fee = abs(float(item.get('fee') or 0.0)) # 수수료 절대값
                    
                    total_realized_pnl += pnl
                    total_payback += (fee * 0.3) # 냈던 수수료의 30%를 페이백으로 더함
                    trades_count += 1

            if trades_count == 0:
                return f"📊 {start_dt.strftime('%m-%d')} 이후 내역이 없습니다."

            final_total_pnl = total_realized_pnl + total_payback
            roi = (final_total_pnl / current_seed) * 100

            if is_summary:
                return (f"📈 **자산 현황 요약**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"💵 매매 손익: {total_realized_pnl:+.2f} USDT\n"
                        f"🎁 수수료 페이백: {total_payback:+.2f} USDT\n"
                        f"📊 최종 ROI: **{roi:+.2f}%**")

            return (f"📊 **상세 리포트**\n"
                    f"📅 {start_dt.strftime('%m-%d')} ~ {now_kst.strftime('%m-%d %H:%M')}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"• 거래 건수: {trades_count}건\n"
                    f"• 순수 매매: {total_realized_pnl:+.2f} USDT\n"
                    f"• 예상 페이백: {total_payback:+.2f} USDT\n"
                    f"• 합산 수익: **{final_total_pnl:+.2f}** USDT\n"
                    f"• 수익률: **{roi:+.2f}%**")
