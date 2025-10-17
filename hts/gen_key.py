import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# 🚨 주의: 이 키와 IV(초기화 벡터)는 실제 환경에서 안전하게 관리되어야 합니다.
# 예제에서는 고정 값을 사용합니다.
ENCRYPTION_KEY = b'af5a47919cf4c4666761809302f9e274' #b'ThisIsASecretKeyForAES256Bit!!!!'  # 32바이트 (256비트) 키
INITIALIZATION_VECTOR = b'16ByteIVForAES!!'             # 16바이트 IV (CBC 모드 필수)
OUTPUT_FILE = "ebase.bin"

def create_and_encrypt(ip_string: str, key: bytes, iv: bytes, output_file: str = OUTPUT_FILE):
    """
    IP 주소 문자열을 지정된 키로 AES 암호화하여 파일에 저장합니다.
    """
    if not ip_string:
        print("오류: IP 주소 문자열을 입력해야 합니다.")
        return

    # 1. 패딩 (블록 크기에 맞추기)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(ip_string.encode('utf-8')) + padder.finalize()

    # 2. 암호화 객체 생성 및 실행
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # 3. 파일 저장 (암호화된 바이트 그대로 저장)
    try:
        with open(output_file, 'wb') as f:
            f.write(encrypted_data)
        
        print("-" * 50)
        print(f"✅ 암호화 성공: IP가 '{output_file}'에 저장되었습니다.")
        print(f"원본 IP (기준): {ip_string}")
        print(f"저장된 바이트 크기: {len(encrypted_data)}")
        print("-" * 50)

    except IOError as e:
        print(f"❌ 파일 쓰기 오류가 발생했습니다: {e}")


def decrypt_and_read(key: bytes, iv: bytes, input_file: str = OUTPUT_FILE) -> str | None:
    """
    파일에서 암호화된 데이터를 읽어 지정된 키로 복호화하고 IP 주소 문자열을 반환합니다.
    """
    try:
        # 1. 파일 읽기
        with open(input_file, 'rb') as f:
            encrypted_data = f.read()

        # 2. 복호화 객체 생성 및 실행
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

        # 3. 패딩 제거
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
        
        # 4. 바이트를 문자열로 디코딩
        decrypted_ip_string = decrypted_data.decode('utf-8')
        
        print("-" * 50)
        print(f"✅ 복호화 성공: IP 주소가 복원되었습니다.")
        print(f"복원된 IP: {decrypted_ip_string}")
        print("-" * 50)
        
        return decrypted_ip_string

    except FileNotFoundError:
        print(f"❌ 오류: 입력 파일 '{input_file}'을 찾을 수 없습니다.")
        return None
    except Exception as e:
        # 키/IV가 잘못되었거나 데이터가 손상되면 발생할 수 있습니다.
        print(f"❌ 복호화 오류가 발생했습니다 (키/IV 불일치 가능성): {e}")
        return None

# --- 실행 예시 ---
if __name__ == "__main__":
    
    # 1. 암호화 및 파일 저장
    target_ip = "http://13.230.135.40:9090/api"
    create_and_encrypt(target_ip, ENCRYPTION_KEY, INITIALIZATION_VECTOR)

    # 2. 파일에서 읽어 복호화 및 IP 복원
    restored_ip = decrypt_and_read(ENCRYPTION_KEY, INITIALIZATION_VECTOR)
    
    # 3. 잘못된 키로 복호화 시도 (오류 발생 확인)
    print("\n--- 잘못된 키로 복호화 시도 ---")
    WRONG_KEY = b'WrongKeyForAES256BitPlease!'
    decrypt_and_read(WRONG_KEY, INITIALIZATION_VECTOR)
    
    # 4. 테스트 파일 정리 (선택 사항)
    # os.remove(OUTPUT_FILE)