# 지수선물호가 출력라이브러리
import pymongo
import json
import datetime
import socketio 
#from frealtime_get import logger
#from frealtime_get import sendToServer
import lsfrealtime as freal

presentCodelist={}
rsws = socketio.Client()
trws = socketio.Client()

trade_mongo=pymongo.MongoClient('mongodb+srv://devbox72:PyeCYJ0G72MlcpGU@tradeccs.fo3b3.mongodb.net/tradeccs?retryWrites=true&w=majority')

tradedb=trade_mongo['tradeccs']
rtcodeinfo = tradedb.realtimecodeinfos
prevSellData=0
prevBuyData=0 
accessflag= False

#clServerIP = 'http://13.114.37.25:5353' #'http://18.177.240.35:5353'
#csServerIP = 'http://13.112.58.90:4343' #'http://13.114.12.144:4343'

clServerIP = 'http://localhost:5353' #'http://18.177.240.35:5353'
csServerIP = 'http://localhost:4343' #'http://13.114.12.144:4343'

cpoint_list= []

#relay data ws server event handler
@rsws.event
def connect():
    print("rsws connected!")

@rsws.event
def connect_error(data):
    print("rsws connection failed!")

@rsws.event
def disconnect():
    print("rsws disconnected!")

@rsws.event
def reconnect():
    print("rsws reconnected!")   

#trading ws server event handler
@trws.event
def connect():
    print("rsws connected!")

@trws.event
def connect_error(data):
    print("rsws connection failed!")

@trws.event
def disconnect():
    print("rsws disconnected!")

@trws.event
def reconnect():
    print("rsws reconnected!")       


def add_to_list(key, value):
    global cpoint_list
    cpoint_list.append([key, value])

# key를 기준으로 value 찾기 함수
def find_in_datadict(key):
    return cpoint_list.get

#index, value = find_index_and_value_by_key("name")
def find_index_and_value_by_key(key):
    global cpoint_list
    for index, item in enumerate(cpoint_list):
        if item[0] == key:
            return index, item[1]
    return None, None  # key가 없으면 (None, None) 반환

def update_value_by_index(index, new_value):
    global cpoint_list
    if index is not None and 0 <= index < len(cpoint_list):
        cpoint_list[index][1] = new_value
        return True  # 성공적으로 변경하면 True 반환
    return False  # 유효하지 않은 index이면 False 반환

def setDictData(setData):
    #logger.debug('logger 에 접근 완료')
    global presentCodelist
    presentCodelist=setData
    #print('import list:')
    #print(presentCodelist)

def connetServer():
    if rsws.connected == False :
        print('client_server_ws connect try....')
        rsws.connect(clServerIP,transports=['websocket'],retry=True) 
        #rsws.connect('http://18.180.239.45:5353',retry=True) 
        #rsws.connect('http://localhost:5353',transports=['websocket'],retry=True)
    if trws.connected == False :
        print('trade_server__ws connect try....')
        trws.connect(csServerIP,transports=['websocket'],retry=True) 
        #trws.connect('http://18.180.239.45:4343',retry=True) 
        #trws.connect('http://localhost:4343',transports=['websocket'],retry=True)  

def sendToServer(chName,sendData):
    global rsws
    if rsws.connected == True:
        rsws.emit(chName,sendData)

def sendToTrServer(chName,sendData):
    global trws
    if trws.connected == True:
        trws.emit(chName,sendData)

def chgKospiCode(codeDec):
    prefix_str = codeDec[0:4]
    sub_str = codeDec[4:]
    if sub_str=='W3000' :
        sub_str='W03'
    
    recon_str = prefix_str+sub_str 
    return recon_str

def insertCodeInfo(code):
    current_time = datetime.datetime.now() 
    filter = {'code' : code ,'cpoint' : 0,'ba1point':0,'sa1point':0}
    newvalues = { "$set": {'code':code,'cpoint':0,'ba1point':0,'sa1point':0,'createdAt':current_time } }
    #information.insert_one(record)
    rtcodeinfo.update_one(filter, newvalues,upsert=True)  
    return

