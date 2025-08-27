"""
공통 UI 컴포넌트 (버튼, 입력창 등)
재사용 가능한 UI 요소들
"""
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLineEdit, QTextEdit, QLabel, 
    QVBoxLayout, QHBoxLayout, QFrame, QProgressBar,
    QComboBox, QSpinBox, QCheckBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor

from src.foundation.logging import get_logger
from .modern_style import ModernStyle
from . import tokens


logger = get_logger("toolbox.ui_kit")


class ModernPrimaryButton(QPushButton):
    """기본 액션 버튼 (파란색) - 키워드 분석기 스타일 기반"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        # 반응형 크기 계산
        padding_v = int(tokens.GAP_6 * scale)
        padding_h = int(tokens.GAP_12 * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        border_radius = int(tokens.RADIUS_SM * scale)
        min_width = int(70 * scale)
        min_height = int(tokens.BTN_H_SM * scale)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-weight: 580;
                font-size: {font_size}px;
                font-family: '{ModernStyle.DEFAULT_FONT}';
                min-width: {min_width}px;
                min-height: {min_height}px;
            }}
            QPushButton:hover {{
                background-color: {tokens.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {tokens.COLOR_PRIMARY_PRESSED};
                margin-top: 1px;
            }}
            QPushButton:disabled {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_SECONDARY};
            }}
        """)


class ModernSuccessButton(QPushButton):
    """성공/저장 버튼 (녹색) - 키워드 분석기 스타일 기반"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        # 반응형 크기 계산
        padding_v = int(tokens.GAP_6 * scale)
        padding_h = int(tokens.GAP_12 * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        border_radius = int(tokens.RADIUS_SM * scale)
        min_width = int(70 * scale)
        min_height = int(tokens.BTN_H_SM * scale)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.COLOR_SUCCESS};
                color: white;
                border: none;
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-weight: 580;
                font-size: {font_size}px;
                font-family: '{ModernStyle.DEFAULT_FONT}';
                min-width: {min_width}px;
                min-height: {min_height}px;
            }}
            QPushButton:hover {{
                background-color: {tokens.COLOR_SUCCESS_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {tokens.COLOR_SUCCESS_PRESSED};
                margin-top: 1px;
            }}
            QPushButton:disabled {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_SECONDARY};
            }}
        """)


class ModernDangerButton(QPushButton):
    """위험/삭제 버튼 (빨간색) - 키워드 분석기 스타일 기반"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        # 반응형 크기 계산
        padding_v = int(tokens.GAP_6 * scale)
        padding_h = int(tokens.GAP_12 * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        border_radius = int(tokens.RADIUS_SM * scale)
        min_width = int(70 * scale)
        min_height = int(tokens.BTN_H_SM * scale)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.COLOR_DANGER};
                color: white;
                border: none;
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-weight: 580;
                font-size: {font_size}px;
                font-family: '{ModernStyle.DEFAULT_FONT}';
                min-width: {min_width}px;
                min-height: {min_height}px;
            }}
            QPushButton:hover {{
                background-color: {tokens.COLOR_DANGER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {tokens.COLOR_DANGER_PRESSED};
                margin-top: 1px;
            }}
            QPushButton:disabled {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_SECONDARY};
            }}
        """)


class ModernCancelButton(QPushButton):
    """취소/정지 버튼 - 활성화 시에만 빨간색"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._setup_style()
    
    def _setup_style(self):
        """토큰 기반 스타일 - 기존 크기 유지 + 작은 화면에서만 축소"""
        scale = tokens.get_screen_scale_factor()
        
        # 모든 화면에서 동일한 비율로 스케일링 적용
        padding_v = int(tokens.GAP_6 * scale)
        padding_h = int(tokens.GAP_12 * scale)  
        border_radius = int(tokens.RADIUS_MD * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        min_width = int(tokens.BTN_H_MD * 2 * scale)
        min_height = int(tokens.BTN_H_SM * scale)
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_SECONDARY};
                border: none;
                padding: {padding_v}px {padding_h}px;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
                font-weight: 580;
                min-width: {min_width}px;
                min-height: {min_height}px;
            }}
            QPushButton:enabled {{
                background-color: {tokens.COLOR_DANGER};
                color: white;
            }}
            QPushButton:enabled:hover {{
                background-color: {tokens.COLOR_DANGER_HOVER};
                color: white;
            }}
            QPushButton:enabled:pressed {{
                background-color: {tokens.COLOR_DANGER_PRESSED};
                color: white;
            }}
            QPushButton:disabled {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_SECONDARY};
            }}
        """)


