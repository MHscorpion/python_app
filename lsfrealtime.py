#
# Title   : Futures ws data realtime receiver 
# test OS : MAC M3 pro  Sonoma 14.4
#
import logging
import logging.handlers
import sys
import traceback
import pymongo
import socketio 
import websockets
import json
import requests
import hashlib
import os
import asyncio
import datetime
import time
import lsrevdata as raccess
from datetime import date, timedelta

# LS증권 접속 정보
# ws_url "wss://openapi.ls-sec.co.kr:9443/websocket"
# api_url "https://openapi.ls-sec.co.kr:8080"

#client=pymongo.MongoClient('mongodb+srv://androlimo2osys:Must980419@mongocluster.sm5hzzb.mongodb.net/mydb?retryWrites=true&w=majority')
#client=pymongo.MongoClient('mongodb://stock:0419@127.0.0.1:27017/Stockfuture?replicaSet=rs0&retryWrites=true&w=majority')
client=pymongo.MongoClient('mongodb+srv://neov5550:must98*419@cluster1.fe2ug5h.mongodb.net/tradeccs?retryWrites=true&w=majority&appName=Cluster1')

stockdb=client['tradeccs']
#futuretable = stockdb.stockfutureinfos
mastertable = stockdb.mastercodes
tradingfirmtable = stockdb.tradingfirms
exgratetable = stockdb.exgrates

presentCodelist = {}

logger = logging.getLogger(__name__)
formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] =>> %(message)s')

streamHandler = logging.StreamHandler()
fileHandler = logging.FileHandler('./server.log')

streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)

logger.addHandler(streamHandler)
logger.addHandler(fileHandler)

logger.setLevel(level=logging.DEBUG)

masterCodeList=[]
masterCodeDict = {} 

g_appkey = "PSOdB4dK0vMFThPNkCjfXJKZCpI3nYxPU3Ez" #"PSQR7rXtUSETOxRzfp2cWtdowY5bRC1rDQNW" #"PSyA055JFN5FhAlMVysqBDdOmjyKLbVOgWEJ"
g_appsecret = "NRBinUGvs3WTVc9gw2WVVuZtr77mJXj7" 
API_KEY = "757d79d628aa8332f915af95"

#g_appkey = "PSQR7rXtUSETOxRzfp2cWtdowY5bRC1rDQNW" #"PSyA055JFN5FhAlMVysqBDdOmjyKLbVOgWEJ"
#g_appsecret = "hXqoXyHf6dkMiTweAC4xsHX5l3UXsBAW" #"94YYLmDHNE8FdM1TKKF3LtkrW0tIBV9b"
ws_url = 'wss://openapi.ls-sec.co.kr:9443/websocket' # 실전투자계좌
api_url="https://openapi.ls-sec.co.kr:8080"

#from Crypto.Cipher import AES
#from Crypto.Util.Padding import unpad
#from base64 import b64decode
 
clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')
key_bytes = 32


def get_public_ip() -> str | None:
    """
    외부 서비스를 통해 현재 시스템의 공인 IP 주소를 가져옵니다.
    """
    try:
        # 공인 IP 주소를 간단하게 제공하는 서비스(icanhazip.com) 사용
        response = requests.get('https://icanhazip.com', timeout=5)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"❌ 공인 IP를 가져오는 중 오류 발생: {e}")
        return None

