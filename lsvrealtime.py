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
import lsvrevdata as raccess



client=pymongo.MongoClient('mongodb+srv://devbox72:PyeCYJ0G72MlcpGU@tradeccs.fo3b3.mongodb.net/tradeccs?retryWrites=true&w=majority')
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
g_appsecret = "NRBinUGvs3WTVc9gw2WVVuZtr77mJXj7" #"hXqoXyHf6dkMiTweAC4xsHX5l3UXsBAW" #"94YYLmDHNE8FdM1TKKF3LtkrW0tIBV9b"
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
    
    #print(masterCodeDict)    
   
    ws_url=dict['ws_url']
    print(ws_url)
    api_url=dict['api_url']
    print(api_url)
    #g_appkey=dict['app_key']
    #print(g_appkey)
    #g_appsecret=dict['app_secret']
    #print(g_appsecret)
    
def get_tsize_by_code(code: str) -> str:
    return masterCodeDict.get(code, "코드가 존재하지 않습니다.")
    
def referTest(fcode): 
    print('call referTest()')
    print(f"Master Code List Length: {len(masterCodeDict)}")

def get_exchangeRate():
    #global api_url
    try:
        print('------ 환률 조회 요청 ------')          
        headers = {"content-type": "application/json"}
        paramData = {"authkey": "Yge3eVr5q6ZwH571fTkCa4EqLKOpjI1T",
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
        #get_exchangeRate()
        print("test")
        g_approval_key = get_approval(g_appkey, g_appsecret)
        print("approval_key [%s]" % (g_approval_key))
        senddata_list=[]
        senddata_list.clear()
        code_list =[]
        code_list.clear()
        raccess.deleteCodeInfo()
        
    
        for getdata in masterCodeList:
            dict = json.loads(getdata)
            #print(dict["tr_id"])    
            #print(dict["tr_id2"])    
            if dict["tr_id"]=="OVH" : # 해외 지수선물 코드
                #print(dict["code"])
                raccess.insertCodeInfo(dict["code"])
                fcode = dict["code"].ljust(8,' ')
                code_list.append([dict["tr_id"],fcode])
                code_list.append([dict["tr_id2"],fcode])

            if dict["tr_id"]=="FH0" : #국내 지수선물 코드 (KOSPI200)
                '''
                codeDec = dict["code"]
                prefix_str = codeDec[0:4]
                sub_str = codeDec[4:]
                if sub_str=='12' :
                    sub_str='C'

                recon_str = prefix_str+sub_str    
                recon_str = recon_str.ljust(8,'0')
                '''    
                recon_str='101W3000'
                raccess.insertCodeInfo(recon_str)
                
                code_list.append([dict["tr_id"],recon_str])
                code_list.append([dict["tr_id2"],recon_str])    
        
        #kospi     tr_cd  'FC0' , 'FH0'
        #oversea   tr_cde  'OVC' , 'OVH'
        print(code_list)
        for cd,key in code_list:
            temp = '{"header":{"token":"%s","tr_type":"3"},"body":{"tr_cd":"%s","tr_key":"%s"}}'%(g_approval_key,cd,key) 
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
        #호주달러 ADH25   
        '''  
        raccess.connetServer()
        
        nasdaqvolumedata="""
        { "header":{"tr_cd":"OVH","tr_key":"NQZ25   "},"body":{"offerrem2":"4","offerho4":"20887.0","bidho5":"20877.0","symbol":"NQZ25","offerho3":"20886.0","offerrem3":"1","bidho4":"20878.0","bidno1":"4","offerrem4":"4","offerho5":"20888.0","offerrem5":"2","offerno2":"4","bidno3":"2","offerno1":"3","bidno2":"2","offerno4":"4","bidno5":"3","offerrem1":"3","offerno3":"1","bidno4":"3","offerno5":"2","totoffercnt":"14","totbidcnt":"14","bidrem3":"2","bidrem4":"3","bidrem1":"4","bidrem2":"2","bidho1":"20881.0","hotime":"201507","offerho2":"20885.0","bidho3":"20879.0","bidrem5":"3","offerho1":"20884.0","bidho2":"20880.0","totofferrem":"14","totbidrem":"14"}}"""

        hangsengvolumedata="""
        { "header":{"tr_cd":"OVH","tr_key":"HSIU25  "},"body":{"offerrem2":"4","offerho4":"20887.0","bidho5":"20877.0","symbol":"HSIU25","offerho3":"20886.0","offerrem3":"1","bidho4":"20878.0","bidno1":"4","offerrem4":"4","offerho5":"20888.0","offerrem5":"2","offerno2":"4","bidno3":"2","offerno1":"3","bidno2":"2","offerno4":"4","bidno5":"3","offerrem1":"3","offerno3":"1","bidno4":"3","offerno5":"2","totoffercnt":"14","totbidcnt":"14","bidrem3":"2","bidrem4":"3","bidrem1":"4","bidrem2":"2","bidho1":"20881.0","hotime":"201507","offerho2":"20885.0","bidho3":"20879.0","bidrem5":"3","offerho1":"20884.0","bidho2":"20880.0","totofferrem":"14","totbidrem":"14"}}"""

        hojudalvolumedata="""
        { "header":{"tr_cd":"OVH","tr_key":"ADZ25   "},"body":{"offerrem2":"4","offerho4":"20887.0","bidho5":"20877.0","symbol":"ADZ25","offerho3":"20886.0","offerrem3":"1","bidho4":"20878.0","bidno1":"4","offerrem4":"4","offerho5":"20888.0","offerrem5":"2","offerno2":"4","bidno3":"2","offerno1":"3","bidno2":"2","offerno4":"4","bidno5":"3","offerrem1":"3","offerno3":"1","bidno4":"3","offerno5":"2","totoffercnt":"14","totbidcnt":"14","bidrem3":"2","bidrem4":"3","bidrem1":"4","bidrem2":"2","bidho1":"20881.0","hotime":"201507","offerho2":"20885.0","bidho3":"20879.0","bidrem5":"3","offerho1":"20884.0","bidho2":"20880.0","totofferrem":"14","totbidrem":"14"}}"""
        
        kospivolumedata="""
        { "header":{"tr_cd":"FH0","tr_key":"101W9000"},"body":{"offerrem2":"4","offerho4":"20887.0","bidho5":"20877.0","futcode":"101W9000","offerho3":"20886.0","offerrem3":"1","bidho4":"20878.0","bidno1":"4","offerrem4":"4","offerho5":"20888.0","offerrem5":"2","offerno2":"4","bidno3":"2","offerno1":"3","bidno2":"2","offerno4":"4","bidno5":"3","offerrem1":"3","offerno3":"1","bidno4":"3","offerno5":"2","totoffercnt":"14","totbidcnt":"14","bidrem3":"2","bidrem4":"3","bidrem1":"4","bidrem2":"2","bidho1":"20881.0","hotime":"201507","offerho2":"20885.0","bidho3":"20879.0","bidrem5":"3","offerho1":"20884.0","bidho2":"20880.0","totofferrem":"14","totbidrem":"14","offercnt1":"1","offercnt2":"1","offercnt3":"1","offercnt4":"1","offercnt5":"1","bidcnt1":"1","bidcnt2":"1","bidcnt3":"1","bidcnt4":"1","bidcnt5":"1" }}"""
        
        nasdaqtradedata='{"header":{"tr_cd":"OVC","tr_key":"NQZ25   "},"body":{"ovsmkend":"20241018","symbol":"NQZ25","lSeq":"1","chgrate":"0.50","kordate":"20241018","trdtm":"071508","curpr":"20469.75","ovsdate":"20241018","mdvolume":"","ydiffpr":"101.75","totq":"56802","high":"20479.75","ydiffSign":"2","low":"20320.75","msvolume":"","cgubun":"+","trdq":"1","open":"20384.00","kortm":"211508"}}'
        hangsengtradedata='{"header":{"tr_cd":"OVC","tr_key":"HSIU25  "},"body":{"ovsmkend":"20241018","symbol":"HSIU25","lSeq":"1","chgrate":"0.50","kordate":"20241018","trdtm":"071508","curpr":"17540.0","ovsdate":"20241018","mdvolume":"","ydiffpr":"101.75","totq":"56802","high":"17560.0","ydiffSign":"2","low":"17520.0","msvolume":"","cgubun":"+","trdq":"1","open":"17530.0","kortm":"211508"}}'
        hojudaltradedata='{"header":{"tr_cd":"OVC","tr_key":"ADZ25   "},"body":{"ovsmkend":"20241018","symbol":"ADZ25","lSeq":"1","chgrate":"0.50","kordate":"20241018","trdtm":"071508","curpr":"17540.0","ovsdate":"20241018","mdvolume":"","ydiffpr":"101.75","totq":"56802","high":"17560.0","ydiffSign":"2","low":"17520.0","msvolume":"","cgubun":"+","trdq":"1","open":"17530.0","kortm":"211508"}}'
        #kospitradedata='{"header":{"tr_cd":"OVC","tr_key":"101W9000"},"body":{"ovsmkend":"20241018","symbol":"101W9000","lSeq":"1","chgrate":"1","kordate":"20241018","trdtm":"071508","curpr":"17540.0","ovsdate":"20241018","mdvolume":"1","ydiffpr":"101.75","totq":"56802","high":"323.00","ydiffSign":"2","low":"323.00","msvolume":"1","cgubun":"+","trdq":"1","open":"323,00","kortm":"211508"}}'
        kospitradedata='{"header":{"tr_cd":"FC0","tr_key":"101W9000"},"body":{"futcode": "101W9000", "mdchecnt": "24677", "sign": "2", "mschecnt": "25848", "ibasis": "1.40", "mdvolume": "47535", "cpower": "107.33", "cvolume": "5", "high": "363.15", "low": "322.65", "price": "325.50", "kasis": "-0.37", "cgubun": "-", "bidho1": "325.50", "k200jisu": "325.30", "value": "8071446", "offerho1": "325.55", "jgubun": "40", "change": "1.65", "chetime": "125920", "openyak": "258512", "volume": "99392", "drate": "0.51", "openyakcha": "-962", "jnilvolume": "93515", "msvolume": "51019", "sbasis": "0.20", "theoryprice": "326.70", "open": "323.00"}}'
        
        transDelay = 0.2 #0.05  #0.1 0.01

        while True:
          nqz24value = '20857.00'
          hsiv24value = '19544.0' #['17540.0','17541.0','17542.0','17543.0','17544.0','17545.0','17546.0','17547.0','17548.0','17549.0']
          adh25value = '0.63030'
          kospivalue = '323.00'
          
          nqz24tick = 0.25
          hsiv24tick = 1.0
          adh25tick = round(0.00005,5)
          kospitick = 0.05
          
          nqcurpoint= str(float(nqz24value))    
          hscurpoint= str(float(hsiv24value))    
          adhcurpoint= str(float(adh25value))    
          kospipoint= str(float(kospivalue))    
          
          for i in range(10):
              nasVol = json.loads(nasdaqvolumedata)
              nasCur = json.loads(nasdaqtradedata)
              
              hsVol = json.loads(hangsengvolumedata)
              hsCur = json.loads(hangsengtradedata)
              
              adhVol = json.loads(hojudalvolumedata)
              adhCur = json.loads(hojudaltradedata)
              
              kospiVol = json.loads(kospivolumedata)
              kospiCur = json.loads(kospitradedata)
              
              nqcurpoint =str(float(nqz24value)+nqz24tick*i)
              hscurpoint =str(float(hsiv24value)+hsiv24tick*i)
              adhcurpoint = f"{(float(adh25value)+ adh25tick*i):.5f}"
              kospipoint = f"{(float(kospivalue)+ kospitick*i):.2f}"#str(float(kospivalue)+kospitick*i)
              
              nasCur['body']['curpr'] = nqcurpoint.ljust(8,'0');    
              hsCur['body']['curpr'] = hscurpoint.ljust(7,'0');  
              adhCur['body']['curpr'] = adhcurpoint #.ljust(7,'0');    
              kospiCur['body']['price'] = kospipoint.ljust(6,'0');  
              
              nasVol['body']['offerho1'] = str(float(nqcurpoint)+nqz24tick*(1)).ljust(8,'0')
              nasVol['body']['offerho2'] = str(float(nqcurpoint)+nqz24tick*(2)).ljust(8,'0')
              nasVol['body']['offerho3'] = str(float(nqcurpoint)+nqz24tick*(3)).ljust(8,'0')
              nasVol['body']['offerho4'] = str(float(nqcurpoint)+nqz24tick*(4)).ljust(8,'0')
              nasVol['body']['offerho5'] = str(float(nqcurpoint)+nqz24tick*(5)).ljust(8,'0')

              nasVol['body']['bidho1'] = str(float(nqcurpoint)-nqz24tick*(1)).ljust(8,'0')
              nasVol['body']['bidho2'] = str(float(nqcurpoint)-nqz24tick*(2)).ljust(8,'0')
              nasVol['body']['bidho3'] = str(float(nqcurpoint)-nqz24tick*(3)).ljust(8,'0')
              nasVol['body']['bidho4'] = str(float(nqcurpoint)-nqz24tick*(4)).ljust(8,'0')
              nasVol['body']['bidho5'] = str(float(nqcurpoint)-nqz24tick*(5)).ljust(8,'0')

              hsVol['body']['offerho1'] = str(float(hscurpoint)+hsiv24tick*(1)).ljust(7,'0')
              hsVol['body']['offerho2'] = str(float(hscurpoint)+hsiv24tick*(2)).ljust(7,'0')
              hsVol['body']['offerho3'] = str(float(hscurpoint)+hsiv24tick*(3)).ljust(7,'0')
              hsVol['body']['offerho4'] = str(float(hscurpoint)+hsiv24tick*(4)).ljust(7,'0')
              hsVol['body']['offerho5'] = str(float(hscurpoint)+hsiv24tick*(5)).ljust(7,'0')

              hsVol['body']['bidho1'] = str(float(hscurpoint)-hsiv24tick*(1)).ljust(7,'0')
              hsVol['body']['bidho2'] = str(float(hscurpoint)-hsiv24tick*(2)).ljust(7,'0')
              hsVol['body']['bidho3'] = str(float(hscurpoint)-hsiv24tick*(3)).ljust(7,'0')
              hsVol['body']['bidho4'] = str(float(hscurpoint)-hsiv24tick*(4)).ljust(7,'0')
              hsVol['body']['bidho5'] = str(float(hscurpoint)-hsiv24tick*(5)).ljust(7,'0')
              
              adhVol['body']['offerho1'] = f"{(float(adhcurpoint)+adh25tick*(1)):.5f}"
              adhVol['body']['offerho2'] = f"{(float(adhcurpoint)+adh25tick*(2)):.5f}"
              adhVol['body']['offerho3'] = f"{(float(adhcurpoint)+adh25tick*(3)):.5f}"
              adhVol['body']['offerho4'] = f"{(float(adhcurpoint)+adh25tick*(4)):.5f}"
              adhVol['body']['offerho5'] = f"{(float(adhcurpoint)+adh25tick*(5)):.5f}"

              adhVol['body']['bidho1'] = f"{(float(adhcurpoint)-adh25tick*(1)):.5f}"
              adhVol['body']['bidho2'] = f"{(float(adhcurpoint)-adh25tick*(2)):.5f}"
              adhVol['body']['bidho3'] = f"{(float(adhcurpoint)-adh25tick*(3)):.5f}"
              adhVol['body']['bidho4'] = f"{(float(adhcurpoint)-adh25tick*(4)):.5f}"
              adhVol['body']['bidho5'] = f"{(float(adhcurpoint)-adh25tick*(5)):.5f}"
              
              kospiVol['body']['offerho1'] = f"{(float(kospipoint)+kospitick*(1)):.2f}"#str(float(kospipoint)+kospitick*(1)).ljust(6,'0')
              kospiVol['body']['offerho2'] = f"{(float(kospipoint)+kospitick*(2)):.2f}"#str(float(kospipoint)+kospitick*(2)).ljust(6,'0')
              kospiVol['body']['offerho3'] = f"{(float(kospipoint)+kospitick*(3)):.2f}"#str(float(kospipoint)+kospitick*(3)).ljust(6,'0')
              kospiVol['body']['offerho4'] = f"{(float(kospipoint)+kospitick*(4)):.2f}"#str(float(kospipoint)+kospitick*(4)).ljust(6,'0')
              kospiVol['body']['offerho5'] = f"{(float(kospipoint)+kospitick*(5)):.2f}"#str(float(kospipoint)+kospitick*(5)).ljust(6,'0')

              kospiVol['body']['bidho1'] = f"{(float(kospipoint)-kospitick*(1)):.2f}"#str(float(kospipoint)-kospitick*(1)).ljust(6,'0')
              kospiVol['body']['bidho2'] = f"{(float(kospipoint)-kospitick*(2)):.2f}"#str(float(kospipoint)-kospitick*(2)).ljust(6,'0')
              kospiVol['body']['bidho3'] = f"{(float(kospipoint)-kospitick*(3)):.2f}"#str(float(kospipoint)-kospitick*(3)).ljust(6,'0')
              kospiVol['body']['bidho4'] = f"{(float(kospipoint)-kospitick*(4)):.2f}"#str(float(kospipoint)-kospitick*(4)).ljust(6,'0')
              kospiVol['body']['bidho5'] = f"{(float(kospipoint)-kospitick*(5)):.2f}"#str(float(kospipoint)-kospitick*(5)).ljust(6,'0')
            
              nasTsize = get_tsize_by_code(nasCur['header']['tr_key'])
              hsTsize = get_tsize_by_code(hsCur['header']['tr_key'])
              adhTsize = get_tsize_by_code(hsCur['header']['tr_key'])
              kospiTsize = get_tsize_by_code(kospiCur['header']['tr_key'])
              #print(f"Nasdaq Tsize: {nasTsize}")
              #print(f"ADH25 add: {(adh25tick*i):.5f}")
              #print(f"KOSPI tick size : {kospiTsize}")
              await asyncio.sleep(transDelay)
              await raccess.revDataAccess(nasCur["header"]["tr_cd"],1,nasTsize,nasCur["body"])
              await raccess.revDataAccess(nasVol["header"]["tr_cd"],1,nasTsize,nasVol["body"])
              #await asyncio.sleep(transDelay)
                
              await raccess.revDataAccess(hsCur["header"]["tr_cd"],1,hsTsize,hsCur["body"])
              await raccess.revDataAccess(hsVol["header"]["tr_cd"],1,hsTsize,hsVol["body"])    
              #await asyncio.sleep(transDelay)
              
              await raccess.revDataAccess(adhCur["header"]["tr_cd"],1,adhTsize,adhCur["body"])
              await raccess.revDataAccess(adhVol["header"]["tr_cd"],1,adhTsize,adhVol["body"])    
              #await asyncio.sleep(transDelay)
              
              await raccess.revDataAccess(kospiCur["header"]["tr_cd"],1,kospiTsize,kospiCur["body"])
              await raccess.revDataAccess(kospiVol["header"]["tr_cd"],1,kospiTsize,kospiVol["body"])    
              #await asyncio.sleep(transDelay)
          
          nqz24value = nqcurpoint
          hsiv24value = hscurpoint
          adh25value = adhcurpoint
          kospivalue = kospipoint
          print('reverse.....')
          for i in range(10):
              nasVol = json.loads(nasdaqvolumedata)
              nasCur = json.loads(nasdaqtradedata)
              
              hsVol = json.loads(hangsengvolumedata)
              hsCur = json.loads(hangsengtradedata)
              
              adhVol = json.loads(hojudalvolumedata)
              adhCur = json.loads(hojudaltradedata)
              
              kospiVol = json.loads(kospivolumedata)
              kospiCur = json.loads(kospitradedata)
              
              nqcurpoint =str(float(nqz24value)-nqz24tick*i)
              hscurpoint =str(float(hsiv24value)-hsiv24tick*i)
              #adhcurpoint =str(float(adh25value)-adh25tick*i)
              adhcurpoint = f"{(float(adh25value)- adh25tick*i):.5f}"
              if i == 0 :
                kospipoint = f"{(float(kospivalue)- kospitick*i):.2f}"#str(float(kospivalue)+kospitick*i)
              
              nasCur['body']['curpr'] = nqcurpoint.ljust(8,'0');
              hsCur['body']['curpr'] = hscurpoint.ljust(7,'0');
              adhCur['body']['curpr'] = adhcurpoint #.ljust(7,'0');  
              kospiCur['body']['price'] = kospipoint.ljust(6,'0');      
              
              nasVol['body']['offerho1'] = str(float(nqcurpoint)+nqz24tick*(1)).ljust(8,'0')
              nasVol['body']['offerho2'] = str(float(nqcurpoint)+nqz24tick*(2)).ljust(8,'0')
              nasVol['body']['offerho3'] = str(float(nqcurpoint)+nqz24tick*(3)).ljust(8,'0')
              nasVol['body']['offerho4'] = str(float(nqcurpoint)+nqz24tick*(4)).ljust(8,'0')
              nasVol['body']['offerho5'] = str(float(nqcurpoint)+nqz24tick*(5)).ljust(8,'0')

              nasVol['body']['bidho1'] = str(float(nqcurpoint)-nqz24tick*(1)).ljust(8,'0')
              nasVol['body']['bidho2'] = str(float(nqcurpoint)-nqz24tick*(2)).ljust(8,'0')
              nasVol['body']['bidho3'] = str(float(nqcurpoint)-nqz24tick*(3)).ljust(8,'0')
              nasVol['body']['bidho4'] = str(float(nqcurpoint)-nqz24tick*(4)).ljust(8,'0')
              nasVol['body']['bidho5'] = str(float(nqcurpoint)-nqz24tick*(5)).ljust(8,'0')

              hsVol['body']['offerho1'] = str(float(hscurpoint)+hsiv24tick*(1)).ljust(7,'0')
              hsVol['body']['offerho2'] = str(float(hscurpoint)+hsiv24tick*(2)).ljust(7,'0')
              hsVol['body']['offerho3'] = str(float(hscurpoint)+hsiv24tick*(3)).ljust(7,'0')
              hsVol['body']['offerho4'] = str(float(hscurpoint)+hsiv24tick*(4)).ljust(7,'0')
              hsVol['body']['offerho5'] = str(float(hscurpoint)+hsiv24tick*(5)).ljust(7,'0')

              hsVol['body']['bidho1'] = str(float(hscurpoint)-hsiv24tick*(1)).ljust(7,'0')
              hsVol['body']['bidho2'] = str(float(hscurpoint)-hsiv24tick*(2)).ljust(7,'0')
              hsVol['body']['bidho3'] = str(float(hscurpoint)-hsiv24tick*(3)).ljust(7,'0')
              hsVol['body']['bidho4'] = str(float(hscurpoint)-hsiv24tick*(4)).ljust(7,'0')
              hsVol['body']['bidho5'] = str(float(hscurpoint)-hsiv24tick*(5)).ljust(7,'0')
              
              adhVol['body']['offerho1'] = f"{(float(adhcurpoint)+adh25tick*(1)):.5f}"
              adhVol['body']['offerho2'] = f"{(float(adhcurpoint)+adh25tick*(2)):.5f}"
              adhVol['body']['offerho3'] = f"{(float(adhcurpoint)+adh25tick*(3)):.5f}"
              adhVol['body']['offerho4'] = f"{(float(adhcurpoint)+adh25tick*(4)):.5f}"
              adhVol['body']['offerho5'] = f"{(float(adhcurpoint)+adh25tick*(5)):.5f}"

              adhVol['body']['bidho1'] = f"{(float(adhcurpoint)-adh25tick*(1)):.5f}"
              adhVol['body']['bidho2'] = f"{(float(adhcurpoint)-adh25tick*(2)):.5f}"
              adhVol['body']['bidho3'] = f"{(float(adhcurpoint)-adh25tick*(3)):.5f}"
              adhVol['body']['bidho4'] = f"{(float(adhcurpoint)-adh25tick*(4)):.5f}"
              adhVol['body']['bidho5'] = f"{(float(adhcurpoint)-adh25tick*(5)):.5f}"
              
              if i < 5  : 
                kospiVol['body']['offerho1'] = f"{(float(kospipoint)+kospitick*(1)):.2f}"#str(float(kospipoint)+kospitick*(1)).ljust(6,'0')
                kospiVol['body']['offerho2'] = f"{(float(kospipoint)+kospitick*(2)):.2f}"#str(float(kospipoint)+kospitick*(2)).ljust(6,'0')
                kospiVol['body']['offerho3'] = f"{(float(kospipoint)+kospitick*(3)):.2f}"#str(float(kospipoint)+kospitick*(3)).ljust(6,'0')
                kospiVol['body']['offerho4'] = f"{(float(kospipoint)+kospitick*(4)):.2f}"#str(float(kospipoint)+kospitick*(4)).ljust(6,'0')
                kospiVol['body']['offerho5'] = f"{(float(kospipoint)+kospitick*(5)):.2f}"#str(float(kospipoint)+kospitick*(5)).ljust(6,'0')
              else : 
                kospiVol['body']['offerho1'] = f"{(float(kospipoint)+kospitick*(0)):.2f}"#str(float(kospipoint)+kospitick*(1)).ljust(6,'0')
                kospiVol['body']['offerho2'] = f"{(float(kospipoint)+kospitick*(1)):.2f}"#str(float(kospipoint)+kospitick*(2)).ljust(6,'0')
                kospiVol['body']['offerho3'] = f"{(float(kospipoint)+kospitick*(2)):.2f}"#str(float(kospipoint)+kospitick*(3)).ljust(6,'0')
                kospiVol['body']['offerho4'] = f"{(float(kospipoint)+kospitick*(3)):.2f}"#str(float(kospipoint)+kospitick*(4)).ljust(6,'0')
                kospiVol['body']['offerho5'] = f"{(float(kospipoint)+kospitick*(4)):.2f}"#str(float(kospipoint)+kospitick*(5)).ljust(6,'0')  
                    

              kospiVol['body']['bidho1'] = f"{(float(kospipoint)-kospitick*(1)):.2f}"#str(float(kospipoint)-kospitick*(1)).ljust(6,'0')
              kospiVol['body']['bidho2'] = f"{(float(kospipoint)-kospitick*(2)):.2f}"#str(float(kospipoint)-kospitick*(2)).ljust(6,'0')
              kospiVol['body']['bidho3'] = f"{(float(kospipoint)-kospitick*(3)):.2f}"#str(float(kospipoint)-kospitick*(3)).ljust(6,'0')
              kospiVol['body']['bidho4'] = f"{(float(kospipoint)-kospitick*(4)):.2f}"#str(float(kospipoint)-kospitick*(4)).ljust(6,'0')
              kospiVol['body']['bidho5'] = f"{(float(kospipoint)-kospitick*(5)):.2f}"#str(float(kospipoint)-kospitick*(5)).ljust(6,'0')
            
              nasTsize = get_tsize_by_code(nasCur['header']['tr_key'])
              hsTsize = get_tsize_by_code(hsCur['header']['tr_key'])
              adhTsize = get_tsize_by_code(adhCur['header']['tr_key'])
              kospiTsize = get_tsize_by_code(kospiCur['header']['tr_key'])
              #print(f"Nasdaq Tsize: {nasTsize}")
              #print(f"Hangseng Tsize: {hsTsize}")
              
              await asyncio.sleep(transDelay)
              await raccess.revDataAccess(nasCur["header"]["tr_cd"],1,nasTsize,nasCur["body"])
              await raccess.revDataAccess(nasVol["header"]["tr_cd"],1,nasTsize,nasVol["body"])
              #await asyncio.sleep(transDelay)
                
              await raccess.revDataAccess(hsCur["header"]["tr_cd"],1,hsTsize,hsCur["body"])
              await raccess.revDataAccess(hsVol["header"]["tr_cd"],1,hsTsize,hsVol["body"])    
              #await asyncio.sleep(transDelay)
              
              await raccess.revDataAccess(adhCur["header"]["tr_cd"],1,adhTsize,adhCur["body"])
              await raccess.revDataAccess(adhVol["header"]["tr_cd"],1,adhTsize,adhVol["body"])    
              #await asyncio.sleep(transDelay)
              
              await raccess.revDataAccess(kospiCur["header"]["tr_cd"],1,kospiTsize,kospiCur["body"])
              await raccess.revDataAccess(kospiVol["header"]["tr_cd"],1,kospiTsize,kospiVol["body"])    
              #await asyncio.sleep(transDelay)
        
        print('reverse.....')  
        
        '''
        #async with websockets.connect(ws_url, ping_interval=None) as websocket:
        async for websocket in websockets.connect(ws_url, ping_interval=None):    
            try:
                logger.debug('websockets.Connection complete')
                
                for senddata in senddata_list:
                    await websocket.send(senddata)
                    await asyncio.sleep(0.5)
                    print(f"request is :{senddata}")

                while True:
                    data = await websocket.recv()
                    #await asyncio.sleep(0.1)
                    print(f"Recev Command is : {data}")  # 정제되지 않은 Request / Response 출력
                    data = json.loads(data)
                    
                    
                    if "tr_key" in data['header'] :
                        #print(data["header"]["tr_key"])
                        await raccess.revDataAccess(data["header"]["tr_cd"],1,data["body"])
                    
            
            except  websockets.ConnectionClosed:
                logger.debug('websocket connection closed exception!!')            
                continue               
        '''        
    except Exception as error:
        print("lsmainloop() exception!! %s" % error)
        logger.debug('lsmainloop() exception!!')
        print('Connect Again!')
        logger.debug('Connect Again!!')
        time.sleep(0.1)

        # 웹소켓 다시 시작
        # await lsmainLoop()

                    
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
            