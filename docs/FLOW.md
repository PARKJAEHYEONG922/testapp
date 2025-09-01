# 전체 동작 흐름 정리

## 🚀 프로그램 실행 흐름

### 1. 시작 (main.py)
```
main.py 실행
↓
QApplication 생성
↓
MainWindow 생성 및 표시
↓
Sidebar 로드 (config.json 기반)
↓
첫 번째 모듈 자동 선택
```

### 2. 모듈 전환 흐름
```
사용자가 사이드바 메뉴 클릭
↓
Sidebar.switch_page(page_id) 호출
↓
page_changed 시그널 발생
↓
MainWindow.switch_page(page_id) 받음
↓
모듈이 캐시되어 있으면 재사용, 없으면 새로 로드
↓
QStackedWidget으로 페이지 전환
```

### 3. 새 모듈 추가 흐름
```
1. src/services/{module_name}/ 폴더 생성
2. service.py, ui.py, models.py 파일 작성
3. config/config.json에 모듈 정보 추가
4. MainWindow.load_page()에서 모듈 로딩 로직 추가
```

## 📊 데이터 흐름

### API 관리
```
각 모듈
↓
개별 API 매니저 사용
↓
config.json에서 API 키 로드
↓
드롭다운으로 여러 계정 선택 가능
```

### 설정 관리
```
config/config.json (메인 설정)
↓
각 모듈별 개별 설정 파일 (선택사항)
↓
사용자 UI에서 설정 변경
↓
실시간 저장
```

## 🔄 모듈 라이프사이클

1. **로드**: 처음 클릭시 모듈 생성
2. **캐시**: 한번 로드된 모듈은 메모리에 유지
3. **전환**: 빠른 페이지 전환 
4. **정리**: 프로그램 종료시 자동 정리

## 🎯 확장 지점

### 새 모듈 추가시
- `config.json` → 메뉴 정보
- `services/` → 비즈니스 로직
- `MainWindow.load_page()` → 로딩 로직

### 새 API 추가시  
- `utils/api/` → API 클래스
- `config.json` → API 설정
- 각 모듈에서 활용