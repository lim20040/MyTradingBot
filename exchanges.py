import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta

# --- OKX API 설정 (본인의 키로 직접 수정하세요) ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "Lim1004!"

def okx_sign(timestamp, method, request_path, secret):
    message = timestamp + method + request_path
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

async def get_combined_report(days):
    method = "GET"
    # 포지션 히스토리 경로
    request_path = "/api/v5/account/positions-history?instType=SWAP&limit=50"
    timestamp = datetime.utcnow().isoformat()[:-3] + "Z"
    
    headers = {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": okx_sign(timestamp, method, request_path, OKX_API_SECRET),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        url = f"https://www.okx.com{request_path}"
        async with session.get(url, headers=headers) as response:
            res = await response.json()
            
            if res.get("code") != "0":
                return f"❌ **OKX API 에러**: {res.get('msg')}"

            data = res.get("data", [])
            
            # --- 핵심 수정 부분: 조회 시작 시점을 오늘 자정으로 설정 ---
            if days == 1:
                # /report 1 인 경우 오늘 00:00:00 부터
                start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # 그 외에는 요청한 일수만큼 이전부터
                start_dt = datetime.now() - timedelta(days=days)
            
            start_ts = int(start_dt.timestamp() * 1000)
            
            pnls = []
            for item in data:
                cTime = int(item.get('cTime', 0))
                if cTime < start_ts:
                    continue
                
                # Realized PnL 추출
                val = item.get('realizedPnl') or item.get('pnl')
                if val is not None:
                    pnls.append(float(val))

            pnls.reverse() 

            if not pnls:
                date_str = start_dt.strftime('%Y-%m-%d %H:%M')
                return f"📊 **{date_str} 이후로 종료된 포지션 내역이 없습니다.**"

            # 지표 계산
            total_trades = len(pnls)
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            
            total_pnl = sum(pnls)
            win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            max_win = max(wins) if wins else 0.0
            max_loss = min(losses) if losses else 0.0
            
            pf = abs(sum(wins) / sum(losses)) if sum(losses) != 0 else float('inf')

            # 연속 최대 승/패 계산
            max_con_wins = 0
            max_con_losses = 0
            curr_wins = 0
            curr_losses = 0
            for p in pnls:
                if p > 0:
                    curr_wins += 1
                    curr_losses = 0
                    max_con_wins = max(max_con_wins, curr_wins)
                elif p < 0:
                    curr_losses += 1
                    curr_wins = 0
                    max_con_losses = max(max_con_losses, curr_losses)

            # 출력 양식 구성
            start_label = start_dt.strftime('%Y-%m-%d %H:%M')
            now_label = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            report = f"📊 **성과 리포트 — 기간 ({start_label} ~ {now_label})**\n"
            report += "━━━━━━━━━━━━━━━━━━\n"
            report += f"• **총 거래:** {total_trades}건 (승 {len(wins)} / 패 {len(losses)})\n"
            report += f"• **승률:** {win_rate:.1f}%\n"
            report += f"• **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.2f} USDT\n"
            report += f"• **평균 이익:** {avg_win:+.2f} USDT\n"
            report += f"• **평균 손실:** {avg_loss:+.2f} USDT\n"
            report += f"• **최대 단건 이익:** {max_win:+.2f} USDT\n"
            report += f"• **최대 단건 손실:** {max_loss:+.2f} USDT\n"
            
            pf_str = f"{pf:.2f}" if pf != float('inf') else "∞ (손실 없음)"
            report += f"• **손익비(PF):** {pf_str}\n"
            report += f"• **연속 최대 승/패:** {max_con_wins}연승 / {max_con_losses}연패"
            
            return report
