#!/bin/bash

# 파이썬3 인터프리터 경로
PYTHON_INTERPRETER="python3"

# 스크립트 파일명
SCRIPT_NAME="lsvrealtime.py"

# 스크립트가 위치한 디렉터리 경로 (스크립트 파일과 동일한 위치에 있다고 가정)
SCRIPT_DIR=$(dirname "$0")

# 파이썬 스크립트 실행
# $SCRIPT_DIR을 사용하여 스크립트의 절대 경로를 지정해 줍니다.
echo "Running Python script...holiday"
"$PYTHON_INTERPRETER" "$SCRIPT_DIR/$SCRIPT_NAME"

echo "Script finished."