def updateCodeInfoCPoint(code, cpoint):
    current_time = datetime.datetime.now() 
    filter = {'code' : code }
    newvalues = { "$set": {'code':code,'cpoint':cpoint,'createdAt':current_time } }
    #information.insert_one(record)
    rtcodeinfo.update_one(filter, newvalues,upsert=True)  
    return

def updateCodeInfoSap1Bap1(code, bap1point,sap1point):
    current_time = datetime.datetime.now() 
    filter = {'code' : code }
    newvalues = { "$set": {'code':code,'ba1point':bap1point,'sa1point':sap1point,'createdAt':current_time } }
    #information.insert_one(record)
    rtcodeinfo.update_one(filter, newvalues,upsert=True)  
    return

def deleteCodeInfo():
    rtcodeinfo.delete_many({})  
    return
    
async def revDataAccess(trcd,count,tsize,data):
    
    try :
        if trcd == "FH0":  # 지수선물호가 tr 일경우의 처리 단계
            #print("#### 지수선물 호가 ####")
            #print(chgKospiCode(data['futcode']))
            stockhoka_futs(trcd,count,data)
            return

        elif trcd == "FC0":  # 지수선물체결 데이터 처리
            #print("#### 지수선물 체결 ####")
            #print(chgKospiCode(data['futcode']))
            stockspurchase_futs(trcd,count,data)  
            return

        elif trcd == "OVH":  # 해외선물옵션호가 tr 일경우의 처리 단계
            #print("#### 해외선물옵션호가 ####")
            stockhoka_overseafut(trcd,count,tsize,data)
            return

        elif trcd == "OVC":  # 해외선물옵션체결 데이터 처리
            #print("#### 해외선물옵션체결 ####")
            stockspurchase_overseafut(trcd,count,tsize,data)
            return   
    
    except Exception as error:
            print('revDataAccess exception()...')

