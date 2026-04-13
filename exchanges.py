import os
import hmac
import hashlib
import time
import aiohttp
from datetime import datetime, timedelta, timezone

# --- 환경변수 설정 (본인의 키를 여기에 입력하세요) ---
BINGX_API_KEY    = "YAXc8PKbKMHafqyl353ViY2XLBZGEIDyz883bxvHegR6nc5Vfvf2Wye5QqGtC4DnEZAnZH98S1y9TByk0Tsg"
BINGX_API_SECRET = "IDvLrNomyhrJspNnMBiJT4T7INJCXJ7cS7Ej39m0oipjDaHsoQEGrJq2C08F1UnN1WBUInIW4WDPC1zawwspA"
BYBIT_API_KEY    = "sk8aiEADPhwdk4HVly"
BYBIT_API_SECRET = "PpHkUqnCUPsq0mO8sxsjjLXRL7GgVfEgRZtv"

# --- 공통 유틸 ---
def now_ms():
    return int(time.time() * 1000)

async def fetch(session, url, params=None, headers=None):
    async with session.get(url, params=params, headers=headers) as response:
        # 403 에러 등이 나더라도 봇이 죽지 않게 예외 처리
        if response.status != 200:
            return None
        try:
            return await response.json()
        except:
            return None

# --- 바이비트 서명 ---
def bybit_sign(params, secret):
    param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode(), param_str.encode(), hashlib.sha256).hexdigest()

# --- 통합 리포트 생성 ---
async def get_combined_report(days):
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    async with aiohttp.ClientSession() as session:
        # 바이비트 데이터 가져오기 (실패해도 None 반환)
        bybit_url = "https://api.bybit.com/v5/position/closed-pnl"
        bybit_params = {
            "category": "linear", # 본인 계정이 Inverse라면 'inverse'로 수정 필요
            "limit": 100,
            "startTime": start_time,
            "api_key": BYBIT_API_KEY,
            "timestamp": now_ms(),
            "recv_window": 5000
        }
        bybit_params["sign"] = bybit_sign(bybit_params, BYBIT_API_SECRET)
        
        bybit_data = await fetch(session, bybit_url, params=bybit_params)
        
        # 리포트 텍스트 생성
        report = f"📊 **최근 {days}일 거래 리포트**\n\n"
        
        if bybit_data and bybit_data.get("result", {}).get("list"):
            trades = bybit_data["result"]["list"]
            total_pnl = sum(float(t.get("closedPnl", 0)) for t in trades)
            report += f"✅ **Bybit 성과**\n- 실현 손익: {total_pnl:.2f} USDT\n- 종료된 포지션: {len(trades)}건\n"
        else:
            report += "❌ **Bybit**: 데이터를 가져올 수 없습니다. (API 권한 확인 필요)\n"
            
        report += "\n(BingX 데이터는 현재 준비 중입니다.)"
        
        return report