def read_and_verify_code_file(ip_to_verify: str, input_file: str = "code.txt") -> bool:
    """
    파일에서 저장된 해시 값을 읽어 들여, 새로운 IP 주소의 해시 값과 비교합니다.
    """
    if not os.path.exists(input_file):
        print(f"⚠️ 오류: 파일 '{input_file}'을 찾을 수 없습니다. 먼저 파일을 생성해야 합니다.")
        return False
    
    try:
        # 1. 파일에서 저장된 해시 값을 읽어옵니다.
        with open(input_file, 'r', encoding='utf-8') as f:
            stored_hash = f.read().strip()
        
        # 2. 검증하려는 IP 주소의 해시 값을 생성합니다.
        verify_hash_object = hashlib.sha256(ip_to_verify.encode('utf-8'))
        verify_hex_digest = verify_hash_object.hexdigest()

        # 3. 두 해시 값을 비교합니다.
        print("\n" + "=" * 35)
        print(f"🔍 검증 대상 IP: {ip_to_verify} (현재 공인 IP)")
        
        if stored_hash == verify_hex_digest:
            print(f"⭐ 검증 성공: 현재 공인 IP의 해시가 저장된 파일과 **일치**합니다.")
            print(f"저장된 해시: {stored_hash[:10]}...")
            print("=" * 35)
            return True
        else:
            print(f"❌ 검증 실패: 현재 공인 IP의 해시가 저장된 파일과 **일치하지 않습니다**.")
            print(f"저장된 해시: {stored_hash}")
            print(f"현재 IP 해시: {verify_hex_digest}")
            print("=" * 35)
            return False

    except IOError as e:
        print(f"❌ 파일 읽기 오류가 발생했습니다: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        return False


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

def get_agent_info(akey):
    """
    Connects to the NestJS server and retrieves agent information by hocode.

    :param hocode: The hocode to query.
    :return: A dictionary with agent information or None if not found.
    """
    api_url = f"http://54.249.40.102:7272/agents/key/{akey}"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Assuming the API returns JSON data
        agent_info = response.json()
        return agent_info

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"Agent with akey '{akey}' not found.")
            exit()
        else:
            print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response.")

    return None