# 지수선물호가 출력라이브러리
def stockhoka_futs(trid,count,data):

    dataDic={} 
    dataDic2={} 
    try:
        dataDic['tr_id']=trid
        dataDic2['tr_id']=trid
        dataDic['code']=chgKospiCode(data['futcode']) #선물 코드 코드 101V09 , NQU26 ...
        dataDic2['code']=chgKospiCode(data['futcode']) #선물 코드 코드 101V09 , NQU26 ...
        dataDic['time']=data['hotime'] #영업시간
        dataDic2['time']=data['hotime'] #영업시간
        
        dataDic2['sap_point1']=data['offerho1'] #매도호가1  sell ask point
        dataDic['sap_point1']=data['offerho1'] #매도호가1  sell ask point
        dataDic['sap_cnt1']=data['offercnt1']  #매도호가1 건수
        dataDic['sap_rcnt1']=data['offerrem1'] #매도호가1 잔량 
        
        dataDic['sap_point2']=data['offerho2']
        dataDic['sap_cnt2']=data['offercnt2'] 
        dataDic['sap_rcnt2']=data['offerrem2']
        
        dataDic['sap_point3']=data['offerho3']
        dataDic['sap_cnt3']=data['offercnt3'] 
        dataDic['sap_rcnt3']=data['offerrem3']
        
        dataDic['sap_point4']=data['offerho4']
        dataDic['sap_cnt4']=data['offercnt4'] 
        dataDic['sap_rcnt4']=data['offerrem4']
        
        dataDic['sap_point5']=data['offerho5']
        dataDic['sap_cnt5']=data['offercnt5'] 
        dataDic['sap_rcnt5']=data['offerrem5']
        
        dataDic2['bap_point1']=data['bidho1']   #매수호가1 buy ask point
        dataDic['bap_point1']=data['bidho1']   #매수호가1 buy ask point
        dataDic['bap_cnt1']=data['bidcnt1']   #매수호가1 건수
        dataDic['bap_rcnt1']=data['bidrem1']   #매수호가1 잔량 
        
        dataDic['bap_point2']=data['bidho2']
        dataDic['bap_cnt2']=data['bidcnt2']
        dataDic['bap_rcnt2']=data['bidrem2']
        
        dataDic['bap_point3']=data['bidho3']
        dataDic['bap_cnt3']=data['bidcnt3']
        dataDic['bap_rcnt3']=data['bidrem3']
        
        dataDic['bap_point4']=data['bidho4']
        dataDic['bap_cnt4']=data['bidcnt4']
        dataDic['bap_rcnt4']=data['bidrem4']
        
        dataDic['bap_point5']=data['bidho5']
        dataDic['bap_cnt5']=data['bidcnt5']
        dataDic['bap_rcnt5']=data['bidrem5']

        '''
        dataDic['total_sap_cnt']=recvvalue[32]   #총매도호가건수  
        dataDic['total_sap_rcnt']=recvvalue[34]  #총매도호가잔량
        dataDic['total_sap_rcnt_icdc']=recvvalue[36]   #총매도호가잔량증감 

        dataDic['total_bap_cnt']=recvvalue[33]   #총매수호가건수  
        dataDic['total_bap_rcnt']=recvvalue[35]  #총매수호가잔량
        dataDic['total_bap_rcnt_icdc']=recvvalue[37]   #총매수호가잔량증감 
        '''
    
        #총매도호가건수  
        sapcntTotal= int(dataDic['sap_cnt1'])+int(dataDic['sap_cnt2'])+int(dataDic['sap_cnt3'])+int(dataDic['sap_cnt4'])+int(dataDic['sap_cnt5'])
        dataDic['total_sap_cnt']=str(sapcntTotal) # 
        #총매도호가잔량
        saprcntTotal=int(dataDic['sap_rcnt1'])+int(dataDic['sap_rcnt2'])+int(dataDic['sap_rcnt3'])+int(dataDic['sap_rcnt4'])+int(dataDic['sap_rcnt5'])
        dataDic['total_sap_rcnt']=str(saprcntTotal)  
        dataDic['total_asp_rcnt_icdc']="0"   #총매도호가잔량증감 

        #총매수호가건수
        bapcntTotal=sapcntTotal= int(dataDic['bap_cnt1'])+int(dataDic['bap_cnt2'])+int(dataDic['bap_cnt3'])+int(dataDic['bap_cnt4'])+int(dataDic['bap_cnt5'])      
        dataDic['total_bap_cnt']=str(bapcntTotal)  
        #총매수호가잔량
        baprcntTotal=int(dataDic['bap_rcnt1'])+int(dataDic['bap_rcnt2'])+int(dataDic['bap_rcnt3'])+int(dataDic['bap_rcnt4'])+int(dataDic['bap_rcnt5'])
        dataDic['total_bap_rcnt']=str(baprcntTotal)  
        dataDic['total_bap_rcnt_icdc']="0"  #총매수호가잔량증감 
        
        jsonData = json.dumps(dataDic)
        jsonData2 = json.dumps(dataDic2)
        #print(jsonData)
        print(f"국내지수 호가수신 {dataDic['code']}: {dataDic['time']}")
        sendToServer('tradevolumn',jsonData)
        #updateCodeInfoSap1Bap1(dataDic['code'],dataDic['bap_point1'] ,dataDic['sap_point1'])
        sendToTrServer('tradevolumn',jsonData2)
        
        
    except Exception as err: 
        freal.logger.debug('국내 지수 선물 호가 데이터 exception error: %s' % err)
    

