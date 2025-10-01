from pymongo import MongoClient

# MongoDB 연결 정보
# 로컬호스트에 기본 포트(27017)로 연결
# 만약 원격 서버에 연결하려면, 'mongodb://호스트IP:포트/' 형식으로 변경
client = MongoClient('mongodb://deveng:98*419@localhost:27017/')

# 'testdb'라는 데이터베이스에 접속합니다.
# 데이터베이스가 없으면 자동으로 생성됩니다.
db = client['testdb']

# 'users'라는 컬렉션에 접속합니다.
# 컬렉션이 없으면 자동으로 생성됩니다.
collection = db['users']

print("MongoDB에 성공적으로 연결되었습니다.")

# 1. 데이터 삽입 (Create)
print("\n1. 데이터 삽입:")
user_data = {
    "name": "홍길동",
    "age": 30,
    "city": "서울"
}
insert_result = collection.insert_one(user_data)
print(f"데이터 삽입 성공: _id = {insert_result.inserted_id}")

# 여러 개의 문서 삽입
multiple_users = [
    {"name": "김철수", "age": 25, "city": "부산"},
    {"name": "이영희", "age": 35, "city": "대구"}
]
collection.insert_many(multiple_users)
print("여러 데이터 삽입 성공")

# 2. 데이터 조회 (Read)
print("\n2. 데이터 조회:")
# 모든 문서 조회
all_users = collection.find()
print("모든 사용자:")
for user in all_users:
    print(user)

# 조건에 맞는 문서 조회 (예: 나이가 30인 사용자)
query = {"age": 30}
found_user = collection.find_one(query)
print("\n나이가 30인 사용자:")
if found_user:
    print(found_user)
else:
    print("해당 사용자를 찾을 수 없습니다.")

# 3. 데이터 업데이트 (Update)
print("\n3. 데이터 업데이트:")
# 나이가 30인 사용자의 city를 '광주'로 변경
update_query = {"age": 30}
new_values = {"$set": {"city": "광주"}}
update_result = collection.update_one(update_query, new_values)
print(f"{update_result.modified_count}개의 문서가 업데이트되었습니다.")

# 4. 데이터 삭제 (Delete)
print("\n4. 데이터 삭제:")
# 나이가 25인 사용자 삭제
delete_query = {"age": 25}
delete_result = collection.delete_one(delete_query)
print(f"{delete_result.deleted_count}개의 문서가 삭제되었습니다.")

# 연결 종료
client.close()
print("\nMongoDB 연결이 종료되었습니다.")