import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta, timezone

# --- OKX API 설정 (본인 키 입력) ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "Lim1004!"

def okx_sign(timestamp, method, request_path, secret):
    message = timestamp + method + request_path
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

async def get_combined_report(query, current_seed):
    method = "GET"
    request_path = "/api/v5/account/positions-history?instType=SWAP&limit=50"
    
    # 시간 설정 (KST 강제 적용)
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    timestamp_okx = now_utc.isoformat()[:-9] + "Z"
    
    # 기간 판별 로직
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
            
            pnls = []
            for item in data:
                cTime = int(item.get('cTime', 0))
                if start_ts <= cTime <= end_ts:
                    val = item.get('realizedPnl') or item.get('pnl')
                    if val is not None:
                        pnls.append(float(val))

            pnls.reverse() 

            if not pnls:
                return f"📊 **{start_dt.strftime('%m-%d')} 기간에 내역이 없습니다.**"

            # 지표 계산
            total_trades = len(pnls)
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            total_pnl = sum(pnls)
            
            # 수익률(ROI) 계산
            roi = (total_pnl / current_seed) * 100
            
            win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            max_win = max(wins) if wins else 0.0
            max_loss = min(losses) if losses else 0.0

            # 연속 최대 승/패
            max_con_wins, max_con_losses, curr_wins, curr_losses = 0, 0, 0, 0
            for p in pnls:
                if p > 0:
                    curr_wins += 1; curr_losses = 0
                    max_con_wins = max(max_con_wins, curr_wins)
                elif p < 0:
                    curr_losses += 1; curr_wins = 0
                    max_con_losses = max(max_con_losses, curr_losses)

            # 리포트 출력 양식
            report = f"📊 **성과 리포트 (KST)**\n"
            report += f"📅 {start_dt.strftime('%m-%d %H:%M')} ~ {end_dt.strftime('%m-%d %H:%M')}\n"
            report += "━━━━━━━━━━━━━━━━━━\n"
            report += f"• **총 거래:** {total_trades}건 (승 {len(wins)} / 패 {len(losses)})\n"
            report += f"• **승률:** {win_rate:.1f}%\n"
            report += f"• **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.2f} USDT\n"
            report += f"• **수익률(ROI):** {roi:+.2f}% (기준: {current_seed})\n"
            report += f"• **평균 익/손:** {avg_win:+.2f} / {avg_loss:+.2f}\n"
            report += f"• **최대 익/손:** {max_win:+.2f} / {max_loss:+.2f}\n"
            report += f"• **연속 승/패:** {max_con_wins}연승 / {max_con_losses}연패"
            
            return report
