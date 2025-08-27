"""
통합 관리 시스템 메인 데스크톱 애플리케이션
PySide6 기반 GUI 애플리케이션 - 기존 통합관리프로그램 UI 구조 사용
"""
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QStackedWidget, QLabel, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QTimer

from src.foundation.logging import get_logger
from src.foundation.version import version_info
from src.desktop.sidebar import Sidebar
from src.desktop.common_log import CommonLogWidget
from src.desktop.updater import get_auto_updater
from .components import PlaceholderWidget, ErrorWidget
from .styles import AppStyles, WindowConfig, apply_global_styles
from src.toolbox.ui_kit import tokens
from PySide6.QtGui import QIcon

logger = get_logger("desktop.app")




class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.pages = {}  # 페이지 캐시
        self.feature_widgets = {}  # 등록된 기능 위젯들
        self.setup_ui()
        self.setup_window()
        self.setup_updater()
    
    def setup_window(self):
        """윈도우 기본 설정 - 반응형"""
        title = f"통합 관리 시스템 {version_info.get_version_string()}"
        self.setWindowTitle(title)
        
        # 윈도우 아이콘 설정 (타이틀바에 표시되는 아이콘)
        try:
            import os
            import sys
            
            # 개발 모드와 빌드 모드 모두 지원
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 경우
                base_path = sys._MEIPASS
                icon_path = os.path.join(base_path, "assets", "app.ico")
            else:
                # 개발 모드
                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app.ico")
            
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logger.info(f"윈도우 아이콘 설정 완료: {icon_path}")
            else:
                logger.warning(f"아이콘 파일을 찾을 수 없음: {icon_path}")
        except Exception as e:
            logger.error(f"윈도우 아이콘 설정 실패: {e}")
        
        # 반응형 윈도우 크기 설정
        min_width, min_height = WindowConfig.get_min_window_size()
        default_size = WindowConfig.get_default_window_size()
        
        self.setMinimumSize(min_width, min_height)
        self.resize(*default_size)
        
        # 화면 중앙에 배치
        screen = QApplication.primaryScreen()
        screen_center = screen.availableGeometry().center()
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen_center)
        self.move(window_rect.topLeft())
        
        # 전체 윈도우 스타일
        self.setStyleSheet(AppStyles.get_main_window_style())
    
    def setup_updater(self):
        """자동 업데이트 시스템 설정"""
        try:
            self.auto_updater = get_auto_updater()
            
            # 업데이트 관련 시그널 연결
            self.auto_updater.update_available.connect(self.on_update_available)
            self.auto_updater.update_check_failed.connect(self.on_update_check_failed)
            
            # 앱 시작 후 3초 뒤에 업데이트 체크 (백그라운드)
            QTimer.singleShot(3000, lambda: self.auto_updater.check_for_updates(force=False))
            
            logger.info("자동 업데이트 시스템 초기화 완료")
            
        except Exception as e:
            logger.error(f"업데이트 시스템 설정 실패: {e}")
    
    def on_update_available(self, update_info):
        """업데이트 발견 시 처리"""
        try:
            from src.desktop.common_log import log_manager
            log_manager.add_log(f"🆙 새로운 버전 {update_info.latest_version}이 출시되었습니다!", "info")
            
            # 업데이트 다이얼로그 표시
            self.auto_updater.show_update_dialog(update_info)
            
        except Exception as e:
            logger.error(f"업데이트 알림 처리 오류: {e}")
    
    def on_update_check_failed(self, error_message):
        """업데이트 체크 실패 시 처리"""
        # 로그에만 기록 (사용자에게는 방해하지 않음)
        logger.debug(f"업데이트 체크 실패: {error_message}")
    
    def setup_ui(self):
        """UI 구성"""
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 전체 레이아웃 (수직) - 반응형 여백
        main_container_layout = QVBoxLayout()
        margins = WindowConfig.get_main_margins()
        main_container_layout.setContentsMargins(*margins)
        main_container_layout.setSpacing(0)
        
        # 헤더 제거 - API 설정 버튼을 로그 영역으로 이동
        
        # 메인 레이아웃 (수평) - 토큰 기반 여백
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(*margins)
        main_layout.setSpacing(tokens.GAP_6)
        
        # 사이드바 (모듈별 네비게이션)
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        
        # 메인 컨텐츠 영역
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(AppStyles.get_content_stack_style())
        
        # 공통 로그 위젯 - 화면 크기에 따라 반응형 크기
        self.common_log = CommonLogWidget()
        self.common_log.api_settings_requested.connect(self.open_api_settings)
        
        # 화면 크기에 따른 로그 위젯 너비 계산 - 동일 비율 적용
        from src.toolbox.ui_kit.tokens import get_screen_scale_factor
        scale = get_screen_scale_factor()
        base_log_width = 270
        
        # 화면 스케일과 동일한 비율로 축소
        log_width = int(base_log_width * scale)
        self.common_log.setFixedWidth(log_width)
        
        # 스플리터 대신 간단한 레이아웃
        content_widget = QWidget()
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(tokens.GAP_6)
        
        content_layout.addWidget(self.content_stack, 1)  # 확장 가능
        content_layout.addWidget(self.common_log, 0)     # 고정 크기
        content_widget.setLayout(content_layout)
        
        # 메인 레이아웃에 추가
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content_widget, 1)  # 확장 가능
        
        # 메인 영역을 위젯으로 만들어서 컨테이너에 추가
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        main_container_layout.addWidget(main_widget)
        
        central_widget.setLayout(main_container_layout)
        
        # 초기 페이지 로드 (UI 완전 초기화 후)
        QTimer.singleShot(0, self.load_initial_page)
    
    
    def open_api_settings(self):
        """통합 API 설정 열기"""
        try:
            from src.desktop.api_dialog import APISettingsDialog
            from PySide6.QtWidgets import QDialog
            
            dialog = APISettingsDialog(self)
            
            # API 설정 변경 시그널 연결
            if hasattr(dialog, 'api_settings_changed'):
                dialog.api_settings_changed.connect(self.on_api_settings_changed)
            
            if dialog.exec() == QDialog.Accepted:
                # API 설정 저장됨을 로그에 알림
                from src.desktop.common_log import log_manager
                log_manager.add_log("🔄 통합 API 설정이 업데이트되었습니다.", "success")
        except Exception as e:
            logger.error(f"API 설정 오류: {e}")
            QMessageBox.critical(self, "오류", f"API 설정 오류: {str(e)}")
    
    def on_api_settings_changed(self):
        """API 설정이 변경되었을 때 호출되는 함수"""
        try:
            from src.desktop.common_log import log_manager
            from src.desktop.api_checker import APIChecker
            
            log_manager.add_log("🔄 API 설정이 변경되었습니다. 연결 상태를 다시 확인합니다.", "info")
            
            # 캐시 무효화 후 API 상태 재확인
            APIChecker.invalidate_all_caches()
            QTimer.singleShot(500, self.recheck_api_status)
            
        except Exception as e:
            logger.error(f"API 설정 변경 처리 오류: {e}")
    
    def recheck_api_status(self):
        """API 상태 재확인 (상세 모드)"""
        try:
            from src.desktop.api_checker import APIChecker
            
            is_ready = APIChecker.check_all_apis_detailed()
            
            if is_ready:
                from src.desktop.common_log import log_manager
                log_manager.add_log("🎉 API 설정이 완료되었습니다! 모든 기능을 사용할 수 있습니다.", "success")
            
        except Exception as e:
            logger.error(f"API 상태 재확인 오류: {e}")
    
    def load_initial_page(self):
        """초기 페이지 로드"""
        # API 상태 확인 (최우선)
        self.check_api_status_on_startup()
        
        if self.sidebar.current_page:
            self.switch_page(self.sidebar.current_page)
    
    def check_api_status_on_startup(self):
        """시작 시 API 상태 확인 (조용한 모드)"""
        try:
            from src.desktop.api_checker import check_api_status_on_startup
            from src.desktop.common_log import log_manager
            
            # 간단한 시작 메시지
            log_manager.add_log("🚀 통합관리프로그램 시작됨", "success")
            
            # API 상태 확인 (조용히)  
            is_ready = check_api_status_on_startup()
            
            # API 설정 안내는 필요한 경우에만 표시
            if not is_ready:
                QTimer.singleShot(2000, self.show_api_setup_reminder)
            
        except Exception as e:
            logger.error(f"API 상태 확인 오류: {e}")
    
    def show_api_setup_reminder(self):
        """API 설정 안내 메시지 (지연 표시)"""
        try:
            from src.desktop.common_log import log_manager
            log_manager.add_log("💡 상단 '⚙️ API 설정' 버튼에서 네이버 검색광고 API와 네이버 개발자 API를 설정하세요.", "info")
            
        except Exception as e:
            logger.error(f"API 설정 안내 오류: {e}")
    
    def switch_page(self, page_id):
        """페이지 전환"""
        try:
            # 페이지가 이미 로드되어 있으면 재사용
            if page_id in self.pages:
                widget = self.pages[page_id]
            else:
                # 새 페이지 로드
                widget = self.load_page(page_id)
                self.pages[page_id] = widget
                self.content_stack.addWidget(widget)
            
            # 페이지 전환
            self.content_stack.setCurrentWidget(widget)
            
        except Exception as e:
            logger.error(f"페이지 로드 오류: {e}")
            QMessageBox.critical(self, "오류", f"페이지 로드 오류: {str(e)}")
    
    def load_page(self, page_id):
        """페이지 로드"""
        try:
            # 등록된 기능 위젯이 있으면 반환
            if page_id in self.feature_widgets:
                return self.feature_widgets[page_id]
            
            # 기본적으로는 플레이스홀더 표시
            module_name = self.get_module_name(page_id)
            return PlaceholderWidget(module_name, page_id)
            
        except Exception as e:
            # 오류 발생시 오류 페이지 표시
            return ErrorWidget(str(e))
    
    def get_module_name(self, module_id):
        """모듈 ID에서 이름 가져오기"""
        module_names = {
            'keyword_analysis': '키워드 검색기',
            'rank_tracking': '네이버상품 순위추적',
            'naver_cafe': '네이버 카페DB추출',
            'powerlink_analyzer': 'PowerLink 분석',
            'naver_product_title_generator': '네이버 상품명 생성기',
        }
        return module_names.get(module_id, module_id)
    
    def add_feature_tab(self, widget, title):
        """기능 탭 추가 (기존 탭 방식 호환)"""
        # 탭 제목을 기반으로 page_id 생성
        page_id = self.title_to_page_id(title)
        
        # 기능 위젯 등록
        self.feature_widgets[page_id] = widget
        
        # 사이드바에 메뉴 항목이 있으면 활성화, 없으면 추가
        if not self.sidebar.has_page(page_id):
            self.sidebar.add_page(page_id, title, "📊")
        
        logger.info(f"기능 탭 추가됨: {title} (page_id: {page_id})")
    
    def title_to_page_id(self, title):
        """탭 제목을 page_id로 변환"""
        title_map = {
            '키워드 검색기': 'keyword_analysis',
            '네이버상품 순위추적': 'rank_tracking',
            '네이버 카페DB추출': 'naver_cafe',
            'PowerLink 분석': 'powerlink_analyzer',
            '네이버 상품명 생성기': 'naver_product_title_generator',
        }
        return title_map.get(title, title.lower().replace(' ', '_'))


