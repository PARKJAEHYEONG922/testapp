"""
파워링크 자동화 메인 UI
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QLineEdit, QSpinBox, QPushButton,
                              QMessageBox, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from src.toolbox.ui_kit.modern_style import ModernStyle
from src.toolbox.ui_kit import tokens
from src.toolbox.ui_kit.components import ModernPrimaryButton, ModernDangerButton
from src.foundation.logging import get_logger
from src.foundation.config import config_manager
from .service import PowerlinkAutomationService
from .models import AutomationSettings
from .ui_table import KeywordTableWidget

logger = get_logger("powerlink_automation.ui_main")


class PowerlinkAutomationWidget(QWidget):
    """파워링크 자동화 메인 위젯"""
    
    def __init__(self):
        super().__init__()
        self.service = PowerlinkAutomationService()
        self.settings = AutomationSettings()
        self.keyword_table = None
        self.auto_bidding_worker = None
        self.timer = QTimer(self)
        self.remaining_seconds = 0
        
        self.setup_ui()
        self.setup_connections()
        self.load_api_credentials()
        self.update_ui_state()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setSpacing(tokens.GAP_16)
        layout.setContentsMargins(tokens.GAP_20, tokens.GAP_20, tokens.GAP_20, tokens.GAP_20)
        
        # 헤더
        header_layout = self._create_header()
        layout.addLayout(header_layout)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {ModernStyle.COLORS['border']};")
        layout.addWidget(separator)
        
        # 컨트롤 패널
        control_layout = self._create_control_panel()
        layout.addLayout(control_layout)
        
        # 키워드 테이블
        self.keyword_table = KeywordTableWidget(self.service)
        layout.addWidget(self.keyword_table)
        
        # 하단 액션 패널
        action_layout = self._create_action_panel()
        layout.addLayout(action_layout)
        
    def _create_header(self) -> QHBoxLayout:
        """헤더 생성"""
        layout = QHBoxLayout()
        
        # 제목
        title = QLabel("🚀 파워링크 자동입찰")
        title.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.COLORS['text_primary']};
                font-size: {tokens.FONT_HEADER}px;
                font-weight: 700;
                margin-bottom: {tokens.GAP_10}px;
            }}
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # 비즈머니 잔액 표시
        self.balance_label = QLabel("비즈머니: 조회 중...")
        self.balance_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.COLORS['text_secondary']};
                font-size: {tokens.FONT_NORMAL}px;
                padding: {tokens.GAP_8}px {tokens.GAP_12}px;
                background-color: {ModernStyle.COLORS['bg_muted']};
                border-radius: {tokens.RADIUS_SM}px;
            }}
        """)
        layout.addWidget(self.balance_label)
        
        
        return layout
        
    def _create_control_panel(self) -> QHBoxLayout:
        """컨트롤 패널 생성"""
        layout = QHBoxLayout()
        layout.setSpacing(tokens.GAP_16)
        
        # 캠페인 선택
        campaign_layout = QVBoxLayout()
        campaign_layout.addWidget(QLabel("캠페인"))
        self.campaign_combo = QComboBox()
        self.campaign_combo.setMinimumWidth(150)
        campaign_layout.addWidget(self.campaign_combo)
        layout.addLayout(campaign_layout)
        
        # 광고그룹 선택
        adgroup_layout = QVBoxLayout()
        adgroup_layout.addWidget(QLabel("광고그룹"))
        self.adgroup_combo = QComboBox()
        self.adgroup_combo.setMinimumWidth(150)
        adgroup_layout.addWidget(self.adgroup_combo)
        layout.addLayout(adgroup_layout)
        
        # 키워드 필터
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(QLabel("키워드 필터"))
        self.keyword_filter = QLineEdit()
        self.keyword_filter.setPlaceholderText("키워드로 필터링...")
        filter_layout.addWidget(self.keyword_filter)
        layout.addLayout(filter_layout)
        
        # 설정
        settings_layout = self._create_settings_panel()
        layout.addLayout(settings_layout)
        
        # 동기화 버튼
        self.sync_button = ModernPrimaryButton("🔄 동기화")
        layout.addWidget(self.sync_button)
        
        return layout
        
    def _create_settings_panel(self) -> QVBoxLayout:
        """설정 패널 생성"""
        layout = QVBoxLayout()
        
        # 대기시간 설정
        wait_layout = QHBoxLayout()
        wait_layout.addWidget(QLabel("대기시간"))
        self.wait_time_spin = QSpinBox()
        self.wait_time_spin.setRange(1, 20)
        self.wait_time_spin.setValue(self.settings.wait_time_minutes)
        self.wait_time_spin.setSuffix("분")
        wait_layout.addWidget(self.wait_time_spin)
        layout.addLayout(wait_layout)
        
        # 입찰 증가폭 설정
        increment_layout = QHBoxLayout()
        increment_layout.addWidget(QLabel("큰 증가폭"))
        self.increment_spin = QSpinBox()
        self.increment_spin.setRange(10, 300)
        self.increment_spin.setValue(self.settings.large_diff_increment)
        self.increment_spin.setSuffix("원")
        increment_layout.addWidget(self.increment_spin)
        layout.addLayout(increment_layout)
        
        return layout
        
    def _create_action_panel(self) -> QHBoxLayout:
        """액션 패널 생성"""
        layout = QHBoxLayout()
        
        # 상태 메시지
        self.status_label = QLabel("준비")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {ModernStyle.COLORS['text_secondary']};
                font-size: {tokens.FONT_NORMAL}px;
                padding: {tokens.GAP_8}px;
            }}
        """)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 자동입찰 시작/중지 버튼
        self.start_button = ModernPrimaryButton("▶️ 자동입찰 시작")
        self.stop_button = ModernDangerButton("⏹️ 중지")
        self.stop_button.setEnabled(False)
        
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        
        return layout
        
    def setup_connections(self):
        """시그널 연결"""
        self.sync_button.clicked.connect(self.sync_data)
        self.start_button.clicked.connect(self.start_auto_bidding)
        self.stop_button.clicked.connect(self.stop_auto_bidding)
        
        self.campaign_combo.currentTextChanged.connect(self.on_campaign_changed)
        self.adgroup_combo.currentTextChanged.connect(self.on_adgroup_changed)
        self.keyword_filter.textChanged.connect(self.on_filter_changed)
        
        self.wait_time_spin.valueChanged.connect(self.update_settings)
        self.increment_spin.valueChanged.connect(self.update_settings)
        
        self.timer.timeout.connect(self.update_timer_display)
        
    def load_api_credentials(self):
        """기존 API 설정 로드"""
        try:
            api_config = config_manager.load_api_config()
            
            if api_config.is_searchad_valid():
                self.service.set_credentials(
                    api_config.searchad_access_license,
                    api_config.searchad_secret_key, 
                    api_config.searchad_customer_id
                )
                logger.info("네이버 검색광고 API 설정 로드 완료")
            else:
                logger.warning("네이버 검색광고 API 설정이 없습니다")
                
        except Exception as e:
            logger.error(f"API 설정 로드 오류: {e}")
            
    def sync_data(self):
        """데이터 동기화"""
        if not self.service.credentials.is_valid():
            QMessageBox.warning(self, "경고", "먼저 메인 화면에서 API 설정을 완료해주세요.")
            return
            
        self.sync_button.setText("동기화 중...")
        self.sync_button.setEnabled(False)
        
        # 데이터 로드
        QTimer.singleShot(100, self._perform_sync)
        
    def _perform_sync(self):
        """실제 동기화 수행"""
        try:
            # 캠페인 로드
            campaigns = self.service.fetch_campaigns()
            self.campaign_combo.clear()
            self.campaign_combo.addItem("전체 캠페인", "")
            
            for campaign in campaigns:
                self.campaign_combo.addItem(campaign.name, campaign.ncc_campaign_id)
                
            self.keyword_table.set_campaigns(campaigns)
            
            self.sync_button.setText("동기화 완료")
            self.update_ui_state()
            
            QMessageBox.information(self, "완료", "데이터 동기화가 완료되었습니다.")
            
        except Exception as e:
            logger.error(f"동기화 오류: {e}")
            QMessageBox.critical(self, "오류", f"동기화 중 오류가 발생했습니다: {str(e)}")
            self.sync_button.setText("🔄 동기화")
            self.sync_button.setEnabled(True)
            
    def on_campaign_changed(self):
        """캠페인 변경 이벤트"""
        campaign_id = self.campaign_combo.currentData()
        if campaign_id is not None:
            self.keyword_table.load_adgroups(campaign_id)
            
    def on_adgroup_changed(self):
        """광고그룹 변경 이벤트"""
        adgroup_data = self.adgroup_combo.currentData()
        if adgroup_data:
            adgroup_id, campaign_id = adgroup_data
            self.keyword_table.load_keywords(campaign_id, adgroup_id)
            
    def on_filter_changed(self):
        """필터 변경 이벤트"""
        filter_text = self.keyword_filter.text()
        self.keyword_table.apply_filter(filter_text)
        
    def update_settings(self):
        """설정 업데이트"""
        self.settings.wait_time_minutes = self.wait_time_spin.value()
        self.settings.large_diff_increment = self.increment_spin.value()
        
    def start_auto_bidding(self):
        """자동입찰 시작"""
        selected_keywords = self.keyword_table.get_selected_keywords()
        if not selected_keywords:
            QMessageBox.warning(self, "경고", "입찰할 키워드를 선택해주세요.")
            return
            
        # 상한가 검증
        for keyword_info in selected_keywords:
            if keyword_info[10] <= 0:  # max_bid
                QMessageBox.warning(self, "상한가 오류", "모든 키워드의 상한가를 설정해주세요.")
                return
                
        from .worker import AutoBiddingWorker
        self.auto_bidding_worker = AutoBiddingWorker(
            selected_keywords, self.settings, self.service
        )
        
        # 시그널 연결
        self.auto_bidding_worker.rank_updated.connect(self.keyword_table.update_rank)
        self.auto_bidding_worker.bid_updated.connect(self.keyword_table.update_bid)
        self.auto_bidding_worker.remaining_seconds.connect(self.set_remaining_seconds)
        self.auto_bidding_worker.target_reached.connect(self.keyword_table.log_target_reached)
        self.auto_bidding_worker.status_message.connect(self.set_status_message)
        
        self.auto_bidding_worker.start()
        
        # UI 상태 변경
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.sync_button.setEnabled(False)
        
    def stop_auto_bidding(self):
        """자동입찰 중지"""
        if self.auto_bidding_worker:
            self.auto_bidding_worker.stop()
            self.auto_bidding_worker.wait()
            self.auto_bidding_worker = None
            
        self.timer.stop()
        self.remaining_seconds = 0
        self.update_timer_display()
        
        # UI 상태 복원
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.sync_button.setEnabled(True)
        self.set_status_message("자동입찰이 중지되었습니다.")
        
    def set_remaining_seconds(self, seconds: int):
        """남은 시간 설정"""
        if seconds > 0:
            self.remaining_seconds = seconds
            self.timer.start(1000)
        else:
            self.remaining_seconds = 0
            self.timer.stop()
            self.update_timer_display()
            
    def update_timer_display(self):
        """타이머 표시 업데이트"""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.status_label.setText(f"남은 시간: {self.remaining_seconds}초")
        else:
            self.status_label.setText("자동입찰이 중지되었습니다.")
            
    def set_status_message(self, message: str):
        """상태 메시지 설정"""
        self.status_label.setText(message)
        
    def update_balance(self):
        """비즈머니 잔액 업데이트"""
        if self.service.credentials.is_valid():
            balance = self.service.get_bizmoney_balance()
            self.balance_label.setText(f"비즈머니: {balance}원")
        else:
            self.balance_label.setText("비즈머니: 미인증")
            
    def update_ui_state(self):
        """UI 상태 업데이트"""
        is_authenticated = self.service.credentials.is_valid()
        
        self.sync_button.setEnabled(is_authenticated)
        self.start_button.setEnabled(is_authenticated)
        
        if is_authenticated:
            self.update_balance()
        else:
            self.balance_label.setText("비즈머니: 미인증")