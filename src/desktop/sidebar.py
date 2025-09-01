"""
사이드바 네비게이션 컴포넌트 - 간단한 버전
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt
from src.toolbox.ui_kit import ModernStyle
from src.toolbox.ui_kit import tokens


class ModernSidebarButton(QPushButton):
    """사이드바용 모던 버튼"""
    
    def __init__(self, text, icon="", is_active=False):
        display_text = f"{icon}  {text}" if icon else text
        super().__init__(display_text)
        self.is_active = is_active
        self.setup_style()
    
    def setup_style(self):
        """버튼 스타일 설정 - 반응형 적용"""
        if self.is_active:
            bg_color = ModernStyle.COLORS['primary']
            text_color = 'white'
        else:
            bg_color = 'transparent'
            text_color = ModernStyle.COLORS['text_primary']
        
        # 화면 크기에 따른 패딩과 폰트 크기 조정 - 동일 비율 적용
        from src.toolbox.ui_kit.tokens import get_screen_scale_factor
        scale = get_screen_scale_factor()
        
        # 모든 요소에 동일한 스케일 비율 적용
        padding_v = int(tokens.GAP_10 * scale)
        padding_h = int(tokens.GAP_16 * scale)
        font_size = int(tokens.get_font_size('large') * scale)
        
        style = f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                padding: {padding_v}px {padding_h}px;
                text-align: left;
                font-size: {font_size}px;
                font-weight: 500;
                min-height: 35px;
                max-height: 35px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.COLORS['bg_muted']};
                color: {ModernStyle.COLORS['text_primary']};
            }}
        """
        
        if self.is_active:
            style += f"""
                QPushButton:hover {{
                    background-color: {ModernStyle.COLORS['primary_hover']};
                    color: white;
                }}
            """
        
        self.setStyleSheet(style)
    
    def set_active(self, active):
        """활성 상태 설정"""
        self.is_active = active
        self.setup_style()


class Sidebar(QWidget):
    """사이드바 네비게이션"""
    
    page_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.buttons = {}
        self.current_page = None
        self.pages = {}
        self.setup_ui()
        self.setup_default_modules()
    
    def setup_ui(self):
        """사이드바 UI 설정 - 반응형"""
        # 화면 크기에 따른 사이드바 너비 계산 - 동일 비율 적용
        from src.toolbox.ui_kit.tokens import get_screen_scale_factor
        scale = get_screen_scale_factor()
        base_sidebar_width = 230
        
        # 화면 스케일과 동일한 비율로 축소
        sidebar_width = int(base_sidebar_width * scale)
        self.setFixedWidth(sidebar_width)
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {ModernStyle.COLORS['bg_card']};
                border-right: 1px solid {ModernStyle.COLORS['border']};
            }}
        """)
        
        layout = QVBoxLayout()
        spacing = tokens.GAP_10
        layout.setContentsMargins(0, spacing, 0, spacing)
        layout.setSpacing(tokens.GAP_4)
        
        # 앱 제목 - 토큰 기반
        title_label = QLabel("📊 네이버 통합 관리")
        title_font = tokens.get_font_size('header')
        title_padding = tokens.GAP_10
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.COLORS['text_primary']};
                font-size: {title_font}px;
                font-weight: 700;
                padding: {title_padding}px;
                margin-bottom: {spacing}px;
                border-bottom: 1px solid {ModernStyle.COLORS['border']};
            }}
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 버튼들이 추가될 영역
        self.button_layout = QVBoxLayout()
        self.button_layout.setSpacing(tokens.GAP_10)
        layout.addLayout(self.button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def setup_default_modules(self):
        """기본 모듈들 설정"""
        default_modules = [
            ('keyword_analysis', '키워드 검색기', '🔍'),
            ('rank_tracking', '네이버상품 순위추적', '📈'),
            ('powerlink_analyzer', '파워링크 광고비', '💰'),
            ('powerlink_automation', '파워링크 자동입찰', '🚀'),
            ('naver_product_title_generator', '네이버 상품명 생성기', '🏷️'),
        ]
        
        for page_id, name, icon in default_modules:
            self.add_page(page_id, name, icon)
        
        # 첫 번째 페이지를 기본으로 설정
        if default_modules:
            self.switch_to_page(default_modules[0][0])
    
    def add_page(self, page_id, name, icon=""):
        """페이지 추가"""
        self.pages[page_id] = {'name': name, 'icon': icon}
        
        button = ModernSidebarButton(name, icon)
        button.clicked.connect(lambda: self.switch_to_page(page_id))
        
        self.buttons[page_id] = button
        self.button_layout.addWidget(button)
    
    def switch_to_page(self, page_id):
        """페이지 전환"""
        if page_id == self.current_page:
            return
        
        # 이전 버튼 비활성화
        if self.current_page and self.current_page in self.buttons:
            self.buttons[self.current_page].set_active(False)
        
        # 새 버튼 활성화
        if page_id in self.buttons:
            self.buttons[page_id].set_active(True)
            self.current_page = page_id
            self.page_changed.emit(page_id)
    
    def has_page(self, page_id):
        """페이지 존재 확인"""
        return page_id in self.pages