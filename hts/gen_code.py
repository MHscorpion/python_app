import sys
import hashlib
import os

def create_encrypted_code_file(ip_string: str, output_file: str = "code.txt"):
    """
    IP 주소 문자열을 SHA-256 해시로 변환하여 파일에 저장합니다.

    :param ip_string: 암호화할 IP 주소 문자열
    :param output_file: 결과를 저장할 파일 이름 (기본값: code.txt)
    """
    if not ip_string:
        print("오류: IP 주소 문자열을 입력해야 합니다.")
        print("사용법: python create_code.py <ip_address>")
        return

    # IP 문자열을 바이트로 인코딩한 후 SHA-256 해시 생성
    hash_object = hashlib.sha256(ip_string.encode('utf-8'))
    # 해시 값을 16진수 문자열로 변환
    hex_digest = hash_object.hexdigest()

    try:
        # 파일을 쓰기 모드('w')로 열고 해시 문자열을 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(hex_digest)
        print(f"암호화된 문자열이 '{output_file}'에 성공적으로 저장되었습니다.")
        print(f"원본 IP: {ip_string}")
        print(f"생성된 해시: {hex_digest}")
    except IOError as e:
        print(f"파일 쓰기 오류가 발생했습니다: {e}")
    except Exception as e:
        print(f"예상치 못한 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    # 명령줄 아규먼트 확인
    if len(sys.argv) < 2:
        print("오류: 실행 시 IP 주소 문자열을 아규먼트로 제공해야 합니다.")
        print("예시: python create_code.py 192.168.1.1")
        sys.exit(1)

    # 첫 번째 명령줄 아규먼트를 IP 문자열로 사용
    ip_address = sys.argv[1]
    create_encrypted_code_file(ip_address)