# 국내 지수선물체결처리 출력라이브러리
def stockspurchase_futs(trid,count,data):
    
    try:
        dataDic={} 
        dataDic2={} 
    
        dataDic['tr_id']=trid
        dataDic['code']= data['futcode']#chgKospiCode(data['futcode']) #선물 코드
        dataDic['time']=data['chetime'] #영업시간
        dataDic2['tr_id']=trid
        dataDic2['code']=data['futcode']#chgKospiCode(data['futcode']) #선물 코드
        dataDic2['time']=data['chetime'] #영업시간
        dataDic['prdy_vrss']=data['change'] #선물 전일 대비 등락포인트
        dataDic['prdy_vrss_sign']=data['sign'] #전일 대비 부호
        dataDic['prdy_ctrt']=data['drate'] #선물 전일 대비 등략률 
        dataDic['cpoint']=data['price'] #선물 체결가
        dataDic2['cpoint']=data['price'] #선물 체결가
        dataDic['mpoint']=data['open'] #선물 시가 
        dataDic['hpoint']=data['high'] #선물 최고가
        dataDic['lpoint']=data['low'] #선물 최저가 
        dataDic['tr_vol']=data['cvolume'] #거래량
        dataDic['sellamt']=data['mdvolume'] #총매도수량
        dataDic['buyamt']=data['msvolume'] #총매수수량
        
        if data['cgubun']=='+':
            dataDic['tr_type']="2"
            dataDic2['tr_type']="2"
        if data['cgubun']=='-':
            dataDic['tr_type']="5"    
            dataDic2['tr_type']="5"    

        #dataDic['tr_type']=data['cgubun'] #매도: 5  매수: 2

        jsonData = json.dumps(dataDic)
        jsonData2 = json.dumps(dataDic2)
        print(f"국내체결수신 {dataDic['code']} :{dataDic['cpoint']} :{dataDic['tr_vol']} : {dataDic['time']}")
        sendToServer('trade',jsonData)
        
        index, prevPoint = find_index_and_value_by_key(dataDic['code']) 
        if index == None :
            add_to_list(dataDic['code'],dataDic2['cpoint']);
            print(f"first 국내 체결서버송신 {dataDic['code']} :{dataDic2['cpoint']} :{dataDic['time']}")
            #updateCodeInfoCPoint(dataDic['code'],dataDic['cpoint'])
            sendToTrServer('trade',jsonData2) #체결서버에 전송
        else:
            #index, prevPoint = find_index_and_value_by_key(dataDic['code']) 
            if prevPoint != dataDic2['cpoint'] :
                #cpoint_list[index][1] = dataDic2['cpoint']
                update_value_by_index(index,dataDic2['cpoint']);
                print(f">>>>> 국내 체결서버송신 {dataDic['code']} :{dataDic2['cpoint']} :{dataDic['time']}")
                #updateCodeInfoCPoint(dataDic['code'],dataDic['cpoint'])
                sendToTrServer('trade',jsonData2) #체결서버에 전송
        #sendToTrServer('trade',jsonData2)

    except Exception as err: 
        freal.logger.debug('국내 지수 선물 체결 데이터 exception error: %s' % err)