def run_app(load_features_func=None):
    """애플리케이션 실행"""
    try:
        # 기본 DPI 설정만 유지 (성능 최적화)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        app = QApplication(sys.argv)
        
        # DPI 정보 로그 출력 및 반응형 스케일링 설정
        screen = app.primaryScreen()
        dpr = screen.devicePixelRatio()
        screen_width = screen.geometry().width()
        screen_height = screen.geometry().height()
        
        # 화면 크기 기반 스케일 팩터 계산 및 설정
        from src.toolbox.ui_kit.tokens import calculate_screen_scale_from_resolution, set_screen_scale_factor
        scale_factor = calculate_screen_scale_from_resolution(screen_width, screen_height)
        set_screen_scale_factor(scale_factor)
        
        logger.info(f"화면 DPI 비율: {dpr}, 해상도: {screen_width}x{screen_height}, UI 스케일: {scale_factor:.2f}")
        
        # 전역 스타일 적용
        apply_global_styles(app)
        
        # 메인 윈도우 생성
        main_window = MainWindow()
        
        # 기능 모듈 로드 (있는 경우)
        if load_features_func:
            load_features_func(main_window)
        
        main_window.show()
        
        logger.info("데스크톱 애플리케이션 시작됨")
        
        # 이벤트 루프 시작
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"애플리케이션 실행 실패: {e}")
        raise