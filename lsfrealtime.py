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
import os
import asyncio
import datetime
import time
import lsrevdata as raccess


# LS증권 접속 정보
# ws_url "wss://openapi.ls-sec.co.kr:9443/websocket"
# api_url "https://openapi.ls-sec.co.kr:8080"

client=pymongo.MongoClient('mongodb+srv://androlimo2osys:Must980419@mongocluster.sm5hzzb.mongodb.net/mydb?retryWrites=true&w=majority')
#client=pymongo.MongoClient('mongodb://stock:0419@127.0.0.1:27017/Stockfuture?replicaSet=rs0&retryWrites=true&w=majority')
stockdb=client['Stockfuture']
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

#g_appkey = "PSQR7rXtUSETOxRzfp2cWtdowY5bRC1rDQNW" #"PSyA055JFN5FhAlMVysqBDdOmjyKLbVOgWEJ"
#g_appsecret = "hXqoXyHf6dkMiTweAC4xsHX5l3UXsBAW" #"94YYLmDHNE8FdM1TKKF3LtkrW0tIBV9b"
ws_url = 'wss://openapi.ls-sec.co.kr:9443/websocket' # 실전투자계좌
api_url="https://openapi.ls-sec.co.kr:8080"

#from Crypto.Cipher import AES
#from Crypto.Util.Padding import unpad
#from base64 import b64decode
 
clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')
key_bytes = 32

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
            