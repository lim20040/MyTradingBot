import hmac
import hashlib
import time
import aiohttp
import base64
from datetime import datetime, timedelta

# --- OKX API 설정 (Passphrase가 반드시 필요합니다) ---
OKX_API_KEY    = "b3bbbe7f-3782-4d4c-abe6-abfb6995b387"
OKX_API_SECRET = "1862D6D68735644487A1CB210DA841AF"
OKX_PASSPHRASE = "Lim1004!" # OKX는 키 만들 때 직접 정한 비번이 하나 더 있습니다.

def okx_sign(timestamp, method, request_path, secret):
    message = timestamp + method + request_path
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

async def get_combined_report(days):
    # 최근 3개월 내역까지 조회 가능한 OKX V5 경로
    method = "GET"
    request_path = "/api/v5/account/bills?instType=SWAP&mgnMode=cross&type=5" # type 5가 실현손익 내역
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
                return f"❌ **OKX API 에러**\n- 메시지: {res.get('msg')}\n(OKX는 Passphrase가 틀리면 인증이 안 됩니다.)"

            data = res.get("data", [])
            if not data:
                return f"📊 **최근 {days}일간 OKX 매매 내역이 없습니다.**"

            # pnl 필드를 합산하여 계산
            pnls = [float(item['pnl']) for item in data if item.get('pnl')]
            total_pnl = sum(pnls)
            
            report = f"📊 **OKX 성과 리포트**\n"
            report += "━━━━━━━━━━━━━━━━━━\n"
            report += f"• **총 거래:** {len(pnls)}건\n"
            report += f"• **총 손익:** {'🟢' if total_pnl >= 0 else '🔴'} {total_pnl:+.2f} USDT\n"
            
            return report
