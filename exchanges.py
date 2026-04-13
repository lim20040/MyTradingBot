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
    # 필터를 제거하고 전체 내역을 가져온 뒤 코드에서 선별합니다 (가장 확실한 방법)
    request_path = "/api/v5/account/bills?instType=SWAP&limit=50" 
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
            
            # 실제 손익(pnl)이 0이 아닌 것들만 골라냅니다.
            valid_pnls = []
            for item in data:
                pnl = float(item.get('pnl', 0))
                # type 5(실현손익), 2(포지션종료) 등 수익 관련 내역 필터링
                if pnl != 0:
                    valid_pnls.append(pnl)

            if not valid_pnls:
                return f"📊 **최근 {days}일간 OKX 매매 내역이 없습니다.**\n(지갑이 'Trading Account'인지 확인해주세요!)"

            total_pnl = sum(valid_pnls)
            wins = [p for p in valid_pnls if p > 0]
            losses = [p for p in valid_pnls if p < 0]
            
            report = f"📊 **성과 리포트 — OKX**\n"
            report += "━━━━━━━━━━━━━━━━━━\n"
            report += f"• **총 거래:** {len(valid_pnls)}건 (승 {len(wins)} / 패 {len(losses)})\n"
            report += f"• **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.2f} USDT\n"
            report += f"• **최대 수익:** {max(valid_pnls) if valid_pnls else 0:+.2f} USDT\n"
            report += f"• **최대 손실:** {min(valid_pnls) if valid_pnls else 0:+.2f} USDT\n"
            
            return report