class ModernHelpButton(QPushButton):
    """도움말 버튼 (회색) - 키워드 분석기 스타일 기반"""
    
    def __init__(self, text: str = "❓ 사용법", parent=None):
        super().__init__(text, parent)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        # 반응형 크기 계산
        padding_v = int(tokens.GAP_6 * scale)
        padding_h = int(tokens.GAP_12 * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        border_radius = int(tokens.RADIUS_SM * scale)
        min_width = int(70 * scale)
        min_height = int(tokens.BTN_H_SM * scale)
        border_width = int(tokens.BORDER_1 * scale)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_PRIMARY};
                border: {border_width}px solid {tokens.COLOR_BORDER};
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-weight: 580;
                font-size: {font_size}px;
                font-family: '{ModernStyle.DEFAULT_FONT}';
                min-width: {min_width}px;
                min-height: {min_height}px;
            }}
            QPushButton:hover {{
                background-color: {tokens.COLOR_BG_SECONDARY};
                border-color: {tokens.COLOR_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {tokens.COLOR_PRIMARY};
                color: white;
                border-color: {tokens.COLOR_PRIMARY};
                margin-top: 1px;
            }}
            QPushButton:disabled {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_SECONDARY};
            }}
        """)


class ModernButton(QPushButton):
    """모던 스타일 버튼"""
    
    def __init__(self, text: str, style_type: str = "primary", parent=None):
        super().__init__(text, parent)
        self.style_type = style_type
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 타입별 완전 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        # 반응형 크기 계산
        padding_v = int(tokens.GAP_6 * scale)
        padding_h = int(tokens.GAP_12 * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        border_radius = int(tokens.RADIUS_SM * scale)
        min_width = int(70 * scale)
        min_height = int(tokens.BTN_H_SM * scale)
        border_width = int(tokens.BORDER_1 * scale)
        
        # 타입별 색상 매핑
        if self.style_type in ["primary", "info"]:
            bg_color = tokens.COLOR_PRIMARY
            hover_color = tokens.COLOR_PRIMARY_HOVER
            pressed_color = tokens.COLOR_PRIMARY_PRESSED
            text_color = "white"
            border_color = "none"
        elif self.style_type == "success":
            bg_color = tokens.COLOR_SUCCESS
            hover_color = tokens.COLOR_SUCCESS_HOVER
            pressed_color = tokens.COLOR_SUCCESS_PRESSED
            text_color = "white"
            border_color = "none"
        elif self.style_type in ["danger", "warning"]:
            bg_color = tokens.COLOR_DANGER
            hover_color = tokens.COLOR_DANGER_HOVER
            pressed_color = tokens.COLOR_DANGER_PRESSED
            text_color = "white"
            border_color = "none"
        else:  # secondary, outline
            bg_color = tokens.COLOR_BG_INPUT
            hover_color = tokens.COLOR_BG_SECONDARY
            pressed_color = tokens.COLOR_PRIMARY
            text_color = tokens.COLOR_TEXT_PRIMARY
            border_color = f"{border_width}px solid {tokens.COLOR_BORDER}"
        
        border_style = "border: none;" if border_color == "none" else f"border: {border_color};"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                {border_style}
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-weight: 580;
                font-size: {font_size}px;
                font-family: '{ModernStyle.DEFAULT_FONT}';
                min-width: {min_width}px;
                min-height: {min_height}px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                {'border-color: ' + tokens.COLOR_PRIMARY + ';' if border_color != 'none' else ''}
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
                {'color: white; border-color: ' + tokens.COLOR_PRIMARY + ';' if border_color != 'none' else ''}
                margin-top: 1px;
            }}
            QPushButton:disabled {{
                background-color: {tokens.COLOR_BG_INPUT};
                color: {tokens.COLOR_TEXT_SECONDARY};
            }}
        """)
    
    # _darken_color 메서드 제거됨 - 공용 스타일 사용으로 불필요


