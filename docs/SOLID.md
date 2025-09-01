# SOLID 원칙 적용 가이드

## 📋 개요
이 문서는 네이버 마케팅 통합 프로그램 개발시 SOLID 원칙을 어떻게 적용할지 정리한 가이드입니다.

## 🎯 SOLID 원칙 정의

### 1. **S**ingle Responsibility Principle (단일 책임 원칙)
> 한 클래스는 하나의 책임만 가져야 한다

#### ✅ 적용 방법
```
❌ 나쁜 예: BlogService 클래스에서 UI 처리 + API 호출 + 데이터 저장
✅ 좋은 예: 
   - BlogService: API 호출만
   - BlogUI: UI 처리만  
   - BlogRepository: 데이터 저장만
```

#### 📁 폴더 구조에서 적용
```
src/services/blog_writer/
├── service.py        # 비즈니스 로직만
├── ui.py            # UI 처리만
├── repository.py    # 데이터 접근만
└── models.py        # 데이터 모델만
```

### 2. **O**pen/Closed Principle (개방/폐쇄 원칙)
> 확장에는 열려있고, 수정에는 닫혀있어야 한다

#### ✅ 적용 방법
```python
# 베이스 클래스
class BaseAPIService:
    def call_api(self): pass

# 확장 (기존 코드 수정 없이)
class NaverAPIService(BaseAPIService): pass
class OpenAIAPIService(BaseAPIService): pass
```

### 3. **L**iskov Substitution Principle (리스코프 치환 원칙)
> 자식 클래스는 부모 클래스를 완전히 대체할 수 있어야 한다

#### ✅ 적용 방법
```python
class BaseModule:
    def get_name(self): pass
    def create_widget(self): pass

# 모든 모듈이 동일한 인터페이스
class BlogModule(BaseModule): pass
class KeywordModule(BaseModule): pass
```

### 4. **I**nterface Segregation Principle (인터페이스 분리 원칙)
> 클라이언트는 사용하지 않는 메서드에 의존하면 안된다

#### ✅ 적용 방법
```python
# 큰 인터페이스 (나쁜 예)
class BigInterface:
    def ui_method(self): pass
    def api_method(self): pass
    def db_method(self): pass

# 분리된 인터페이스 (좋은 예)
class UIInterface:
    def create_widget(self): pass

class APIInterface: 
    def call_api(self): pass
```

### 5. **D**ependency Inversion Principle (의존성 역전 원칙)
> 구체적인 것이 아닌 추상적인 것에 의존해야 한다

#### ✅ 적용 방법
```python
# 나쁜 예: 구체 클래스에 의존
class BlogService:
    def __init__(self):
        self.api = NaverAPI()  # 구체 클래스

# 좋은 예: 인터페이스에 의존
class BlogService:
    def __init__(self, api: BaseAPI):
        self.api = api  # 추상화
```

## 🔧 **프로젝트에서 실제 적용**

### 모듈 구조 템플릿
```
src/services/{module_name}/
├── __init__.py
├── service.py       # S: 비즈니스 로직만
├── ui.py           # S: UI 처리만
├── repository.py   # S: 데이터 접근만
├── models.py       # S: 데이터 모델만
└── interfaces.py   # I: 인터페이스 정의
```

### API 관리자 구조
```
src/utils/api/
├── base_api.py     # L: 모든 API의 베이스
├── naver_api.py    # O: 확장 가능
├── openai_api.py   # O: 확장 가능
└── api_factory.py  # D: 의존성 주입
```

## ⚠️ **주의사항**

1. **과도한 추상화 금지**: SOLID를 위한 SOLID는 피하기
2. **점진적 적용**: 한 번에 모든 원칙 적용하려 하지 말기
3. **실용성 우선**: 코드가 복잡해지면 단순화 고려

## 🎯 **체크리스트**

개발할 때 이 질문들을 자문하기:

- [ ] 이 클래스는 한 가지 일만 하는가? (S)
- [ ] 새 기능 추가시 기존 코드를 수정해야 하는가? (O) 
- [ ] 자식 클래스가 부모를 완전히 대체할 수 있는가? (L)
- [ ] 사용하지 않는 메서드를 강제로 구현하고 있는가? (I)
- [ ] 구체 클래스에 직접 의존하고 있는가? (D)

## 💡 **다음에 개발할 때 참고하기**

새 모듈 추가시:
1. `src/services/{module_name}` 폴더 생성
2. 위 템플릿 구조 따라 파일 생성  
3. 체크리스트로 SOLID 원칙 검증
4. 기존 코드 수정 없이 확장되는지 확인