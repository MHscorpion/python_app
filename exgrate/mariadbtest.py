import mysql.connector
import matplotlib.pyplot as plt
import datetime
import random

def get_tank_data_and_plot():
    """
    MariaDB의 t_tank_data 테이블에서 데이터를 조회하거나,
    접속 실패 시 임의의 데이터를 생성하여 그래프를 그립니다.
    """
    # MariaDB 연결 설정 (본인의 DB 정보로 변경하세요!)
    db_config = {
        'host': '192.168.219.124',      # 예: 'localhost', '127.0.0.1', 또는 서버 IP
        'user': 'root',      # 예: 'root', 'xray_admin'
        'password': '1234', # 본인의 DB 비밀번호
        'database': 'xray_monitor_test' # 사용할 데이터베이스 이름
    }

    conn = None
    cursor = None
    data_for_plot = []
    plot_title = "X-ray Data Trends"

    try:
        # MariaDB에 연결 시도
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print("MariaDB에 성공적으로 연결되었습니다. 데이터를 조회합니다.")
            cursor = conn.cursor(dictionary=True)

            sql_query = """
            SELECT
                date_time,
                CAST(exp_count AS SIGNED) as exp_count_int, -- 정수형으로 변환 시도
                CAST(temp AS DECIMAL(5,2)) as temp_decimal   -- 실수형으로 변환 시도
            FROM t_tank_data
            WHERE date_time IS NOT NULL AND exp_count IS NOT NULL AND temp IS NOT NULL
            ORDER BY date_time ASC;
            """
            cursor.execute(sql_query)
            db_records = cursor.fetchall()

            if db_records:
                print(f"총 {len(db_records)}개의 실제 데이터가 조회되었습니다.")
                # 그래프를 위한 데이터 가공
                for record in db_records:
                    try:
                        # date_time을 datetime 객체로 파싱 시도 (다양한 포맷 고려)
                        dt_obj = None
                        if isinstance(record['date_time'], datetime.datetime):
                            dt_obj = record['date_time']
                        elif isinstance(record['date_time'], str):
                            # 일반적인 datetime 문자열 포맷 시도 (YYYY-MM-DD HH:MM:SS)
                            try:
                                dt_obj = datetime.datetime.strptime(record['date_time'], '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                # 다른 포맷 시도 (YYYYMMDDHHMMSS)
                                try:
                                    dt_obj = datetime.datetime.strptime(record['date_time'], '%Y%m%d%H%M%S')
                                except ValueError:
                                    pass # 파싱 실패, None으로 남김

                        if dt_obj and record['exp_count_int'] is not None and record['temp_decimal'] is not None:
                            data_for_plot.append({
                                'time': dt_obj,
                                'exp_count': record['exp_count_int'],
                                'temp': record['temp_decimal']
                            })
                        else:
                            print(f"경고: 데이터 파싱 실패 또는 NULL 값 포함 - {record}")
                    except Exception as e:
                        print(f"데이터 레코드 처리 중 오류 발생: {record} - {e}")
                plot_title = "실제 X-ray 데이터 트렌드 (조회 성공)"
            else:
                print("t_tank_data 테이블에 데이터가 없습니다. 임의 데이터를 생성합니다.")
                data_for_plot = generate_random_data()
                plot_title = "임의 생성된 X-ray 데이터 트렌드 (데이터 없음)"
        else:
            # 연결에 실패했으나 예외가 발생하지 않은 경우 (흔치 않음)
            print("MariaDB 연결 상태가 올바르지 않습니다. 임의 데이터를 생성합니다.")
            data_for_plot = generate_random_data()
            plot_title = "임의 생성된 X-ray 데이터 트렌드 (DB 연결 오류)"

    except mysql.connector.Error as err:
        print(f"MariaDB 연결 또는 쿼리 오류 발생: {err}")
        print("DB 연결에 실패했습니다. 임의 데이터를 생성합니다.")
        data_for_plot = generate_random_data()
        plot_title = "임의 생성된 X-ray 데이터 트렌드 (DB 연결 실패)"
    except Exception as e:
        print(f"알 수 없는 오류 발생: {e}")
        print("오류로 인해 임의 데이터를 생성합니다.")
        data_for_plot = generate_random_data()
        plot_title = "임의 생성된 X-ray 데이터 트렌드 (예상치 못한 오류)"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("MariaDB 연결이 종료되었습니다.")

    # 그래프 그리기
    if data_for_plot:
        plot_data(data_for_plot, plot_title)
    else:
        print("그래프를 그릴 데이터가 없습니다.")

def generate_random_data(num_points=20):
    """
    임의의 시간과 값을 가진 데이터를 생성합니다.
    """
    print(f"임의 데이터 {num_points}개를 생성합니다.")
    random_data = []
    # 현재 시간으로부터 역순으로 데이터를 생성하여 최근 데이터처럼 보이게 함
    end_time = datetime.datetime.now()
    for i in range(num_points):
        # 시간은 약 10분 간격으로 과거로 이동
        time_point = end_time - datetime.timedelta(minutes=(num_points - 1 - i) * 10)
        
        # exp_count는 100에서 500 사이의 임의 정수
        exp_count = random.randint(100, 500)
        
        # temp는 30.0에서 60.0 사이의 임의 실수 (소수점 2자리)
        temp = round(random.uniform(30.0, 60.0), 2)
        
        random_data.append({'time': time_point, 'exp_count': exp_count, 'temp': temp})
    
    return random_data

def plot_data(data, title):
    """
    제공된 데이터를 사용하여 그래프를 그립니다.
    """
    times = [d['time'] for d in data]
    exp_counts = [d['exp_count'] for d in data]
    temps = [d['temp'] for d in data]

    plt.figure(figsize=(12, 6)) # 그래프 크기 설정

    # 첫 번째 y축 (exp_count)
    ax1 = plt.subplot(111)
    ax1.plot(times, exp_counts, marker='o', linestyle='-', color='b', label='Exposure Count')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Exposure Count', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.grid(True, linestyle='--', alpha=0.6)

    # 두 번째 y축 (temp)
    ax2 = ax1.twinx() # x축을 공유하는 두 번째 y축 생성
    ax2.plot(times, temps, marker='x', linestyle='--', color='r', label='Temperature (°C)')
    ax2.set_ylabel('Temperature (°C)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')

    # X축 날짜/시간 포맷 설정
    plt.gcf().autofmt_xdate() # 날짜 레이블 겹치지 않게 자동 포맷

    plt.title(title)
    plt.legend(loc='upper left') # 범례 표시
    ax2.legend(loc='upper right')

    plt.tight_layout() # 레이아웃 자동 조정
    plt.show()

# 스크립트 실행 시 함수 호출
if __name__ == "__main__":
    get_tank_data_and_plot()