def updateMongodb(trid,pValue):   
    global prevSellData
    global prevBuyData
    dataDic={} 
    
    dataDic['tr_id']=trid
    dataDic['code']=pValue[0] #선물 코드
    dataDic['time']=pValue[1] #영업시간
    dataDic['prdy_vrss']=pValue[2] #선물 전일 대비 등락포인트
    dataDic['prdy_vrss_sign']=pValue[3] #전일 대비 부호
    dataDic['prdy_ctrt']=pValue[4] #선물 전일 대비 등략률 
    dataDic['cpoint']=pValue[5] #선물 체결가
    dataDic['mpoint']=pValue[6] #선물 시가 
    dataDic['hpoint']=pValue[7] #선물 최고가
    dataDic['lpoint']=pValue[8] #선물 최저가 
    dataDic['tr_vol']=pValue[9] #거래량
    dataDic['sellamt']=pValue[10] #총매도수량
    dataDic['buyamt']=pValue[11] #총매수수량
    dataDic['tr_type']="0" #매도: 5  매수: 2
    
    curSellData = int(pValue[10])
    curBuyData = int(pValue[11])
    
    if prevSellData == 0:
        dataDic['tr_type']="0"
        prevSellData =  curSellData
        prevBuyData =  curBuyData
    else: 
        if prevSellData < curSellData :
            prevSellData =  curSellData
            dataDic['tr_type']="5"
        
        if prevBuyData < curBuyData :
            prevBuyData =  curBuyData
            dataDic['tr_type']="2"    
               
    
    jsonData = json.dumps(dataDic)
    #print(jsonData)
    #print(f"체결수신 {dataDic['code']}")
    print(f"국내체결수신 {dataDic['code']} :{dataDic['cpoint']} : {dataDic['time']}")
    #sendToServer('trade',jsonData)
    
    '''    
    current_time = datetime.datetime.now() 
    filter = {'tr_id' : trid,'tr_key':dataDic['code']}
    newvalues = { "$set": {'name':'korea','update': current_time.strftime('%Y-%m-%d %H:%M:%S'), 'data':jsonData ,'trader':"KO_HKS" } }
    #information.insert_one(record)
    futuretrade.update_one(filter, newvalues,upsert=True)  
    '''
    
    
    '''
    #종목 현재가 테이블 업데이트 
    try:
        index = list(presentCodelist.keys()).index(pValue[0])
    except Exception as err: 
        index = -1
        print('not find code')
        print(err)
    
    if index != -1 :
        curPrice =  pValue[5].replace('.','')
        if presentCodelist[pValue[0]] != curPrice :  # 현재가가 변경되었을때만 디비에 저장 
            #print(f"{presentCodelist[index][1]}:{curPrice}")
            print( f"{index}:{pValue[0]}:{pValue[5]}: ==>{presentCodelist[pValue[0]]}" )  
            presentCodelist[pValue[0]]=curPrice
            filter2 = {'code' : pValue[0]}
            newvalues2 = { "$set": {'tr_id':'fpresent','price':curPrice,'expiredate': 'NONE','update': current_time.strftime('%H:%M:%S') } }
            futurePresentTable.update_one(filter2, newvalues2,upsert=True)     
    '''        

