import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta

# --- OKX API 설정 ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "Lim1004!"

def okx_sign(timestamp, method, request_path, secret):
    message = timestamp + method + request_path
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

async def get_combined_report(days):
    method = "GET"
    # 최근 내역을 충분히 가져옵니다.
    request_path = f"/api/v5/account/bills?instType=SWAP&type=2&limit=100" 
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
            data = res.get("data", [])
            
            # 1. 주문 ID별로 손익 합산 (데이터 왜곡 방지)
            trade_map = {}
            for item in data:
                ts = int(item.get('ts', 0))
                # 요청한 기간 내의 데이터만 필터링
                if ts < int((datetime.now() - timedelta(days=days)).timestamp() * 1000):
                    continue
                oid = item.get('ordId')
                pnl = float(item.get('pnl', 0))
                if oid and pnl != 0:
                    if oid not in trade_map:
                        trade_map[oid] = {'pnl': 0, 'ts': ts}
                    trade_map[oid]['pnl'] += pnl

            # 시간순 정렬
            sorted_trades = sorted(trade_map.values(), key=lambda x: x['ts'])
            pnls = [t['pnl'] for t in sorted_trades]

            if not pnls:
                return f"📊 **최근 {days}일간 매매 내역이 없습니다.**"

            # 2. 지표 계산
            total_trades = len(pnls)
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
            
            total_pnl = sum(pnls)
            avg_win = sum(wins) / win_count if win_count > 0 else 0
            avg_loss = sum(losses) / loss_count if loss_count > 0 else 0
            
            max_win = max(pnls) if pnls else 0
            max_loss = min(pnls) if pnls else 0
            
            pf = abs(sum(wins) / sum(losses)) if sum(losses) != 0 else float('inf')

            # 3. 연속 승/패 계산
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_wins = 0
            current_losses = 0
            
            for p in pnls:
                if p > 0:
                    current_wins += 1
                    current_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_wins)
                elif p < 0:
                    current_losses += 1
                    current_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)

            # 4. 결과 출력 (사진 양식 준수)
            now_str = datetime.now().strftime('%Y-%m-%d')
            start_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            report = f"📊 **성과 리포트 — 기간 ({start_str} ~ {now_str})**\n"
            report += "━━━━━━━━━━━━━━━━━━\n"
            report += f"• **총 거래:** {total_trades}건 (승 {win_count} / 패 {loss_count})\n"
            report += f"• **승률:** {win_rate:.1f}%\n"
            report += f"• **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.2f} USDT\n"
            report += f"• **평균 이익:** {avg_win:+.2f} USDT\n"
            report += f"• **평균 손실:** {avg_loss:+.2f} USDT\n"
            report += f"• **최대 단건 이익:** {max_win:+.2f} USDT\n"
            report += f"• **최대 단건 손실:** {max_loss:+.2f} USDT\n"
            
            pf_str = f"{pf:.2f}" if pf != float('inf') else "∞ (손실 없음)"
            report += f"• **손익비(PF):** {pf_str}\n"
            report += f"• **연속 최대 승/패:** {max_consecutive_wins}연승 / {max_consecutive_losses}연패"
            
            return report