class ModernLineEdit(QLineEdit):
    """모던 스타일 라인 에디트"""
    
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        border_width = int(tokens.BORDER_2 * scale)
        border_radius = int(tokens.RADIUS_SM * scale)
        padding_v = int(tokens.GAP_8 * scale)
        padding_h = int(tokens.GAP_12 * scale)
        font_size = int(tokens.get_font_size('small') * scale)
        
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {tokens.COLOR_BG_PRIMARY};
                border: {border_width}px solid {tokens.COLOR_BORDER};
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-size: {font_size}px;
                font-family: '{ModernStyle.DEFAULT_FONT}';
                color: {tokens.COLOR_TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {tokens.COLOR_PRIMARY};
                outline: none;
            }}
        """)


class ModernTextEdit(QTextEdit):
    """모던 스타일 텍스트 에디트"""
    
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        border_width = int(tokens.BORDER_2 * scale)
        border_radius = int(tokens.RADIUS_MD * scale)
        padding = int(tokens.GAP_8 * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        
        self.setStyleSheet(f"""
            QTextEdit {{
                border: {border_width}px solid {tokens.COLOR_BORDER};
                border-radius: {border_radius}px;
                padding: {padding}px;
                font-size: {font_size}px;
                background-color: {tokens.COLOR_BG_PRIMARY};
            }}
            QTextEdit:focus {{
                border-color: {tokens.COLOR_PRIMARY};
                outline: none;
            }}
        """)


class ModernCard(QGroupBox):
    """모던 스타일 카드 - 네이버카페 버전 스타일 (공용 표준)"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        font_size = int(tokens.get_font_size('small') * scale)
        border_width = int(tokens.BORDER_2 * scale)
        border_radius = int(tokens.RADIUS_LG * scale)
        margin_v = int(tokens.GAP_10 * scale)
        padding_top = int(tokens.GAP_16 * scale)
        left_pos = int(tokens.GAP_16 * scale)
        title_padding = int(tokens.GAP_10 * scale)
        
        self.setStyleSheet(f"""
            QGroupBox {{
                font-size: {font_size}px;
                font-weight: 600;
                border: {border_width}px solid {tokens.COLOR_BORDER};
                border-radius: {border_radius}px;
                margin: {margin_v}px 0;
                padding-top: {padding_top}px;
                background-color: {tokens.COLOR_BG_CARD};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {left_pos}px;
                padding: 0 {title_padding}px;
                color: {tokens.COLOR_TEXT_PRIMARY};
                background-color: {tokens.COLOR_BG_CARD};
            }}
        """)


class ModernProgressBar(QProgressBar):
    """모던 스타일 프로그레스 바"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_style()
    
    def _setup_style(self):
        """반응형 스타일 적용 - 모든 크기 속성 스케일링"""
        scale = tokens.get_screen_scale_factor()
        
        border_width = int(tokens.BORDER_2 * scale)
        border_radius = int(tokens.RADIUS_MD * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        height = int((tokens.BTN_H_SM - tokens.GAP_6) * scale)
        chunk_radius = int(tokens.RADIUS_SM * scale)
        min_height = int(tokens.BTN_H_SM * scale)
        
        self.setStyleSheet(f"""
            QProgressBar {{
                border: {border_width}px solid {tokens.COLOR_BORDER};
                border-radius: {border_radius}px;
                text-align: center;
                font-size: {font_size}px;
                background-color: {tokens.COLOR_BG_INPUT};
                height: {height}px;
            }}
            QProgressBar::chunk {{
                background-color: {tokens.COLOR_PRIMARY};
                border-radius: {chunk_radius}px;
            }}
        """)
        
        self.setMinimumHeight(min_height)


class StatusWidget(QWidget):
    """상태 표시 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 설정"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("준비됨")
        scale = tokens.get_screen_scale_factor()
        font = QFont()
        font.setPixelSize(int(tokens.get_font_size('normal') * scale))
        self.status_label.setFont(font)
        
        layout.addWidget(self.status_label)
        layout.addStretch()
    
    def set_status(self, text: str, status_type: str = "info"):
        """토큰 기반 상태 설정"""
        colors = {
            "success": tokens.COLOR_SUCCESS,
            "warning": tokens.COLOR_WARNING,
            "error": tokens.COLOR_DANGER,
            "info": tokens.COLOR_INFO
        }
        
        color = colors.get(status_type, tokens.COLOR_INFO)
        
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")


class FormGroup(QWidget):
    """폼 그룹 위젯"""
    
    def __init__(self, label_text: str, widget: QWidget, parent=None):
        super().__init__(parent)
        self._setup_ui(label_text, widget)
    
    def _setup_ui(self, label_text: str, widget: QWidget):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 라벨
        label = QLabel(label_text)
        scale = tokens.get_screen_scale_factor()
        font = QFont()
        font.setPixelSize(int(tokens.get_font_size('normal') * scale))
        label.setFont(font)
        label.setStyleSheet(f"color: {tokens.COLOR_TEXT_PRIMARY}; font-weight: bold;")
        
        layout.addWidget(label)
        layout.addWidget(widget)


# 편의 함수들
def create_button(text: str, style_type: str = "primary") -> ModernButton:
    """모던 버튼 생성 편의 함수"""
    return ModernButton(text, style_type)


def create_input(placeholder: str = "") -> ModernLineEdit:
    """모던 입력창 생성 편의 함수"""
    return ModernLineEdit(placeholder)


def create_text_area(placeholder: str = "") -> ModernTextEdit:
    """모던 텍스트 영역 생성 편의 함수"""
    return ModernTextEdit(placeholder)


def create_card(title: str = "") -> ModernCard:
    """모던 카드 생성 편의 함수"""
    return ModernCard(title)


def create_form_group(label: str, widget: QWidget) -> FormGroup:
    """폼 그룹 생성 편의 함수"""
    return FormGroup(label, widget)