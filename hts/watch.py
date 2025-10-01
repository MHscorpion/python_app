from pymongo import MongoClient
import time

# MongoDB 연결 정보
#client = MongoClient('mongodb://localhost:27017/')
client = MongoClient('mongodb://deveng:98*419@localhost:27017/')
db = client['testdb']
collection = db['users']

print("MongoDB에 성공적으로 연결되었습니다.")

def run_watch_test():
    """
    Watches for changes in the 'users' collection for 20 seconds.
    """
    print("\n[MongoDB Watch 기능 테스트 시작]")
    print("20초 동안 'users' 컬렉션의 변경 사항을 감시합니다...")

    # watch() 메소드를 사용하여 변경 스트림을 엽니다.
    # fullDocument='updateLookup' 옵션은 업데이트된 문서의 전체 내용을 가져옵니다.
    with collection.watch(full_document='updateLookup') as stream:
        start_time = time.time()
        
        # 20초 동안 변경 사항을 감시
        while time.time() - start_time < 20:
            change = stream.try_next()
            if change:
                print("\n[변경 감지!] 변경 유형:", change['operationType'])
                if change['operationType'] == 'insert':
                    print("새로운 문서:", change['fullDocument'])
                elif change['operationType'] == 'update':
                    print("변경 전 문서:", change['fullDocument'])
                    print("변경 사항:", change['updateDescription']['updatedFields'])
                elif change['operationType'] == 'delete':
                    print("삭제된 문서 ID:", change['documentKey']['_id'])
            
            # 1초마다 확인
            time.sleep(1)

    print("\n[MongoDB Watch 기능 테스트 종료]")

# ---- 주요 로직 ----
try:
    # 1. 기존 데이터 삭제 (테스트 환경 초기화)
    print("기존 'users' 컬렉션 데이터 삭제...")
    collection.delete_many({})

    # 2. Watch 기능 테스트를 별도의 쓰레드나 프로세스로 실행
    # 여기서는 간단히 순차적으로 진행
    
    # 3. 데이터 삽입 (Watch에서 감지될 변화)
    print("\n데이터 삽입 (10초 대기 후):")
    time.sleep(10) # 10초 대기 후 변경 시작
    collection.insert_one({"name": "새로운유저", "age": 20})
    print("새로운유저 삽입 완료.")

    # 4. 데이터 업데이트 (Watch에서 감지될 변화)
    print("\n데이터 업데이트:")
    collection.update_one({"name": "새로운유저"}, {"$set": {"age": 21}})
    print("새로운유저 나이 업데이트 완료.")

    # 5. Watch 기능 실행
    run_watch_test()
    
finally:
    client.close()
    print("\nMongoDB 연결이 종료되었습니다.")