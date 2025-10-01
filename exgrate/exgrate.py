# exchange_rate_fetcher.py
import requests
import json # JSON 응답을 보기 좋게 출력하기 위해 임포트
import datetime
import pymongo


client=pymongo.MongoClient('mongodb+srv://androlimo2osys:Must980419@mongocluster.sm5hzzb.mongodb.net/mydb?retryWrites=true&w=majority')
stockdb=client['Stockfuture']
exgratetable = stockdb.exgrates
mastertable = stockdb.mastercodes

# 발급받은 ExchangeRate-API 키를 여기에 입력하세요.
# 절대로 공개 저장소에 API 키를 직접 올리지 마세요!
# 실제 애플리케이션에서는 환경 변수 등으로 관리하는 것이 좋습니다.
API_KEY = "757d79d628aa8332f915af95"

def get_exchange_rates(base_currency: str = "USD") -> dict:
    """
    ExchangeRate-API에서 최신 환율 정보를 가져옵니다.

    Args:
        base_currency (str): 기준이 되는 통화 코드 (예: "USD", "KRW", "EUR").
                             무료 플랜에서는 'USD'가 기본이며, 다른 통화도 지원합니다.

    Returns:
        dict: 환율 정보가 담긴 딕셔너리. API 호출 실패 시 빈 딕셔너리 반환.
    """
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{base_currency.upper()}"
    
    print(f"Fetching exchange rates from: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status() # HTTP 에러 (4xx, 5xx) 발생 시 예외 발생

        data = response.json()

        if data.get("result") == "success":
            return data
        else:
            print(f"Error from API: {data.get('error-type', 'Unknown error')}")
            return {}

    except requests.exceptions.RequestException as e:
        print(f"Network or API request error: {e}")
        return {}
    except json.JSONDecodeError:
        print("Failed to decode JSON response.")
        return {}

def get_rate_for_pair(base_currency: str, target_currency: str) -> float | None:
    """
    특정 통화 쌍의 환율을 가져옵니다.

    Args:
        base_currency (str): 기준 통화 코드.
        target_currency (str): 대상 통화 코드.

    Returns:
        float | None: 환율 값. 찾을 수 없거나 에러 발생 시 None 반환.
    """
    data = get_exchange_rates(base_currency)
    if data and "conversion_rates" in data:
        krwValue = data["conversion_rates"].get(target_currency.upper())
        dataDic={} 
        
        dataDic['code']=base_currency
        dataDic['price']=f"{krwValue:.2f}"
        current_time = datetime.datetime.now() 
        dataDic['udpate']=current_time.strftime('%Y-%m-%d %H:%M:%S')
        
        filter = {'code' : base_currency}
        newvalues = { "$set": dataDic }
        exgratetable.update_one(filter, newvalues,upsert=True)  
        return krwValue;
    return None

if __name__ == "__main__":
    # --- 모든 환율 정보 가져오기 (USD 기준) ---
    ''' 
    print("\n--- All rates (Base: USD) ---")
    all_usd_rates = get_exchange_rates("USD")
    if all_usd_rates:
        # 보기 좋게 JSON 출력
        print(json.dumps(all_usd_rates, indent=4))
    else:
        print("Failed to get all USD rates.")
    '''
    # --- 특정 통화 쌍 환율 가져오기 (USD to KRW) ---
    print("\n--- USD to KRW rate ---")
    usd_to_krw_rate = get_rate_for_pair("USD", "KRW")
    if usd_to_krw_rate is not None:
        print(f"1 USD = {usd_to_krw_rate:.2f} KRW")
        dataDic={} 
        dataDic['marketcode']='CME'
        dataDic['exchangerate']=f"{usd_to_krw_rate:.2f}"
        #current_time = datetime.datetime.now() 
        #dataDic['udpate']=current_time.strftime('%Y-%m-%d %H:%M:%S')
        filter = {'marketcode' : 'CME'}
        newvalues = { "$set": dataDic }
        mastertable.update_many(filter, newvalues,upsert=False)  
    else:
        print("Failed to get USD to KRW rate.")

    # --- 특정 통화 쌍 환율 가져오기 (KRW to JPY) ---
    print("\n--- HKD to KRW rate ---")
    krw_to_hkd_rate = get_rate_for_pair("HKD", "KRW")
    if krw_to_hkd_rate is not None:
        print(f"1 HKD = {krw_to_hkd_rate:.2f} KRW")
        dataDic={} 
        dataDic['marketcode']='HKEx'
        dataDic['exchangerate']=f"{krw_to_hkd_rate:.2f}"
        #current_time = datetime.datetime.now() 
        #dataDic['udpate']=current_time.strftime('%Y-%m-%d %H:%M:%S')
        filter = {'marketcode' : 'HKEx'}
        newvalues = { "$set": dataDic }
        mastertable.update_many(filter, newvalues,upsert=False)  
    else:
        print("Failed to get KRW to JPY rate.")

    # --- 존재하지 않는 통화 시도 (에러 테스트) ---
    '''
    non_existent_rate = get_rate_for_pair("EUR", "KRW")
    if non_existent_rate is not None:
        print(f"1 EUR= {non_existent_rate} KRW")
    else:
        print("Failed to get XYZ to ABC rate (expected).")
    '''    