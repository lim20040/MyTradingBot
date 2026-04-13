import hmac
import hashlib
import time
import aiohttp
from datetime import datetime, timedelta

# --- API 설정 ---
BINGX_ACC1_KEY    = "YAXc8PKbKMHafqyl353ViY2XLBZGEIDyz883bxvHegR6nc5Vfvf2Wye5QqGtC4DnEZAnZH98S1y9TByk0Tsg"
BINGX_ACC1_SECRET = "IDvLrNomyhrJspNnMBiJT4T7INJCXJ7cS7Ej39m0oipjDaHsoQEGrJq2C08F1UnN1WBUInIW4WDPC1zawwspA"

BINGX_ACC2_KEY    = "3NZaUYyrIMiO0RcKk4m5lyq83HFQnUrLnd381uKhDfN0jfp2TOvdQfVEuk5Ge5zECVsrsKxm6AZ11Azw"
BINGX_ACC2_SECRET = "qsQ2hDBahCrFBuvZr7BxlUm7ja7uYijdunvZxG7zXGIQM7aiEApzK41A8mVahKqUc3NIKTXaZQypWMg43g"

def bingx_sign(params, secret):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

async def get_bingx_data_debug(session, api_key, secret):
    # 가장 기초적인 '포지션 내역' 경로로 테스트
    url = "https://open-api.bingx.com/openApi/swap/v2/user/getClosedProfit"
    params = {"timestamp": int(time.time() * 1000), "limit": 10}
    params["signature"] = bingx_sign(params, secret)
    headers = {"X-BX-APIKEY": api_key}
    
    async with session.get(url, params=params, headers=headers) as response:
        res_text = await response.text()
        status = response.status
        try:
            res_json = await response.json()
            return {"status": status, "msg": res_json.get("msg"), "code": res_json.get("code"), "data": res_json.get("data", [])}
        except:
            return {"status": status, "raw": res_text[:100]}

async def get_combined_report(days):
    async with aiohttp.ClientSession() as session:
        # 계정 1만 먼저 딥하게 디버깅해봅니다.
        res = await get_bingx_data_debug(session, BINGX_ACC1_KEY, BINGX_ACC1_SECRET)
        
        if res.get("code") != 0:
            return f"❌ **빙엑스 서버 응답 에러**\n- 상태코드: {res.get('status')}\n- 에러코드: {res.get('code')}\n- 메시지: {res.get('msg')}\n\n이 메시지가 뜨면 API 키 설정(IP제한/권한) 문제입니다!"

        trades = res.get("data", [])
        if not trades:
            return f"❓ **인증은 성공했으나 데이터가 0건입니다.**\n- 최근 10건 내역 조회 시도 결과: 빈 리스트\n\n혹시 격리(Isolated)가 아닌 교차(Cross) 마진을 쓰시나요?"

        # 데이터가 있으면 기존 양식대로 출력 (중략)
        return f"✅ 성공! 데이터 {len(trades)}건을 찾았습니다. 양식에 맞춰 출력합니다..."
