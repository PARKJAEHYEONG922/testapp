"""
네이버 카페 DB 추출기 컨트롤 위젯 (좌측 패널)
진행상황, 카페검색, 게시판검색, 추출설정, 추출시작버튼, 정지버튼을 포함
"""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer

from src.toolbox.ui_kit import ModernStyle, tokens
from src.toolbox.ui_kit.modern_dialog import ModernConfirmDialog
from src.toolbox.ui_kit import ModernInfoDialog
from src.toolbox.ui_kit.components import ModernCard, ModernPrimaryButton, ModernSuccessButton, ModernCancelButton
from src.desktop.common_log import log_manager
from src.foundation.logging import get_logger
from .models import CafeInfo, BoardInfo, ExtractionProgress, ExtractionTask
from .worker import NaverCafeUnifiedWorker
from .service import NaverCafeExtractionService

logger = get_logger("features.naver_cafe.control_widget")


class NaverCafeControlWidget(QWidget):
    """네이버 카페 추출 컨트롤 위젯 (좌측 패널)"""
    
    # 시그널 정의
    extraction_started = Signal()
    extraction_completed = Signal(dict)  # 추출 완료 시 결과 전달
    extraction_error = Signal(str)
    extraction_progress_updated = Signal(object)  # ExtractionProgress 객체
    user_extracted = Signal(object)  # ExtractedUser 객체
    data_cleared = Signal()  # 데이터 클리어 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_cafes: List[CafeInfo] = []
        self.current_boards: List[BoardInfo] = []
        self.extraction_in_progress = False
        self.is_manually_stopped = False
        
        # 통합 워커 (하나만 사용)
        self.unified_worker = None
        
        # 서비스 인스턴스 (CLAUDE.md: UI는 service 경유)
        self.service = NaverCafeExtractionService()
        
        self.setup_ui()
        self.setup_connections()
        
        # 초기 상태 설정
        self.update_progress_step(0, "active", "카페를 검색해주세요")
        
    def setup_ui(self):
        """UI 초기화 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        layout = QVBoxLayout(self)
        spacing = int(tokens.GAP_10 * scale)
        layout.setSpacing(spacing)
        
        # 1. 진행상황 카드
        progress_card = self.create_progress_card()
        layout.addWidget(progress_card)
        
        # 2. 카페 검색 카드
        search_card = self.create_search_card()
        layout.addWidget(search_card)
        
        # 3. 카페 선택 카드
        cafe_card = self.create_cafe_card()
        layout.addWidget(cafe_card)
        
        # 4. 게시판 선택 카드
        board_card = self.create_board_card()
        layout.addWidget(board_card)
        
        # 5. 추출 설정 카드
        settings_card = self.create_settings_card()
        layout.addWidget(settings_card)
        
        # 6. 제어 버튼들
        control_buttons = self.create_control_buttons()
        layout.addWidget(control_buttons)
        
        # 여유 공간
        layout.addStretch()
        
    def create_progress_card(self) -> ModernCard:
        """진행상황 카드 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        card = ModernCard("📊 진행상황")
        # 진행상황 카드의 고정 높이 설정 (크기 변동 방지) - 반응형 스케일링 적용
        card_height = int(140 * scale)
        card.setFixedHeight(card_height)
        layout = QVBoxLayout()
        layout_spacing = int(tokens.GAP_10 * scale)
        layout.setSpacing(layout_spacing)
        
        # 진행 단계들
        self.progress_steps = [
            {"name": "카페 검색", "icon": "🔍", "status": "pending"},
            {"name": "카페 선택", "icon": "📍", "status": "pending"}, 
            {"name": "게시판 로딩", "icon": "📋", "status": "pending"},
            {"name": "게시판 선택", "icon": "✅", "status": "pending"},
            {"name": "추출 준비", "icon": "🚀", "status": "pending"}
        ]
        
        # 진행 단계 표시 컨테이너
        progress_container = QWidget()
        border_radius = int(tokens.RADIUS_SM * scale)
        padding = int(tokens.GAP_12 * scale)
        margin = int(tokens.GAP_6 * scale)
        min_height = int(30 * scale)
        progress_container.setStyleSheet(f"""
            QWidget {{
                background-color: {ModernStyle.COLORS['bg_input']};
                border: 1px solid {ModernStyle.COLORS['border']};
                border-radius: {border_radius}px;
                padding: 0px;
                margin: 0px;
                min-height: {min_height}px;
            }}
        """)
        
        progress_grid = QHBoxLayout()
        margin_h = int(tokens.GAP_6 * scale)
        margin_v = int(tokens.GAP_4 * scale)
        grid_spacing = int(tokens.GAP_8 * scale)
        progress_grid.setContentsMargins(
            margin_h, margin_v,
            margin_h, margin_v
        )
        progress_grid.setSpacing(grid_spacing)
        
        self.progress_labels = []
        
        for i, step in enumerate(self.progress_steps):
            # 단계 라벨
            step_label = QLabel()
            step_label.setAlignment(Qt.AlignCenter)
            self.update_step_display(step_label, step, "pending")
            
            progress_grid.addWidget(step_label)
            self.progress_labels.append(step_label)
            
            # 화살표 (마지막 단계 제외)
            if i < len(self.progress_steps) - 1:
                arrow_label = QLabel("→")
                arrow_label.setAlignment(Qt.AlignCenter)
                arrow_font_size = int(tokens.get_font_size('small') * scale)
                arrow_label.setStyleSheet(f"""
                    QLabel {{
                        color: {ModernStyle.COLORS['text_muted']};
                        font-size: {arrow_font_size}px;
                        font-weight: bold;
                    }}
                """)
                progress_grid.addWidget(arrow_label)
        
        progress_container.setLayout(progress_grid)
        layout.addWidget(progress_container)
        
        # 상태 메시지 - 반응형 스케일링 적용
        self.status_label = QLabel("추출 대기 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font_size = int(tokens.get_font_size('normal') * scale)
        status_border_radius = int(tokens.GAP_4 * scale)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.COLORS['primary']};
                font-size: {status_font_size}px;
                font-weight: 600;
                background-color: rgba(59, 130, 246, 0.1);
                border-radius: {status_border_radius}px;
            }}
        """)
        layout.addWidget(self.status_label)
        
        card.setLayout(layout)
        return card
    
    def update_step_display(self, label, step, status):
        """단계 표시 업데이트 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        if status == "pending":
            color = ModernStyle.COLORS['text_muted']
            bg_color = "transparent"
        elif status == "active":
            color = ModernStyle.COLORS['primary']
            bg_color = f"rgba(59, 130, 246, 0.2)"
        elif status == "completed":
            color = ModernStyle.COLORS['success']
            bg_color = f"rgba(16, 185, 129, 0.2)"
        elif status == "error":
            color = ModernStyle.COLORS['danger']
            bg_color = f"rgba(239, 68, 68, 0.2)"
        
        label.setText(f"{step['icon']}\n{step['name']}")
        # 반응형 스케일링 적용
        border_radius = int(tokens.GAP_3 * scale)
        padding_v = int(tokens.GAP_6 * scale)
        padding_h = int(tokens.GAP_4 * scale)
        font_size = int(tokens.get_font_size('small') * scale)
        min_width = int(tokens.GAP_50 * scale)
        max_width = int(tokens.GAP_60 * scale)
        label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: {bg_color};
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-size: {font_size}px;
                font-weight: 600;
                text-align: center;
                min-width: {min_width}px;
                max-width: {max_width}px;
            }}
        """)
    
    def update_progress_step(self, step_index, status, message=""):
        """진행 단계 업데이트"""
        if 0 <= step_index < len(self.progress_steps):
            self.progress_steps[step_index]["status"] = status
            self.update_step_display(self.progress_labels[step_index], self.progress_steps[step_index], status)
            
            # 추출 중이면 status_label을 건드리지 않음 (on_progress_updated에서 처리)
            if hasattr(self, 'extraction_in_progress') and self.extraction_in_progress and step_index == 4:
                return
            
            # 상태 메시지 표시
            if message:
                self.status_label.setText(message)
            else:
                # 기본 메시지를 현재 활성 단계에 맞게 설정
                self._update_default_status_message()
    
    def _update_default_status_message(self):
        """현재 활성 단계에 맞는 기본 상태 메시지 설정"""
        # 현재 활성 단계 찾기
        active_step_index = -1
        for i, step in enumerate(self.progress_steps):
            if step["status"] == "active":
                active_step_index = i
                break
        
        # 활성 단계에 맞는 메시지 설정
        if active_step_index == 0:  # 카페 검색
            self.status_label.setText("카페를 검색해주세요")
        elif active_step_index == 1:  # 카페 선택
            self.status_label.setText("카페를 선택해주세요")
        elif active_step_index == 2:  # 게시판 로딩
            self.status_label.setText("게시판 목록을 불러오는 중...")
        elif active_step_index == 3:  # 게시판 선택
            self.status_label.setText("게시판을 선택해주세요")
        elif active_step_index == 4:  # 추출 준비
            self.status_label.setText("추출 준비 완료!")
        else:
            # 모든 단계가 완료되었거나 활성 단계가 없는 경우
            completed_count = sum(1 for step in self.progress_steps if step["status"] == "completed")
            if completed_count == len(self.progress_steps):
                self.status_label.setText("모든 준비 완료!")
            else:
                self.status_label.setText("추출 대기 중...")
    
    def reset_progress_steps(self):
        """진행 단계 초기화"""
        for i, step in enumerate(self.progress_steps):
            step["status"] = "pending"
            self.update_step_display(self.progress_labels[i], step, "pending")
        
        # 첫 번째 단계를 활성으로 설정
        self.update_progress_step(0, "active", "카페를 검색해주세요")
        
    def create_search_card(self) -> ModernCard:
        """카페 검색 카드 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        card = ModernCard("🔍 카페 검색")
        layout = QVBoxLayout()
        layout_spacing = int(tokens.GAP_8 * scale)
        layout.setSpacing(layout_spacing)
        
        # 검색어 입력과 검색 버튼을 가로로 배치 - 반응형 스케일링 적용
        search_input_layout = QHBoxLayout()
        input_layout_spacing = int(tokens.GAP_8 * scale)
        search_input_layout.setSpacing(input_layout_spacing)
        
        # 검색어 입력 - 반응형 스케일링 적용
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("카페명 또는 URL을 입력하세요")
        # 입력 필드와 버튼의 높이를 동일하게 설정 - 반응형 스케일링 적용
        input_height = int(tokens.GAP_36 * scale)  # 패딩 포함한 총 높이
        border_radius = int(tokens.GAP_8 * scale)
        padding_v = int(tokens.GAP_8 * scale)
        padding_h = int(tokens.GAP_10 * scale)
        font_size = int(tokens.get_font_size('normal') * scale)
        border_width = int(2 * scale)
        self.search_input.setFixedHeight(input_height)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ModernStyle.COLORS['bg_input']};
                border: {border_width}px solid {ModernStyle.COLORS['border']};
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-size: {font_size}px;
                color: {ModernStyle.COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {ModernStyle.COLORS['primary']};
                background-color: {ModernStyle.COLORS['bg_card']};
            }}
        """)
        
        # 검색 버튼 - toolbox 공용 컴포넌트 사용
        self.search_button = ModernPrimaryButton("🔍 검색")
        # 입력 필드와 동일한 높이로 설정
        self.search_button.setFixedHeight(input_height)
        
        search_input_layout.addWidget(self.search_input, 1)
        search_input_layout.addWidget(self.search_button)
        
        layout.addLayout(search_input_layout)
        
        card.setLayout(layout)
        return card
        
    def create_cafe_card(self) -> ModernCard:
        """카페 선택 카드 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        card = ModernCard("📍 카페 선택")
        layout = QVBoxLayout()
        layout_spacing = int(tokens.GAP_8 * scale)
        layout.setSpacing(layout_spacing)
        
        # 카페 선택 드롭다운 - 반응형 스케일링 적용
        self.cafe_combo = QComboBox()
        combo_padding_v = int(tokens.GAP_8 * scale)
        combo_padding_h = int(tokens.GAP_12 * scale)
        combo_border_width = int(2 * scale)
        combo_border_radius = int(tokens.GAP_6 * scale)
        combo_font_size = int(tokens.get_font_size('normal') * scale)
        combo_min_height = int(tokens.GAP_10 * scale)
        self.cafe_combo.setStyleSheet(f"""
            QComboBox {{
                padding: {combo_padding_v}px {combo_padding_h}px;
                border: {combo_border_width}px solid {ModernStyle.COLORS['border']};
                border-radius: {combo_border_radius}px;
                background-color: {ModernStyle.COLORS['bg_input']};
                font-size: {combo_font_size}px;
                min-height: {combo_min_height}px;
            }}
            QComboBox:focus {{
                border-color: {ModernStyle.COLORS['primary']};
            }}
        """)
        layout.addWidget(self.cafe_combo)
        
        # 선택된 카페 표시 라벨 - 반응형 스케일링 적용
        self.selected_cafe_label = QLabel("")
        self.selected_cafe_label.setWordWrap(True)  # 텍스트 줄바꿈 허용
        label_font_size = int(tokens.get_font_size('normal') * scale)
        label_padding = int(tokens.GAP_8 * scale)
        label_border_radius = int(tokens.GAP_4 * scale)
        label_margin_top = int(tokens.GAP_5 * scale)
        label_min_height = int(tokens.GAP_10 * scale)
        self.selected_cafe_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.COLORS['success']};
                font-weight: 600;
                font-size: {label_font_size}px;
                padding: {label_padding}px;
                background-color: rgba(16, 185, 129, 0.1);
                border-radius: {label_border_radius}px;
                margin-top: {label_margin_top}px;
                min-height: {label_min_height}px;
            }}
        """)
        self.selected_cafe_label.setVisible(False)  # 처음에는 숨김
        layout.addWidget(self.selected_cafe_label)
        
        # 게시판 로딩 위젯 (원본과 동일)
        self.board_loading_widget = self.create_loading_widget()
        layout.addWidget(self.board_loading_widget)
        
        card.setLayout(layout)
        return card
    
    def create_loading_widget(self) -> QWidget:
        """로딩 상태 표시 위젯 생성 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        loading_widget = QWidget()
        loading_layout = QHBoxLayout()
        margin_left = int(tokens.GAP_8 * scale)
        layout_spacing = int(tokens.GAP_6 * scale)
        loading_layout.setContentsMargins(margin_left, 0, 0, 0)
        loading_layout.setSpacing(layout_spacing)
        
        # 로딩 스피너 (회전하는 이모지) - 반응형 스케일링 적용
        self.loading_spinner = QLabel("🔄")
        spinner_font_size = int(tokens.get_font_size('normal') * scale)
        self.loading_spinner.setStyleSheet(f"""
            QLabel {{
                font-size: {spinner_font_size}px;
                color: {ModernStyle.COLORS['primary']};
            }}
        """)
        
        # 로딩 메시지 - 반응형 스케일링 적용
        self.loading_message = QLabel("게시판 로딩 중...")
        message_font_size = int(tokens.get_font_size('small') * scale)
        self.loading_message.setStyleSheet(f"""
            QLabel {{
                font-size: {message_font_size}px;
                color: {ModernStyle.COLORS['text_secondary']};
                font-style: italic;
            }}
        """)
        
        loading_layout.addWidget(self.loading_spinner)
        loading_layout.addWidget(self.loading_message)
        loading_layout.addStretch()
        
        loading_widget.setLayout(loading_layout)
        loading_widget.hide()  # 처음에는 숨김
        
        # 회전 애니메이션 타이머
        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self.rotate_spinner)
        self.spinner_icons = ["🔄", "🔃", "⚡", "💫"]
        self.spinner_index = 0
        
        return loading_widget
    
    def rotate_spinner(self):
        """스피너 회전 애니메이션"""
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_icons)
        self.loading_spinner.setText(self.spinner_icons[self.spinner_index])
    
    def show_board_loading(self, message="게시판 로딩 중..."):
        """게시판 로딩 표시 시작"""
        self.loading_message.setText(message)
        self.board_loading_widget.show()
        self.spinner_timer.start(500)  # 0.5초마다 회전
    
    def hide_board_loading(self):
        """게시판 로딩 표시 종료"""
        self.board_loading_widget.hide()
        self.spinner_timer.stop()
        self.spinner_index = 0
        self.loading_spinner.setText("🔄")
        
    def create_board_card(self) -> ModernCard:
        """게시판 선택 카드 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        card = ModernCard("📋 게시판 선택")
        layout = QVBoxLayout()
        layout_spacing = int(tokens.GAP_8 * scale)
        layout.setSpacing(layout_spacing)
        
        # 게시판 드롭다운
        self.board_combo = QComboBox()
        self.board_combo.setStyleSheet(self.cafe_combo.styleSheet())
        self.board_combo.setEnabled(False)  # 처음엔 비활성화
        
        # 선택된 게시판 정보 - 반응형 스케일링 적용
        self.selected_board_label = QLabel("")
        self.selected_board_label.setWordWrap(True)  # 텍스트 줄바꿈 허용
        board_label_font_size = int(tokens.get_font_size('normal') * scale)
        board_label_padding = int(tokens.GAP_8 * scale)
        board_label_border_radius = int(tokens.GAP_4 * scale)
        board_label_margin_top = int(tokens.GAP_5 * scale)
        board_label_min_height = int(tokens.GAP_10 * scale)
        self.selected_board_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.COLORS['success']};
                font-weight: 600;
                font-size: {board_label_font_size}px;
                padding: {board_label_padding}px;
                background-color: rgba(16, 185, 129, 0.1);
                border-radius: {board_label_border_radius}px;
                margin-top: {board_label_margin_top}px;
                min-height: {board_label_min_height}px;
            }}
        """)
        self.selected_board_label.setVisible(False)
        
        layout.addWidget(self.board_combo)
        layout.addWidget(self.selected_board_label)
        
        card.setLayout(layout)
        return card
        
    def create_settings_card(self) -> ModernCard:
        """추출 설정 카드 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        card = ModernCard("⚙️ 추출 설정")
        layout = QFormLayout()
        
        # 페이지 범위 설정 - 원본과 완전히 동일
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setMinimum(1)
        self.start_page_spin.setMaximum(9999)
        self.start_page_spin.setValue(1)  # config 제거로 하드코딩
        
        self.end_page_spin = QSpinBox()
        self.end_page_spin.setMinimum(1)
        self.end_page_spin.setMaximum(9999)
        self.end_page_spin.setValue(10)  # config 제거로 하드코딩
        
        # 반응형 스케일링 적용
        spin_padding = int(tokens.GAP_8 * scale)
        spin_border_width = int(2 * scale)
        spin_border_radius = int(tokens.GAP_6 * scale)
        spin_font_size = int(tokens.get_font_size('normal') * scale)
        spin_min_height = int(tokens.GAP_10 * scale)
        spin_button_width = int(tokens.GAP_16 * scale)
        
        for spin in [self.start_page_spin, self.end_page_spin]:
            spin.setStyleSheet(f"""
                QSpinBox {{
                    padding: {spin_padding}px;
                    border: {spin_border_width}px solid {ModernStyle.COLORS['border']};
                    border-radius: {spin_border_radius}px;
                    background-color: {ModernStyle.COLORS['bg_primary']};
                    font-size: {spin_font_size}px;
                    min-height: {spin_min_height}px;
                }}
                QSpinBox:focus {{
                    border-color: {ModernStyle.COLORS['primary']};
                }}
                QSpinBox::up-button {{
                    subcontrol-origin: border;
                    subcontrol-position: top right;
                    width: {spin_button_width}px;
                    background-color: rgba(240, 240, 240, 0.7);
                    border-bottom: 1px solid #ccc;
                }}
                QSpinBox::down-button {{
                    subcontrol-origin: border;
                    subcontrol-position: bottom right;
                    width: {spin_button_width}px;
                    background-color: rgba(240, 240, 240, 0.7);
                    border-top: 1px solid #ccc;
                }}
                QSpinBox::up-button:hover {{
                    background-color: rgba(220, 220, 220, 0.9);
                }}
                QSpinBox::down-button:hover {{
                    background-color: rgba(220, 220, 220, 0.9);
                }}
            """)
        
        layout.addRow("시작 페이지:", self.start_page_spin)
        layout.addRow("종료 페이지:", self.end_page_spin)
        
        card.setLayout(layout)
        return card
        
    def create_control_buttons(self) -> QWidget:
        """제어 버튼들 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_spacing = int(tokens.GAP_12 * scale)
        button_layout.setSpacing(button_spacing)
        
        # 추출 시작 버튼 - toolbox 공용 컴포넌트 사용, 반응형 스케일링 적용
        self.extract_button = ModernSuccessButton("🚀 추출 시작")
        button_height = int(tokens.GAP_15 * scale)
        self.extract_button.setFixedHeight(button_height)
        self.extract_button.setEnabled(False)  # 처음엔 비활성화
        
        # 정지 버튼 - toolbox 공용 컴포넌트 사용 (활성화 시에만 빨간색), 반응형 스케일링 적용
        self.stop_button = ModernCancelButton("⏹ 정지")
        self.stop_button.setFixedHeight(button_height)
        self.stop_button.setEnabled(False)  # 처음엔 비활성화
        
        button_layout.addWidget(self.extract_button)
        button_layout.addWidget(self.stop_button)
        
        return button_container
        
    def setup_connections(self):
        """시그널 연결"""
        self.search_button.clicked.connect(self.start_cafe_search)
        self.cafe_combo.currentIndexChanged.connect(self.on_cafe_selected)
        self.board_combo.currentIndexChanged.connect(self.on_board_selected)
        self.extract_button.clicked.connect(self.start_extraction)
        self.stop_button.clicked.connect(self.stop_extraction)
        self.search_input.returnPressed.connect(self.start_cafe_search)
    
    def start_cafe_search(self):
        """카페 검색 시작"""
        search_text = self.search_input.text().strip()
        if not search_text:
            ModernInfoDialog.warning(self, "검색어 입력 필요", "검색할 카페명 또는 URL을 입력해주세요.")
            return
        
        # 이미 워커가 실행 중인 경우 중단
        if self.unified_worker and self.unified_worker.isRunning():
            self.unified_worker.stop()
            self.unified_worker.wait()
        
        # 검색 재시도 관련 변수들 제거됨
        self.search_button.setEnabled(False)
        
        # 카페 검색 시작 단계 업데이트
        self.update_progress_step(0, "active", "카페 검색 중...")
        
        # 기존 카페 목록 클리어
        self.cafe_combo.clear()
        self.current_cafes.clear()
        self.current_boards.clear()
        self.board_combo.clear()
        self.board_combo.setEnabled(False)
        self.selected_cafe_label.setVisible(False)
        self.selected_board_label.setVisible(False)
        self.extract_button.setEnabled(False)
        
        log_manager.add_log(f"카페 검색 시작: {search_text}", "info")
        
        # 통합 워커로 카페 검색
        self.unified_worker = NaverCafeUnifiedWorker()
        self.unified_worker.setup_search_cafe(search_text)
        self.unified_worker.step_completed.connect(self.on_unified_step_completed)
        self.unified_worker.step_error.connect(self.on_unified_step_error)
        self.unified_worker.start()
    
    def on_unified_step_completed(self, step_name: str, result):
        """통합 워커 단계 완료 처리"""
        if step_name == "카페 검색":
            self.on_search_completed(result)
        elif step_name == "게시판 로딩":
            self.on_boards_loaded(result)
        elif step_name == "사용자 추출":
            self.on_extraction_completed(result)
    
    def on_unified_step_error(self, step_name: str, error_msg: str):
        """통합 워커 오류 처리"""
        if step_name == "카페 검색":
            self.on_search_error(error_msg)
        elif step_name == "게시판 로딩":
            self.on_board_loading_error(error_msg)
        elif step_name == "사용자 추출":
            self.on_extraction_error(error_msg)
    
        
    def on_cafe_selected(self, index):
        """카페 선택 시 처리 (원본과 동일)"""
        # 기본 선택 항목("카페를 선택해주세요...")을 선택한 경우
        if index <= 0:
            # 진행상황을 카페 선택 대기 상태로 설정
            self.update_progress_step(1, "active", "카페를 선택해주세요")
            self.update_progress_step(2, "pending")
            self.update_progress_step(3, "pending")
            self.update_progress_step(4, "pending")
            
            # 선택된 카페 표시 숨김
            self.selected_cafe_label.setVisible(False)
            
            # 게시판 로딩 표시 숨기기
            self.hide_board_loading()
            
            # 게시판 관련 UI 초기화
            self.board_combo.clear()
            self.current_boards.clear()
            self.board_combo.setEnabled(False)
            self.selected_board_label.setVisible(False)
            self.extract_button.setEnabled(False)
            return
            
        # 실제 카페 선택 (index - 1로 보정)
        if index - 1 >= len(self.current_cafes):
            return
            
        selected_cafe = self.current_cafes[index - 1]
        
        # 이미 게시판이 로딩된 카페를 다시 선택한 경우는 하위 단계 초기화 (원본과 동일)
        if hasattr(self, '_last_selected_cafe_index') and self._last_selected_cafe_index == index:
            if self.progress_steps[2]["status"] == "completed":
                # 이미 완료된 카페 재선택 시 하위 단계들 초기화
                self.update_progress_step(2, "pending")
                self.update_progress_step(3, "pending") 
                self.update_progress_step(4, "pending")
                
                # 게시판 UI 초기화
                self.board_combo.clear()
                self.current_boards.clear()
                self.board_combo.setEnabled(False)
                self.selected_board_label.setVisible(False)
                self.extract_button.setEnabled(False)
        
        self._last_selected_cafe_index = index
        
        # 카페 선택 완료 단계 업데이트 (원본과 동일)
        display_name = f"{selected_cafe.name}"
        if hasattr(selected_cafe, 'member_count') and selected_cafe.member_count:
            display_name += f" ({selected_cafe.member_count})"
        
        self.update_progress_step(1, "completed", f"선택됨: {display_name}")
        self.update_progress_step(2, "active", "게시판 목록을 불러오는 중...")
        
        # 선택된 카페 표시
        self.selected_cafe_label.setText(f"선택: {display_name}")
        self.selected_cafe_label.setVisible(True)
        
        # 게시판 로딩 표시 시작 (원본과 동일)
        self.show_board_loading(f"{selected_cafe.name}의 게시판을 불러오는 중...")
        
        # 게시판 로딩 시작 (통합 워커 사용)
        if self.unified_worker and self.unified_worker.isRunning():
            self.unified_worker.stop()
            self.unified_worker.wait()
        
        self.unified_worker = NaverCafeUnifiedWorker()
        self.unified_worker.setup_load_boards(selected_cafe)
        self.unified_worker.step_completed.connect(self.on_unified_step_completed)
        self.unified_worker.step_error.connect(self.on_unified_step_error)
        self.unified_worker.start()
        
        log_manager.add_log(f"카페 선택: {selected_cafe.name}", "info")
    
    def on_board_selected(self, index):
        """게시판 선택 시 처리 (원본과 동일)"""
        # 기본 선택 항목("게시판을 선택해주세요...")을 선택한 경우
        if index <= 0:
            # 진행상황을 게시판 선택 대기 상태로 설정
            self.update_progress_step(3, "active", "게시판을 선택해주세요")
            self.update_progress_step(4, "pending")
            
            # 선택된 게시판 표시 숨김
            self.selected_board_label.setVisible(False)
            
            # 추출 버튼 비활성화
            self.extract_button.setEnabled(False)
            return
            
        # 실제 게시판 선택 (index - 1로 보정)
        if index - 1 >= len(self.current_boards):
            return
            
        selected_board = self.current_boards[index - 1]
        
        # 게시판 선택 완료 단계 업데이트 (원본과 동일)
        board_display_name = selected_board.name
        if selected_board.article_count > 0:
            board_display_name += f" ({selected_board.article_count}개 게시글)"
        
        self.update_progress_step(3, "completed", f"선택됨: {board_display_name}")
        self.update_progress_step(4, "completed", "추출 준비 완료!")
        
        # 선택된 게시판 표시
        self.selected_board_label.setText(f"선택: {board_display_name}")
        self.selected_board_label.setVisible(True)
        
        # 추출 버튼 활성화
        self.extract_button.setEnabled(True)
    
    def load_boards_for_cafe(self, cafe_info: CafeInfo):
        """선택된 카페의 게시판 목록 로딩"""
        # 이미 워커가 실행 중인 경우 중단
        if self.unified_worker and self.unified_worker.isRunning():
            self.unified_worker.stop()
            self.unified_worker.wait()
        
        self.status_label.setText("게시판 목록 로딩 중...")
        
        # 기존 게시판 목록 클리어
        self.board_combo.clear()
        self.current_boards.clear()
        self.board_combo.setEnabled(False)
        self.selected_board_label.setVisible(False)
        self.extract_button.setEnabled(False)
        
        log_manager.add_log(f"게시판 목록 로딩 시작: {cafe_info.name}", "info")
        
        # 통합 워커로 게시판 로딩
        self.unified_worker = NaverCafeUnifiedWorker()
        self.unified_worker.setup_load_boards(cafe_info)
        self.unified_worker.step_completed.connect(self.on_unified_step_completed)
        self.unified_worker.step_error.connect(self.on_unified_step_error)
        self.unified_worker.start()
        
    def start_extraction(self):
        """추출 시작 - 원본과 동일한 유효성 검사"""
        # 유효성 검사
        cafe_index = self.cafe_combo.currentIndex()
        board_index = self.board_combo.currentIndex()
        
        # 카페 선택 확인 (인덱스 0은 안내 메시지)
        if cafe_index <= 0:
            ModernInfoDialog.warning(self, "카페 선택 필요", "카페를 먼저 선택해주세요.")
            self.cafe_combo.setFocus()
            return
            
        # 게시판 선택 확인 (인덱스 0은 안내 메시지)
        if board_index <= 0:
            ModernInfoDialog.warning(self, "게시판 선택 필요", "게시판을 선택해주세요.")
            self.board_combo.setFocus()
            return
        
        # 페이지 설정 검증
        if self.start_page_spin.value() > self.end_page_spin.value():
            ModernInfoDialog.warning(self, "페이지 설정 오류", "시작 페이지가 종료 페이지보다 클 수 없습니다.")
            self.start_page_spin.setFocus()
            return
        
        # 현재 카페/게시판 목록 확인
        if not self.current_cafes or not self.current_boards:
            ModernInfoDialog.warning(self, "데이터 오류", "카페와 게시판 정보를 다시 로딩해주세요.")
            return
        
        # 실제 인덱스 계산 (안내 메시지 때문에 -1)
        actual_cafe_index = cafe_index - 1
        actual_board_index = board_index - 1
        
        # 인덱스 범위 검증
        if actual_cafe_index >= len(self.current_cafes):
            ModernInfoDialog.warning(self, "카페 선택 오류", "선택된 카페 정보를 찾을 수 없습니다.")
            return
            
        if actual_board_index >= len(self.current_boards):
            ModernInfoDialog.warning(self, "게시판 선택 오류", "선택된 게시판 정보를 찾을 수 없습니다.")
            return
        
        # 작업 생성
        selected_cafe = self.current_cafes[actual_cafe_index]
        selected_board = self.current_boards[actual_board_index]
        
        extraction_task = ExtractionTask(
            cafe_info=selected_cafe,
            board_info=selected_board,
            start_page=self.start_page_spin.value(),
            end_page=self.end_page_spin.value()
        )
        
        # 새로운 추출 시작 - 기존 데이터 리셋 (CLAUDE.md: service 경유)
        self.service.clear_all_data()  # 기존 사용자 데이터 모두 삭제
        
        # UI 상태 변경
        self.extraction_in_progress = True
        self.extract_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # 진행상황 초기화
        for i in range(4):
            self.update_progress_step(i, "completed")
        self.update_progress_step(4, "active", "데이터를 추출하고 있습니다...")
        
        # 기존 데이터 리셋 시그널 발송 (테이블 클리어)
        self.data_cleared.emit()
        
        # 통합 워커로 추출 시작
        if self.unified_worker and self.unified_worker.isRunning():
            self.unified_worker.stop()
            self.unified_worker.wait()
            
        self.unified_worker = NaverCafeUnifiedWorker()
        self.unified_worker.setup_extract_users(selected_cafe, selected_board, extraction_task.start_page, extraction_task.end_page)
        self.unified_worker.step_completed.connect(self.on_unified_step_completed)
        self.unified_worker.step_error.connect(self.on_unified_step_error)
        self.unified_worker.progress_updated.connect(self.on_progress_updated)
        self.unified_worker.user_extracted.connect(self.on_user_extracted)
        
        # 시그널 발송
        self.extraction_started.emit()
        
        # 워커 시작
        self.unified_worker.start()
        
        page_range = f"{extraction_task.start_page}-{extraction_task.end_page}페이지"
        log_manager.add_log(f"사용자 추출 시작: {selected_cafe.name} > {selected_board.name} ({page_range})", "info")
    
    def stop_extraction(self):
        """추출 정지 - 원본과 동일한 처리"""
        # 수동 정지 플래그 설정
        self.is_manually_stopped = True
        log_manager.add_log("⏹️ 정지 버튼이 클릭되었습니다", "warning")
        
        if self.unified_worker and self.unified_worker.isRunning():
            log_manager.add_log("추출 중지 요청을 워커로 전달합니다", "warning")
            self.unified_worker.stop()
            
            # UI 상태 즉시 복원
            self.extract_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.extraction_in_progress = False
            
            # 진행상황 표시 업데이트
            for i in range(len(self.progress_steps)):
                if self.progress_steps[i]["status"] == "active":
                    self.update_progress_step(i, "error", "사용자에 의해 중지됨")
                    break
            
            # 정지 상태 메시지 표시 - 반응형 스케일링 적용
            self.status_label.setText("추출이 중지되었습니다")
            scale = tokens.get_screen_scale_factor()
            stop_font_size = int(tokens.get_font_size('normal') * scale)
            stop_padding = int(tokens.GAP_8 * scale)
            stop_border_radius = int(tokens.GAP_4 * scale)
            stop_margin = int(tokens.GAP_3 * scale)
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {ModernStyle.COLORS['danger']};
                    font-size: {stop_font_size}px;
                    font-weight: 600;
                    padding: {stop_padding}px;
                    background-color: rgba(239, 68, 68, 0.1);
                    border-radius: {stop_border_radius}px;
                    margin: {stop_margin}px 0;
                }}
            """)
            
            log_manager.add_log("✅ 추출이 중지되었습니다 (UI 상태 복원 완료)", "info")
        else:
            log_manager.add_log("❌ 추출 워커가 실행 중이지 않음", "error")
            # 그래도 UI 상태는 복원
            self.extract_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.extraction_in_progress = False
    
    
    def retry_search(self):
        """검색 재시도"""
        # TODO: 검색 재시도 로직 구현
        pass
    
    def on_progress_updated(self, progress: ExtractionProgress):
        """진행상황 업데이트"""
        # 상태 메시지 업데이트 - 원본과 동일한 형태
        if progress.status_message:
            # "최적화" 단어 제거하여 간단한 메시지로 표시
            status_msg = progress.status_message.replace("최적화 처리 중", "처리 중")
            status_msg = status_msg.replace("최적화", "")
            progress_msg = f"페이지 {progress.current_page}/{progress.total_pages} • API 호출 {progress.api_calls}회 • {status_msg}"
        else:
            progress_msg = f"페이지 {progress.current_page}/{progress.total_pages} • API 호출 {progress.api_calls}회"
        
        self.status_label.setText(progress_msg)
        
        # 상위 위젯에 전달
        self.extraction_progress_updated.emit(progress)
    
    def on_extraction_completed(self, result):
        """추출 완료 처리"""
        self.extraction_in_progress = False
        self.extract_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # 진행 단계 완료 표시
        user_count = result.total_users if hasattr(result, 'total_users') else len(result.get('users', []))
        self.update_progress_step(4, "completed", f"추출 완료! {user_count}명 추출")
        
        log_manager.add_log(f"카페 추출 완료: {user_count}명", "info")
        
        # 추출 기록 저장 (CLAUDE.md: service 경유)
        self.service.save_extraction_result(result, self.unified_worker)
        
        # 상위 위젯에 결과 전달
        self.extraction_completed.emit(result)
        
        # 다이얼로그 제거 - UI에 완료 메시지만 표시
    
# 비즈니스 로직 제거 - service.py로 이동됨
    
    def on_extraction_error(self, error_msg):
        """추출 오류 처리"""
        self.extraction_in_progress = False
        self.extract_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # 진행 단계 오류 표시
        self.update_progress_step(4, "error", "추출 오류 발생")
        
        log_manager.add_log(f"카페 추출 오류: {error_msg}", "error")
        
        # 상위 위젯에 오류 전달
        self.extraction_error.emit(error_msg)
        
        # 오류 다이얼로그
        dialog = ModernConfirmDialog(
            self,
            "추출 오류",
            f"추출 중 오류가 발생했습니다.\\n\\n{error_msg}",
            confirm_text="확인",
            cancel_text=None,
            icon="❌"
        )
        dialog.exec()
    
    def on_user_extracted(self, user):
        """개별 사용자 추출 시 실시간 업데이트 (CLAUDE.md: service 경유)"""
        # 서비스 경유로 데이터베이스에 추가
        self.service.add_extracted_user(user)
        
        # 상위 위젯에 전달
        self.user_extracted.emit(user)
    
    def clear_data(self):
        """데이터 초기화 (CLAUDE.md: service 경유)"""
        # 진행 중인 워커가 있으면 중단
        if self.unified_worker and self.unified_worker.isRunning():
            self.unified_worker.stop()
            self.unified_worker.wait()
            self.extraction_in_progress = False
        
        # 서비스 경유로 데이터 클리어
        self.service.clear_all_data()
        
        # UI 초기화
        self.reset_progress_steps()
        self.extract_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        # 선택된 카페/게시판 라벨 숨김
        self.selected_cafe_label.setVisible(False)
        self.selected_board_label.setVisible(False)
        
        # 클리어 시그널 발송
        self.data_cleared.emit()
        
        log_manager.add_log("카페 추출 데이터 전체 클리어 완료", "info")
    
    
    def on_search_completed(self, cafes: List[CafeInfo]):
        """카페 검색 완료 처리 (원본과 동일)"""
        self.search_button.setEnabled(True)
        
        if not cafes:
            self.update_progress_step(0, "error", "검색 결과 없음")
            ModernInfoDialog.warning(self, "검색 결과", "검색된 카페가 없습니다.")
            return
        
        # 검색 완료 단계 업데이트 (원본과 동일)
        self.update_progress_step(0, "completed", f"카페 {len(cafes)}개 검색 완료")
        self.update_progress_step(1, "active", "카페를 선택해주세요")
        
        # 카페 목록 업데이트
        self.current_cafes = cafes
        self.cafe_combo.clear()
        
        # URL로 검색한 경우와 키워드 검색한 경우 구분
        search_input = self.search_input.text().strip()
        if "cafe.naver.com" in search_input and len(cafes) == 1:
            # URL로 검색해서 카페가 1개만 나온 경우
            for cafe in cafes:
                cafe_text = cafe.name
                if cafe.member_count:
                    cafe_text += f" ({cafe.member_count})"
                self.cafe_combo.addItem(cafe_text)
            
            # 카페 선택 활성화 후 자동 선택
            self.cafe_combo.setEnabled(True)
            self.cafe_combo.setCurrentIndex(0)
            self.on_cafe_selected(1)  # 인덱스 1로 호출 (실제 첫 번째 카페)
        else:
            # 키워드 검색의 경우 사용자가 선택하도록 대기
            # 첫 번째 항목으로 선택 안내 메시지 추가
            self.cafe_combo.addItem("카페를 선택해주세요...")
            
            # 실제 카페 목록 추가
            for cafe in cafes:
                cafe_text = cafe.name
                if cafe.member_count:
                    cafe_text += f" ({cafe.member_count})"
                self.cafe_combo.addItem(cafe_text)
            
            # 카페 선택 활성화 후 기본 선택 항목 설정 (시그널 차단)
            self.cafe_combo.setEnabled(True)
            # 시그널을 일시적으로 차단하여 자동 선택 방지
            self.cafe_combo.blockSignals(True)
            self.cafe_combo.setCurrentIndex(0)
            self.cafe_combo.blockSignals(False)
        
        log_manager.add_log(f"카페 검색 완료: {len(cafes)}개 발견", "info")
    
    def on_search_error(self, error_msg: str):
        """카페 검색 오류 처리"""
        self.search_button.setEnabled(True)
        self.update_progress_step(0, "error", "검색 실패")
        
        ModernInfoDialog.error(self, "검색 오류", f"카페 검색 중 오류가 발생했습니다.\n\n{error_msg}")
        log_manager.add_log(f"카페 검색 오류: {error_msg}", "error")
    
    def on_boards_loaded(self, boards: List[BoardInfo]):
        """게시판 로딩 완료 처리 (원본과 동일)"""
        # 게시판 로딩 표시 숨기기 (원본과 동일)
        self.hide_board_loading()
        
        if not boards:
            self.update_progress_step(2, "error", "게시판 로딩 실패")
            ModernInfoDialog.warning(self, "게시판 로딩", "게시판 목록을 불러올 수 없습니다.")
            return
        
        # 게시판 로딩 완료 단계 업데이트 (원본과 동일)
        self.update_progress_step(2, "completed", f"게시판 {len(boards)}개 로딩 완료")
        self.update_progress_step(3, "active", "게시판을 선택해주세요")
        
        # 게시판 목록 업데이트
        self.current_boards = boards
        self.board_combo.clear()
        
        for board in boards:
            board_text = board.name
            if board.article_count > 0:
                board_text += f" ({board.article_count}개 게시글)"
            self.board_combo.addItem(board_text)
        
        # 게시판 선택 활성화
        self.board_combo.setEnabled(True)
        
        # 게시판 목록에 기본 선택 항목 추가
        self.board_combo.insertItem(0, "게시판을 선택해주세요...")
        self.board_combo.setCurrentIndex(0)
        
        log_manager.add_log(f"게시판 로딩 완료: {len(boards)}개 발견", "info")
    
    def on_board_loading_error(self, error_msg: str):
        """게시판 로딩 오류 처리"""
        # 게시판 로딩 표시 숨기기 (원본과 동일)
        self.hide_board_loading()
        
        self.update_progress_step(2, "error", "게시판 로딩 실패")
        
        ModernInfoDialog.error(self, "게시판 로딩 오류", f"게시판 목록을 불러오는 중 오류가 발생했습니다.\n\n{error_msg}")
        log_manager.add_log(f"게시판 로딩 오류: {error_msg}", "error")
    
    def closeEvent(self, event):
        """위젯 종료 시 리소스 정리 - 브라우저 완전 종료"""
        logger.info("네이버 카페 위젯 종료 시작")
        
        # 통합 워커 정리
        if self.unified_worker and self.unified_worker.isRunning():
            self.unified_worker.stop()
            self.unified_worker.wait()
            logger.info("네이버 카페 통합 워커 종료 완료")
        
        # 어댑터 페이지들 정리
        try:
            from .service import NaverCafeExtractionService
            service = NaverCafeExtractionService()
            if hasattr(service.adapter, 'cleanup_pages'):
                service.adapter.cleanup_pages()
        except Exception as e:
            logger.warning(f"어댑터 페이지 정리 중 오류: {e}")
        
        logger.info("네이버 카페 위젯 종료 완료")
        super().closeEvent(event)