def stockhoka_overseafut(trid,count,tsize,data):
    
    dataDic={} 
    dataDic2={} 
    try:
        dataDic['tr_id']=trid
        dataDic['code']=data['symbol']  #해외선물옵션 코드 101V09 , NQU26 ...
        dataDic['time']=data['hotime']  #수신시간

        dataDic2['tr_id']=trid
        dataDic2['code']=data['symbol']  #해외선물옵션 코드 101V09 , NQU26 ...
        dataDic2['time']=data['hotime']  #수신시간

        dataDic2['sap_point1']=data['offerho1'] #매도호가1  sell ask point   
        dataDic['sap_point1']=data['offerho1'] #매도호가1  sell ask point
        dataDic['sap_cnt1']=data['offerno1']  #매도호가1 건수
        dataDic['sap_rcnt1']=data['offerrem1'] #매도호가1 잔량 
        dataDic['sap_point2']=data['offerho2']
        dataDic['sap_cnt2']=data['offerno2'] 
        dataDic['sap_rcnt2']=data['offerrem2']
        dataDic['sap_point3']=data['offerho3']
        dataDic['sap_cnt3']=data['offerno3'] 
        dataDic['sap_rcnt3']=data['offerrem3']
        dataDic['sap_point4']=data['offerho4']
        dataDic['sap_cnt4']=data['offerno3'] 
        dataDic['sap_rcnt4']=data['offerrem4']
        dataDic['sap_point5']=data['offerho5']
        dataDic['sap_cnt5']=data['offerno3'] 
        dataDic['sap_rcnt5']=data['offerrem5']
        
        dataDic2['bap_point1']=data['bidho1']   #매수호가1 buy ask point
        dataDic['bap_point1']=data['bidho1']   #매수호가1 buy ask point
        dataDic['bap_cnt1']=data['bidno1']   #매수호가1 건수
        dataDic['bap_rcnt1']=data['bidrem1']   #매수호가1 잔량 
        dataDic['bap_point2']=data['bidho2']
        dataDic['bap_cnt2']=data['bidno2']
        dataDic['bap_rcnt2']=data['bidrem2']
        dataDic['bap_point3']=data['bidho3']
        dataDic['bap_cnt3']=data['bidno3']
        dataDic['bap_rcnt3']=data['bidrem3']
        dataDic['bap_point4']=data['bidho4']
        dataDic['bap_cnt4']=data['bidno4']
        dataDic['bap_rcnt4']=data['bidrem4']
        dataDic['bap_point5']=data['bidho5']
        dataDic['bap_cnt5']=data['bidno5']
        dataDic['bap_rcnt5']=data['bidrem5']

        
        if tsize == 1.0 and dataDic2['sap_point1'].endswith(".0") : #or dataDic['code'] == 'HMHF25' or dataDic['code'] == 'YMH25' :
            dataDic2['sap_point1']=data['offerho1'].replace(".0","") #매도호가1
            dataDic2['bap_point1']=data['bidho1'].replace(".0","") #매수호가1
            #print(dataDic2['sap_point1'])
            #print(dataDic2['bap_point1'])
            dataDic['sap_point1']=data['offerho1'].replace(".0","") #매도호가1
            dataDic['bap_point1']=data['bidho1'].replace(".0","") #매수호가1
            dataDic['sap_point2']=data['offerho2'].replace(".0","") 
            dataDic['bap_point2']=data['bidho2'].replace(".0","") 
            dataDic['sap_point3']=data['offerho3'].replace(".0","") 
            dataDic['bap_point3']=data['bidho3'].replace(".0","") 
            dataDic['sap_point4']=data['offerho4'].replace(".0","") 
            dataDic['bap_point4']=data['bidho4'].replace(".0","") 
            dataDic['sap_point5']=data['offerho5'].replace(".0","") 
            dataDic['bap_point5']=data['bidho5'].replace(".0","") 
        #if dataDic['code'] == 'NQU24' :
        #    print(dataDic['time']+" --> " +dataDic['sap_point1']+"|"+dataDic['sap_point2']+"|"+dataDic['sap_point3']+"|"+dataDic['sap_point4']+"|"+dataDic['sap_point5']+"----------")
    
    
        #총매도호가건수  
        sapcntTotal= int(dataDic['sap_cnt1'])+int(dataDic['sap_cnt2'])+int(dataDic['sap_cnt3'])+int(dataDic['sap_cnt4'])+int(dataDic['sap_cnt5'])
        dataDic['total_sap_cnt']=str(sapcntTotal) # 
        #총매도호가잔량
        saprcntTotal=int(dataDic['sap_rcnt1'])+int(dataDic['sap_rcnt2'])+int(dataDic['sap_rcnt3'])+int(dataDic['sap_rcnt4'])+int(dataDic['sap_rcnt5'])
        dataDic['total_sap_rcnt']=str(saprcntTotal)  
        dataDic['total_asp_rcnt_icdc']="0"   #총매도호가잔량증감 

        #총매수호가건수
        bapcntTotal=sapcntTotal= int(dataDic['bap_cnt1'])+int(dataDic['bap_cnt2'])+int(dataDic['bap_cnt3'])+int(dataDic['bap_cnt4'])+int(dataDic['bap_cnt5'])      
        dataDic['total_bap_cnt']=str(bapcntTotal)  
        #총매수호가잔량
        baprcntTotal=int(dataDic['bap_rcnt1'])+int(dataDic['bap_rcnt2'])+int(dataDic['bap_rcnt3'])+int(dataDic['bap_rcnt4'])+int(dataDic['bap_rcnt5'])
        dataDic['total_bap_rcnt']=str(baprcntTotal)  
        dataDic['total_bap_rcnt_icdc']="0"   #총매수호가잔량증감 
        jsonData = json.dumps(dataDic)
        jsonData2 = json.dumps(dataDic2)
        #print(jsonData)
        #print(f"해외지수 호가수신 {dataDic['code']}: {dataDic['time']}")
        sendToServer('tradevolumn',jsonData)
        #updateCodeInfoSap1Bap1(dataDic['code'],dataDic['bap_point1'] ,dataDic['sap_point1'])
        sendToTrServer('tradevolumn',jsonData2)
        '''
        current_time = datetime.datetime.now() 
        filter = {'tr_id' : trid,'tr_key':dataDic['code']}
        newvalues = { "$set": {'name':'oversea','update': current_time.strftime('%Y-%m-%d %H:%M:%S'), 'data':jsonData ,'trader':"KO_HKS" } }
        futurevolume.update_one(filter, newvalues,upsert=True)
        '''
    
    except Exception as err: 
        freal.logger.debug('해외 지수 선물 호가 데이터 exception error: %s' % err)

    

