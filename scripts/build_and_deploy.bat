@echo off
chcp 65001
echo ========================================
echo 통합관리프로그램 빌드 및 배포 스크립트
echo ========================================

:: 현재 날짜와 시간 가져오기
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

:: 빌드 디렉토리 생성
if not exist "dist" mkdir dist
if not exist "build" mkdir build

echo.
echo [1/5] 기존 빌드 파일 정리...
if exist "dist\통합관리프로그램.exe" del "dist\통합관리프로그램.exe"
if exist "build\*" rmdir /s /q "build"

echo.
echo [2/5] engine_local.py 파일들을 .pyd로 변환 중...
:: 각 모듈의 engine_local.py를 .pyd로 변환 (선택사항)
:: nuitka --module src/features/keyword_analysis/engine_local.py
:: nuitka --module src/features/powerlink_analyzer/engine_local.py
:: nuitka --module src/features/naver_cafe/engine_local.py
:: nuitka --module src/features/rank_tracking/engine_local.py
echo [건너뜀] .pyd 변환은 수동으로 실행하세요.

echo.
echo [3/5] PyInstaller로 EXE 빌드 중...
pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name="통합관리프로그램" ^
    --icon=assets/app_icon.ico ^
    --add-data="assets;assets" ^
    --add-data="data;data" ^
    --hidden-import="PySide6.QtCore" ^
    --hidden-import="PySide6.QtGui" ^
    --hidden-import="PySide6.QtWidgets" ^
    --hidden-import="requests" ^
    --hidden-import="openpyxl" ^
    --hidden-import="sqlite3" ^
    --exclude-module="tkinter" ^
    --exclude-module="matplotlib" ^
    --exclude-module="PIL" ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo 빌드 실패!
    pause
    exit /b 1
)

echo.
echo [4/5] 빌드 결과 확인...
if not exist "dist\통합관리프로그램.exe" (
    echo 빌드된 EXE 파일을 찾을 수 없습니다!
    pause
    exit /b 1
)

:: 파일 크기 계산 (MB 단위)
for %%A in ("dist\통합관리프로그램.exe") do set "file_size=%%~zA"
set /a "file_size_mb=%file_size% / 1048576"

echo 빌드 완료: dist\통합관리프로그램.exe (약 %file_size_mb%MB)

echo.
echo [5/5] 배포용 파일 준비...
:: 버전 정보 읽기 (Python 스크립트 사용)
for /f %%i in ('python -c "import sys; sys.path.append('src'); from foundation.version import VERSION; print(VERSION)"') do set "current_version=%%i"

:: 배포 파일명 생성
set "deploy_filename=통합관리프로그램_v%current_version%_%timestamp%.exe"
copy "dist\통합관리프로그램.exe" "dist\%deploy_filename%"

echo.
echo ========================================
echo 빌드 및 배포 준비 완료!
echo ========================================
echo 파일명: %deploy_filename%
echo 크기: %file_size_mb%MB
echo.
echo 다음 단계:
echo 1. dist\%deploy_filename% 파일을 Google Drive에 업로드
echo 2. 파일 공유 설정 (링크가 있는 모든 사용자)
echo 3. 파일 ID 복사
echo 4. deployment\version.json 파일 업데이트:
echo    - latest_version: "%current_version%"
echo    - download_url: "https://drive.google.com/uc?id=파일ID"
echo    - file_size_mb: %file_size_mb%
echo 5. 업데이트된 version.json을 Google Drive에 업로드
echo.
echo Google Drive 업로드 후 팀원들에게 알림을 보내주세요.
echo ========================================

:: 탐색기에서 dist 폴더 열기
explorer "dist"

pause