import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta, timezone

# --- OKX API 설정 (본인 키로 수정) ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "lIM1004!"

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
    
    try:
        target_date = datetime.strptime(str(query), "%Y-%m-%d")
        start_dt = target_date.replace(hour=0, minute=0, second=0)
        end_dt = target_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        days = int(query)
        if days == 1:
            start_dt = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_dt = (now_kst - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now_kst
    
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
            total_fee = 0
            trades_count = 0
            win_list = []
            loss_list = []
            
            # 시간 순서대로 계산하기 위해 뒤집기
            data.reverse()

            for item in data:
                cTime = int(item.get('cTime', 0))
                if start_ts <= cTime <= end_ts:
                    pnl = float(item.get('realizedPnl') or 0)
                    # 수수료는 보통 음수(-)로 찍히므로 절대값으로 합산
                    fee = abs(float(item.get('fee') or 0))
                    
                    total_realized_pnl += pnl
                    total_fee += fee
                    trades_count += 1
                    
                    if pnl > 0: win_list.append(pnl)
                    elif pnl < 0: loss_list.append(pnl)

            if trades_count == 0:
                return f"📊 **{start_dt.strftime('%m-%d')} 내역이 없습니다.**"

            # --- 페이백 계산 (30%) ---
            payback_amount = total_fee * 0.30
            final_pnl = total_realized_pnl + payback_amount
            roi = (final_pnl / current_seed) * 100

            # --- [현재 수익 현황] 요약 모드 ---
            if is_summary:
                report = f"📈 **자산 현황 (페이백 포함)**\n"
                report += f"━━━━━━━━━━━━━━━━━━\n"
                report += f"💰 기준 시드: `{current_seed}` USDT\n"
                report += f"💵 확정 수익: {total_realized_pnl:+.2f} USDT\n"
                report += f"🎁 예상 페이백(30%): {payback_amount:+.2f} USDT\n"
                report += f"📊 합계 ROI: **{roi:+.2f}%**\n"
                return report

            # --- [상세 리포트] 모드 ---
            win_rate = (len(win_list) / trades_count * 100)
            
            report = f"📊 **성과 리포트 (페이백 반영)**\n"
            report += f"📅 {start_dt.strftime('%m-%d')} ~ {end_dt.strftime('%m-%d')}\n"
            report += "━━━━━━━━━━━━━━━━━━\n"
            report += f"• **총 거래:** {trades_count}건 (승 {len(win_list)} / 패 {len(loss_list)})\n"
            report += f"• **승률:** {win_rate:.1f}%\n"
            report += f"• **매매 손익:** {total_realized_pnl:+.2f} USDT\n"
            report += f"• **페이백 합산:** {final_pnl:+.2f} USDT\n"
            report += f"• **최종 수익률:** **{roi:+.2f}%**\n"
            report += f"• **평균 익/손:** {sum(win_list)/len(win_list) if win_list else 0:+.2f} / {sum(loss_list)/len(loss_list) if loss_list else 0:+.2f}"
            
            return report
