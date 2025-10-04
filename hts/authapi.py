import os
import requests
import json
from datetime import date, timedelta


def get_exchangeRate():
    #global api_url
    # 오늘 날짜
    today = date.today()

    # 하루 전 날짜
    yesterday = today - timedelta(days=1)

    # "YYYYMMDD" 형식으로 변환
    yesterday_str = today.strftime('%Y%m%d')
    print(yesterday_str)

    try:
        print('------ 환률 조회 요청 ------')          
        headers = {"content-type": "application/json"}
        paramData = {"authkey": "Yge3eVr5q6ZwH571fTkCa4EqLKOpjI1T",
                     "searchdate":yesterday_str,
                "data": 'AP01',
                }
        PATH = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON"
        URL = f"{PATH}"
        res = requests.get(URL,params=paramData)
        
        jsonData = res.json() 
        
        for zone in jsonData:
            print(zone["cur_nm"], ":", zone["cur_unit"], ":",zone["deal_bas_r"],":",zone["deal_bas_r"].replace(',',''))
            '''
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
        print('------ 환률 조회 완료 ------') 
    except Exception as e: 
        print(e)

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

if __name__ == "__main__":
    # Example usage
    file_name = "code.txt"
    hocode_from_file = ""

    try:
        hocode_from_file = read_hocode_from_file(file_name)
    except FileNotFoundError as e:
        print(e)
        exit()
    
    if not hocode_from_file:
        print(f"오류: '{file_name}' 파일이 비어 있습니다.")
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
    else:
        print("Failed to retrieve agent information.")
    
    get_exchangeRate()