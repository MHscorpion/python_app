import hashlib
import sys
import os
import requests # 공인 IP 주소를 가져오기 위해 requests 모듈 추가

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

def create_encrypted_code_file(ip_string: str, output_file: str = "code.txt"):
    """
    IP 주소 문자열을 SHA-256 해시로 변환하여 파일에 저장합니다.
    """
    if not ip_string:
        print("오류: IP 주소 문자열을 입력해야 합니다.")
        return

    # IP 문자열을 바이트로 인코딩한 후 SHA-256 해시 생성
    hash_object = hashlib.sha256(ip_string.encode('utf-8'))
    # 해시 값을 16진수 문자열로 변환
    hex_digest = hash_object.hexdigest()

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(hex_digest)
        print("-" * 35)
        print(f"✅ 암호화된 문자열이 '{output_file}'에 성공적으로 저장되었습니다.")
        print(f"원본 IP (기준): {ip_string}")
        print(f"생성된 해시: {hex_digest}")
        print("-" * 35)
    except IOError as e:
        print(f"❌ 파일 쓰기 오류가 발생했습니다: {e}")

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("오류: 실행 시 기준 IP 주소 문자열을 아규먼트로 제공해야 합니다.")
        print("사용법: python create_code.py <기준_ip_address>")
        sys.exit(1)

    # 1. 기준 IP 주소로 해시 파일 생성
    initial_ip = sys.argv[1]
    create_encrypted_code_file(initial_ip)

    # 2. 현재 공인 IP를 가져와서 검증 시작
    current_public_ip = get_public_ip()
    
    if current_public_ip:
        read_and_verify_code_file(current_public_ip)
    else:
        print("공인 IP를 가져오지 못하여 검증을 건너뜜.")