def read_hocode_from_file(file_path):
    """
    지정된 파일에서 hocode를 읽어옵니다.
    :param file_path: hocode가 포함된 파일의 경로.
    :return: 파일에서 읽은 hocode 문자열.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        # 파일에서 첫 번째 줄을 읽고 양쪽 공백을 제거합니다.
        hocode = f.readline().strip()
    
    return hocode


def sendToServer(trid,data):
    global sio
    print('sendtoServer %s' % sio.connected)
    if sio.connected == True :
        print('send to server')
        sio.emit(trid,data)
        
def getMasterCode():
    global ws_url
    global api_url
    global g_appkey
    global g_appsecret
    #getCodes = mastertable.find({"enable":"true"})
    masterCodeList.clear()
    print('getMasterCode query...')
    for x in mastertable.find({ "enable": "true" },{"_id":0 ,"region":1,"tr_id":1,"tr_id2":1,"code":1,"tsize":1,"name":1}):
        xStr=str(x)
        jsonStrChg = xStr.replace("'", "\"")
        masterCodeList.append(jsonStrChg)
        code = x.get("code")
        code = code.ljust(8,' ')
        tsize = float(x.get("tsize", "0"))
        if code:
            masterCodeDict[code] = tsize 
    
    for x in tradingfirmtable.find({"tr_cd":"KO_LST"},{"_id":0 ,"ws_url":1,"api_url":1,"app_key":1,"app_secret":1}):
        tInfoStr =  str(x) 
        jsonStrChg = tInfoStr.replace("'", "\"")  
        print(jsonStrChg)
        dict = json.loads(jsonStrChg)
    
    print(masterCodeDict)    
   
    ws_url=dict['ws_url']
    print(ws_url)
    api_url=dict['api_url']
    print(api_url)
    #g_appkey=dict['app_key']
    print(g_appkey)
    #g_appsecret=dict['app_secret']
    print(g_appsecret)
    
def get_tsize_by_code(code: str) -> str:
    return masterCodeDict.get(code, "코드가 존재하지 않습니다.")
'''
def find_by_code( code):
    global masterCodeList
    # 리스트를 순회하면서 'code' 값을 비교
    print('find_by_code')
    for item in masterCodeList:
        dict = json.loads(item)
        print(f"find code {dict['code']}")
        if item.get("code") == code:
            return item  # 일치하는 사전 반환
    return None
'''

def get_exchangeRate():
    #global api_url
    try:
        print('------ 환률 조회 요청 ------')    
        '''      
        headers = {"content-type": "application/json"}
        paramData = {"authkey": "Yge3eVr5q6ZwH571fTkCa4EqLKOpjI1T",
                     "searchdate":"20250617",
                "data": 'AP01',
                }
        PATH = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON"
        URL = f"{PATH}"
        res = requests.get(URL,params=paramData)
        
        jsonData = res.json() 
        
        for zone in jsonData:
            #print(zone["cur_nm"], ":", zone["cur_unit"], ":",zone["deal_bas_r"],)
            dataDic={} 
            dataDic['name']=zone["cur_nm"]
            dataDic['code']=zone["cur_unit"]
            dataDic['price']=zone["deal_bas_r"].replace(',','')
            current_time = datetime.datetime.now() 
            dataDic['udpate']=current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            filter = {'code' : dataDic['code']}
            newvalues = { "$set": dataDic }
            exgratetable.update_one(filter, newvalues,upsert=True)  
        '''
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
            print('------ 환률 조회 완료 ------') 
    except Exception as e: 
        print(e)

# 웹소켓 접속키 발급
def get_approval(key, secret):
    
    # url = https://openapivts.koreainvestment.com:29443' # 모의투자계좌     
    # application/json; charset=UTF-8  application/x-www-form-urlencoded
    
    headers = {"content-type": "application/x-www-form-urlencoded"}
    body = {
            'appkey': key,
            'appsecretkey': secret,
            'grant_type': 'client_credentials',
            'scope':'oob',
            }
    PATH = "/oauth2/token"
    URL = f"{api_url}{PATH}"
    print(URL)
    print(key)
    print(secret)
    
    res = requests.post(URL, headers=headers, data=body)
    print(res.json())
    approval_key = res.json()["access_token"]
    logger.debug('approval_key 발급')
    logger.debug(approval_key)
    return approval_key
 

async def lsmainLoop():
    try:
        global presentCodelist
        #마스터코드 및 증권사 정보 읽어오기
        getMasterCode()
        get_exchangeRate()
        
        g_approval_key = get_approval(g_appkey, g_appsecret)
        #print("approval_key [%s]" % (g_approval_key))
        senddata_list=[]
        senddata_list.clear()
        code_list =[]
        code_list.clear()
        raccess.deleteCodeInfo()
        
        for getdata in masterCodeList:
            dict = json.loads(getdata)
            print(dict["tr_id"])    
            print(dict["tr_id2"])    
            if dict["tr_id"]=="OVH" : # 해외 지수선물 코드
                raccess.insertCodeInfo(dict["code"])
                fcode = dict["code"].ljust(8,' ')
                code_list.append([dict["tr_id"],fcode])
                code_list.append([dict["tr_id2"],fcode])

            if dict["tr_id"]=="FH0" : #국내 지수선물 코드 (KOSPI200)
                codeDec = dict["code"]
                fcode = dict["code"].ljust(8,' ')
                raccess.insertCodeInfo(dict["code"])
                code_list.append([dict["tr_id"],dict["code"]])
                code_list.append([dict["tr_id2"],dict["code"]])    
        
        #kospi     tr_cd  'FC0' , 'FH0'
        #oversea   tr_cde  'OVC' , 'OVH'
        print(code_list)
        for cd,key in code_list:
            temp = '{"header":{"token":"%s","tr_type":"3"},"body":{"tr_cd":"%s","tr_key":"%s"}}'%(g_approval_key,cd,key) 
            print(temp)
            senddata_list.append(temp)   
        
        # GCX24 gold   
        # CLX24  oil
        # NGX24  gas  
        # SIX24 silver
        # YMZ24 mini-dow($5)  42365.0 항셍과 같은 지수구조, 끝에 .0 포함 
        '''
        temp = '{"header":{"token":"%s","tr_type":"3"},"body":{"tr_cd":"OVH","tr_key":"YMZ24   "}}'%(g_approval_key) 
        senddata_list.append(temp)  
        temp = '{"header":{"token":"%s","tr_type":"3"},"body":{"tr_cd":"OVC","tr_key":"YMZ24   "}}'%(g_approval_key) 
        senddata_list.append(temp)    
        '''  
        raccess.connetServer()
        #async with websockets.connect(ws_url, ping_interval=None) as websocket:
        async for websocket in websockets.connect(ws_url, ping_interval=None):    
            try:
                logger.debug('websockets.Connection complete')
                print('websockets.Connection complete')
                
                for senddata in senddata_list:
                    await websocket.send(senddata)
                    await asyncio.sleep(0.5)
                    print(f"request is :{senddata}")

                while True:
                    data = await websocket.recv()
                    #await asyncio.sleep(0.1)
                    #print(f"Recev Command is : {data}")  # 정제되지 않은 Request / Response 출력
                    data = json.loads(data)
                    
                    
                    if "tr_key" in data['header'] :
                        #print(data["header"]["tr_key"])
                        #if data["header"]["tr_key"] == "101W6000" :
                        #    print ( data["body"] )
                        #start_time = time.time()
                        tsize = get_tsize_by_code(data['header']['tr_key'])
                        await raccess.revDataAccess(data["header"]["tr_cd"],1,tsize,data["body"])
                        #end_time = time.time()
                        #execution_time = end_time - start_time
                        #print(f"raccess.revDataAccess executed in: {execution_time:.6f} seconds")
            
            except  websockets.ConnectionClosed:
                logger.debug('websocket connection closed exception!!')            
                continue               

    except Exception as error:
        print("lsmainloop() exception!! %s" % error)
        logger.debug('lsmainloop() exception!!')
        print('Connect Again!')
        logger.debug('Connect Again!!')
        time.sleep(0.1)

        # 웹소켓 다시 시작
        await lsmainLoop()

                    
# 비동기로 서버에 접속한다.
async def main():
    
    #file_name = "/Users/devbox/project/code.txt"
    file_name = "/etc/code.txt"

    hocode_from_file = ""
    # 2. 현재 공인 IP를 가져와서 검증 시작
    current_public_ip = get_public_ip()

    try:
        hocode_from_file = read_hocode_from_file(file_name)
    except FileNotFoundError as e:
        print(e)
        exit()
    
    if not hocode_from_file:
        print(f"오류: '{file_name}' 파일이 비어 있습니다.")
        exit()
    
    if current_public_ip:
        read_and_verify_code_file(current_public_ip,file_name)
    else:
        print("공인 IP를 가져오지 못하여 검증을 건너뜜.")
        exit()

    agent_data = get_agent_info(hocode_from_file)

    if agent_data:
        print("Agent Information:")
        print(f"  hocode: {agent_data.get('hocode')}")
        print(f"  name: {agent_data.get('name')}")
        print(f"  rsserver: {agent_data.get('rsserver')}")
        print(f"  ccserver: {agent_data.get('ccserver')}")
        print(f"  dbserver: {agent_data.get('dbserver')}")
        print(f"  active: {agent_data.get('active')}")
        print(f"  activekey: {agent_data.get('activekey')}")
        raccess.setServerIp(agent_data.get('rsserver'),agent_data.get('ccserver'))
        raccess.clServerIP = agent_data.get('rsserver')
        raccess.csServerIP = agent_data.get('ccserver')
        raccess.outputServerIp()
        if agent_data.get('active') == 'false':
            exit()
    else:
        print("Failed to retrieve agent information.")
    
    try:
        # 웹소켓 시작
        await lsmainLoop()

    except Exception as e:
        print('main() Exception Raised! %s' % e)
        logger.debug('main() Exception Raised!')
        print(e)

        
if __name__ == "__main__":

    # noinspection PyBroadException
    try:
        # ---------------------------------------------------------------------
        # Logic Start!
        # ---------------------------------------------------------------------
        # 웹소켓 시작
        print('program start!!');
        asyncio.run(main())
        

    except KeyboardInterrupt:
        print("KeyboardInterrupt Exception 발생!")
        print(traceback.format_exc())
        sys.exit(-100)

    except Exception:
        print("start Exception 발생!")
        print(traceback.format_exc())
        sys.exit(-200)
            