# 해외선물옵션체결처리 출력라이브러리
def stockspurchase_overseafut(trid,count,tsize,data):
    try:
        dataDic={} 
        dataDic2={} 
    
        dataDic2['tr_id']=trid
        dataDic2['code']=data['symbol'] #선물 코드
        dataDic2['time']=data['kortm'] #영업시간

        dataDic['tr_id']=trid
        dataDic['code']=data['symbol'] #선물 코드
        dataDic['time']=data['kortm'] #영업시간

        dataDic['prdy_vrss']=data['ydiffpr'] #선물 전일 대비 등락포인트
        dataDic['prdy_vrss_sign']=data['ydiffSign'] #전일 대비 부호
        dataDic['prdy_ctrt']=data['chgrate'] #선물 전일 대비 등략률 
        
        dataDic['cpoint']=data['curpr'] #선물 체결가
        dataDic2['cpoint']=data['curpr'] #선물 체결가
        
        dataDic['mpoint']=data['open'] #선물 시가 
        dataDic['hpoint']=data['high'] #선물 최고가
        dataDic['lpoint']=data['low'] #선물 최저가 
        dataDic['tr_vol']=data['trdq'] #거래량
        dataDic['sellamt']=data['mdvolume'] #총매도수량
        dataDic['buyamt']=data['msvolume'] #총매수수량

        if data['cgubun']=='+':
            dataDic['tr_type']="2"
            dataDic2['tr_type']="2"
        if data['cgubun']=='-':
            dataDic['tr_type']="5"    
            dataDic2['tr_type']="5"    
        
        if tsize == 1.0 and dataDic2['cpoint'].endswith(".0") :#or dataDic['code'] == 'HMHF25' or dataDic['code'] == 'YMH25' :
            dataDic['cpoint']=data['curpr'].replace(".0","")  #선물 체결가
            dataDic2['cpoint']=data['curpr'].replace(".0","")  #선물 체결가
            dataDic['mpoint']=data['open'].replace(".0","")  #선물 시가 
            dataDic['hpoint']=data['high'].replace(".0","")  #선물 최고가
            dataDic['lpoint']=data['low'].replace(".0","")  #선물 최저가 
        #dataDic['tr_type']=data['cgubun'] #매도: 5  매수: 2

        #codeInfo = freal.find_by_code(dataDic2['code'])
        #if codeInfo != None :
        #    print(f"소숫점 {codeInfo['code']} , {codeInfo['outrpnt']}")
            
        jsonData = json.dumps(dataDic)
        jsonData2 = json.dumps(dataDic2)
        print(f"해외체결수신 {dataDic['code']} :{dataDic['cpoint']} :{dataDic['tr_vol']} : {dataDic['time']}")
        sendToServer('trade',jsonData) #중계서버에 전송
        
        index, prevPoint = find_index_and_value_by_key(dataDic['code']) 
        if index == None :
            add_to_list(dataDic['code'],dataDic2['cpoint']);
            print(f"first 해외 체결서버송신 {dataDic['code']} :{dataDic2['cpoint']} :{dataDic['time']}")
            #updateCodeInfoCPoint(dataDic['code'],dataDic['cpoint'])
            sendToTrServer('trade',jsonData2) #체결서버에 전송
        else:
            #index, prevPoint = find_index_and_value_by_key(dataDic['code']) 
            if prevPoint != dataDic2['cpoint'] :
                #cpoint_list[index][1] = dataDic2['cpoint']
                update_value_by_index(index,dataDic2['cpoint']);
                print(f">>>>> 해외 체결서버송신 {dataDic['code']} :{dataDic2['cpoint']} :{dataDic['time']}")
                #updateCodeInfoCPoint(dataDic['code'],dataDic['cpoint'])
                sendToTrServer('trade',jsonData2) #체결서버에 전송
            
        
        #sendToTrServer('trade',jsonData2)

    except Exception as err: 
        freal.logger.debug('해외 지수 선물 체결 데이터 exception error: %s' % err)
        
def updateOverseaMongodb(trid,pValue):
    dataDic={} 
    dataDic['tr_id']=trid
    '''
    dataDic['code']=pValue[0] #선물 코드
    dataDic['time']=pValue[8][0:6] #영업시간 <- 체결시간
    dataDic['prdy_vrss']=pValue[12] #선물 전일 대비 등락포인트
    dataDic['prdy_vrss_sign']=pValue[18] #전일 대비 부호
    dataDic['prdy_ctrt']=pValue[13] #선물 전일 대비 등략률 
    dataDic['cpoint']=pValue[10] #선물 체결가
    dataDic['mpoint']=pValue[14] #선물 시가 
    dataDic['hpoint']=pValue[15] #선물 최고가
    dataDic['lpoint']=pValue[16] #선물 최저가 
    dataDic['tr_vol']=pValue[11] #최종거래량
    dataDic['tr_type']=pValue[19] #매도: 5  매수: 2
    '''
    dataDic['code']=pValue[0] #선물 코드
    dataDic['time']=pValue[1][0:6] #영업시간 <- 체결시간
    dataDic['prdy_vrss']=pValue[2] #선물 전일 대비 등락포인트
    dataDic['prdy_vrss_sign']=pValue[3] #전일 대비 부호
    dataDic['prdy_ctrt']=pValue[4] #선물 전일 대비 등략률 
    dataDic['cpoint']=pValue[5] #선물 체결가
    dataDic['mpoint']=pValue[6] #선물 시가 
    dataDic['hpoint']=pValue[7] #선물 최고가
    dataDic['lpoint']=pValue[8] #선물 최저가 
    dataDic['tr_vol']=pValue[9] #최종거래량
    dataDic['tr_type']=pValue[10] #매도: 5  매수: 2

    jsonData = json.dumps(dataDic)
   
    #print(jsonData)
    print(f"해외체결수신 {dataDic['code']} :{dataDic['cpoint']} : {dataDic['time']}")
    #sendToServer('trade',jsonData)
    '''
    current_time = datetime.datetime.now() 
    filter = {'tr_id' : trid,'tr_key':dataDic['code']}
    newvalues = { "$set": {'name':'oversea','update': current_time.strftime('%Y-%m-%d %H:%M:%S'), 'data':jsonData ,'trader':"KO_HKS" } }
    futuretrade.update_one(filter, newvalues,upsert=True)    
    '''
    #print(presentCodelist)
    '''
    #종목 현재가 테이블 업데이트 
    
    try:
        index = list(presentCodelist.keys()).index(pValue[0])
    except Exception as err: 
        index = -1
        print('not find code')
        print(err)
    
    if index != -1 :
        curPrice =  pValue[10] #.replace('.','')
        if presentCodelist[pValue[0]] != curPrice :  # 현재가가 변경되었을때만 디비에 저장 
            #print(f"{presentCodelist[index][1]}:{curPrice}")
            print( f"{index}:{pValue[0]}:{pValue[10]}: ==>{presentCodelist[pValue[0]]}" )
            presentCodelist[pValue[0]]=curPrice
            filter2 = {'code' : pValue[0]}
            newvalues2 = { "$set": {'tr_id':'fpresent','price':curPrice,'expiredate': 'NONE','update': current_time.strftime('%H:%M:%S') } }
            futurePresentTable.update_one(filter2, newvalues2,upsert=True)   
            #newData = {'tr_id':'fpresent','code': pValue[0],'price':curPrice,'expiredate': 'NONE','update': current_time.strftime('%H:%M:%S') }
            #futureDemoPresentTable.insert_one(newData)   
    '''