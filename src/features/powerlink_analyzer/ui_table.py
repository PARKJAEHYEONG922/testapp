"""
파워링크 광고비 분석기 결과 위젯 (우측 패널)
분석 결과 테이블, 키워드 관리, 히스토리 기능을 포함
"""
from datetime import datetime, timedelta, timezone
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog
)
from PySide6.QtCore import Qt, Signal

from src.toolbox.ui_kit import ModernStyle, ModernTableWidget, tokens
from src.toolbox.ui_kit.components import ModernButton
from src.toolbox.formatters import format_int, format_float, format_price_krw
from src.desktop.common_log import log_manager
from src.foundation.logging import get_logger
from .models import KeywordAnalysisResult
from .service import powerlink_service, keyword_database

logger = get_logger("features.powerlink_analyzer.results_widget")



class PowerLinkSaveDialog(QDialog):
    """PowerLink 분석 저장 완료 다이얼로그"""
    
    def __init__(self, session_id: int, session_name: str, keyword_count: int, is_duplicate: bool = False, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.session_name = session_name
        self.keyword_count = keyword_count
        self.is_duplicate = is_duplicate
        self.setup_ui()
        
    def setup_ui(self):
        """UI 초기화 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        self.setWindowTitle("저장 완료")
        self.setModal(True)
        dialog_width = int(380 * scale)  # 반응형 크기
        dialog_height = int(200 * scale)  # 반응형 크기
        self.setFixedSize(dialog_width, dialog_height)
        
        # 메인 레이아웃 - 반응형 스케일링 적용
        layout = QVBoxLayout(self)
        spacing = int(tokens.GAP_15 * scale)
        margin_h = int(tokens.GAP_32 * scale)
        margin_v = int(tokens.GAP_24 * scale)
        layout.setSpacing(spacing)
        layout.setContentsMargins(margin_h, margin_v, margin_h, margin_v)
        
        # 체크 아이콘과 제목
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)
        
        # 체크 아이콘 - 반응형 스케일링 적용
        icon_label = QLabel("✅")
        icon_font_size = int(tokens.get_font_size('large') * scale)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: {icon_font_size}px;
                color: #10b981;
            }}
        """)
        title_layout.addWidget(icon_label)
        
        # 제목 텍스트 - 반응형 스케일링 적용
        title_label = QLabel("저장 완료")
        title_font_size = int(tokens.get_font_size('header') * scale)
        title_margin = int(tokens.GAP_8 * scale)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {title_font_size}px;
                font-weight: 700;
                color: {ModernStyle.COLORS['text_primary']};
                margin-left: {title_margin}px;
            }}
        """)
        title_layout.addWidget(title_label)
        
        layout.addLayout(title_layout)
        
        # 메인 메시지 (중복 여부에 따라 변경)
        if self.is_duplicate:
            message_text = "이미 데이터베이스에 기록이 저장되었습니다."
        else:
            message_text = "프로그램 데이터베이스에 기록이 저장되었습니다."
            
        message_label = QLabel(message_text)
        message_font_size = int(tokens.get_font_size('normal') * scale)
        message_padding = int(tokens.GAP_5 * scale)
        message_label.setStyleSheet(f"""
            QLabel {{
                font-size: {message_font_size}px;
                color: {ModernStyle.COLORS['text_primary']};
                text-align: center;
                padding: {message_padding}px;
            }}
        """)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)  # 자동 줄바꿈
        layout.addWidget(message_label)
        
        # 안내 메시지 - 반응형 스케일링 적용
        guide_label = QLabel("엑셀로 내보내기도 원하시면 내보내기 버튼을\n눌러주세요.")
        guide_font_size = int(tokens.get_font_size('normal') * scale)
        guide_padding = int(tokens.GAP_5 * scale)
        guide_label.setStyleSheet(f"""
            QLabel {{
                font-size: {guide_font_size}px;
                color: {ModernStyle.COLORS['text_secondary']};
                text-align: center;
                line-height: 1.5;
                padding: {guide_padding}px;
            }}
        """)
        guide_label.setAlignment(Qt.AlignCenter)
        guide_label.setWordWrap(True)  # 자동 줄바꿈
        layout.addWidget(guide_label)
        
        layout.addStretch()
        
        # 버튼들 - 반응형 스케일링 적용
        button_layout = QHBoxLayout()
        button_spacing = int(tokens.GAP_10 * scale)
        button_layout.setSpacing(button_spacing)
        
        # 엑셀 내보내기 버튼 (파란색) - 반응형 스케일링 적용
        button_height = int(tokens.GAP_40 * scale)
        button_width = int(tokens.GAP_130 * scale)
        self.export_button = ModernButton("📊 엑셀 내보내기", "primary")
        self.export_button.setMinimumHeight(button_height)
        self.export_button.setMinimumWidth(button_width)
        button_layout.addWidget(self.export_button)
        
        # 완료 버튼 (회색)
        self.complete_button = ModernButton("✅ 완료", "secondary")
        self.complete_button.setMinimumHeight(button_height)
        self.complete_button.setMinimumWidth(button_width)
        button_layout.addWidget(self.complete_button)
        
        layout.addLayout(button_layout)
        
        # 시그널 연결
        self.complete_button.clicked.connect(self.accept)
        self.export_button.clicked.connect(self.export_to_excel)
        
    def export_to_excel(self):
        """엑셀 내보내기 실행 (UI 로직만)"""
        try:
            # 현재 분석 결과 가져오기
            keywords_data = powerlink_service.get_all_keywords()
            
            # service에 위임 (오케스트레이션 + adapters 파일 I/O)
            success = powerlink_service.export_current_analysis_with_dialog(
                keywords_data=keywords_data,
                session_name=getattr(self, 'session_name', ''),
                parent_widget=self
            )
            
            if success:
                self.accept()  # 다이얼로그 종료
        
        except Exception as e:
            log_manager.add_log(f"PowerLink 엑셀 내보내기 UI 처리 실패: {e}", "error")
            




class PowerLinkResultsWidget(QWidget):
    """파워링크 분석 결과 위젯 (우측 패널)"""
    
    # 시그널 정의
    save_button_state_changed = Signal(bool)  # 저장 버튼 상태 변경
    clear_button_state_changed = Signal(bool)  # 클리어 버튼 상태 변경
    keyword_added = Signal(str)  # 키워드 추가됨
    keyword_updated = Signal(str, object)  # 키워드 데이터 업데이트됨
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.keywords_data = {}  # 키워드 데이터 참조
        
        # 히스토리 로드 플래그 초기화
        self.is_loaded_from_history = False
        self.first_activation = True  # 첫 번째 활성화 여부
        
        self.setup_ui()
        self.setup_connections()
        
        # 초기 히스토리 로드 (UI 생성 후) - 로그 표시하지 않음
        try:
            self.refresh_history_list(show_log=False)
        except Exception as e:
            logger.error(f"초기 히스토리 로드 실패: {e}")
        
    def setup_ui(self):
        """UI 초기화 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        layout = QVBoxLayout(self)
        spacing = int(tokens.GAP_15 * scale)
        layout.setSpacing(spacing)
        
        # 탭 위젯 생성 - 반응형 스케일링 적용
        self.tab_widget = QTabWidget()
        tab_radius = int(tokens.GAP_8 * scale)
        tab_padding = int(tokens.GAP_10 * scale)
        tab_button_padding_v = int(tokens.GAP_12 * scale)
        tab_button_padding_h = int(tokens.GAP_20 * scale)
        tab_margin = int(tokens.GAP_2 * scale)
        tab_font_size = int(tokens.get_font_size('normal') * scale)
        border_width = int(2 * scale)
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: {border_width}px solid {ModernStyle.COLORS['border']};
                border-radius: {tab_radius}px;
                background-color: {ModernStyle.COLORS['bg_card']};
                padding: {tab_padding}px;
            }}
            QTabBar::tab {{
                background-color: {ModernStyle.COLORS['bg_secondary']};
                color: {ModernStyle.COLORS['text_secondary']};
                padding: {tab_button_padding_v}px {tab_button_padding_h}px;
                margin-right: {tab_margin}px;
                border-top-left-radius: {tab_radius}px;
                border-top-right-radius: {tab_radius}px;
                font-weight: 600;
                font-size: {tab_font_size}px;
            }}
            QTabBar::tab:selected {{
                background-color: {ModernStyle.COLORS['primary']};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {ModernStyle.COLORS['primary_hover']};
                color: white;
            }}
        """)
        
        # 모바일 탭
        mobile_tab = self.create_mobile_tab()
        self.tab_widget.addTab(mobile_tab, "📱 모바일 분석")
        
        # PC 탭  
        pc_tab = self.create_pc_tab()
        self.tab_widget.addTab(pc_tab, "💻 PC 분석")
        
        # 이전 기록 탭
        history_tab = self.create_history_tab()
        self.tab_widget.addTab(history_tab, "📚 이전 기록")
        
        layout.addWidget(self.tab_widget)
        
        # 분석 관리 버튼들
        button_layout = QHBoxLayout()
        
        # 전체 클리어 버튼
        self.clear_button = ModernButton("🗑 전체 클리어", "warning")
        self.clear_button.setEnabled(False)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        # 현재 분석 저장 버튼
        self.save_analysis_button = ModernButton("💾 현재 분석 저장", "success")
        self.save_analysis_button.setEnabled(False)
        button_layout.addWidget(self.save_analysis_button)
        
        layout.addLayout(button_layout)
        
    def create_mobile_tab(self) -> QWidget:
        """모바일 탭 생성 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        spacing = int(10 * scale)
        layout.setSpacing(spacing)
        
        # 선택 삭제 버튼
        button_layout = QHBoxLayout()
        self.mobile_delete_button = ModernButton("🗑️ 선택 삭제", "danger")
        self.mobile_delete_button.setEnabled(False)
        button_layout.addWidget(self.mobile_delete_button)
        button_layout.addStretch()
        
        # 모바일 테이블
        self.mobile_table = self.create_analysis_table()
        
        layout.addLayout(button_layout)
        layout.addWidget(self.mobile_table)
        
        return tab
        
    def create_pc_tab(self) -> QWidget:
        """PC 탭 생성 - 반응형 스케일링 적용"""
        # 화면 스케일 팩터 가져오기
        scale = tokens.get_screen_scale_factor()
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        spacing = int(10 * scale)
        layout.setSpacing(spacing)
        
        # 선택 삭제 버튼
        button_layout = QHBoxLayout()
        self.pc_delete_button = ModernButton("🗑️ 선택 삭제", "danger")
        self.pc_delete_button.setEnabled(False)
        button_layout.addWidget(self.pc_delete_button)
        button_layout.addStretch()
        
        # PC 테이블
        self.pc_table = self.create_analysis_table()
        
        layout.addLayout(button_layout)
        layout.addWidget(self.pc_table)
        
        return tab
    
    def create_history_tab(self) -> QWidget:
        """이전 기록 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # 상단 버튼들
        button_layout = QHBoxLayout()
        
        self.delete_history_button = ModernButton("🗑️ 선택 삭제", "danger")
        self.delete_history_button.setEnabled(False)
        self.view_history_button = ModernButton("👀 보기", "primary")
        self.view_history_button.setEnabled(False)
        self.export_selected_history_button = ModernButton("💾 선택 저장", "success")
        self.export_selected_history_button.setEnabled(False)
        
        button_layout.addWidget(self.delete_history_button)
        button_layout.addWidget(self.export_selected_history_button)
        button_layout.addStretch()
        button_layout.addWidget(self.view_history_button)
        
        layout.addLayout(button_layout)
        
        # 이전 기록 테이블 (ModernTableWidget 사용)
        self.history_table = ModernTableWidget(
            columns=["", "세션명", "생성일시", "키워드 수"],
            has_checkboxes=True,
            has_header_checkbox=True
        )
        
        # 컬럼 너비 설정 (체크박스 컬럼 제외)
        header = self.history_table.horizontalHeader()
        # header.resizeSection(0, 50)   # 체크박스 컬럼 - ModernTableWidget에서 자동으로 80px 고정 처리
        header.resizeSection(1, 300)  # 세션명 컬럼  
        header.resizeSection(2, 150)  # 생성일시 컬럼
        header.resizeSection(3, 100)  # 키워드 수 컬럼
        header.setStretchLastSection(True)
        
        layout.addWidget(self.history_table)
        
        return tab
    
    def create_analysis_table(self) -> ModernTableWidget:
        """분석 결과 테이블 생성 (ModernTableWidget 사용)"""
        # 헤더 설정 (0번째는 체크박스 컬럼)
        headers = [
            "", "키워드", "월검색량", "클릭수", "클릭률", 
            "1p노출위치", "1등광고비", "최소노출가격", "추천순위", "상세"
        ]
        
        table = ModernTableWidget(
            columns=headers,
            has_checkboxes=True,
            has_header_checkbox=True
        )
        
        # 헤더 설정
        header = table.horizontalHeader()
        
        # 체크박스 컬럼은 ModernTableWidget에서 자동으로 80px 고정 처리됨
        
        # 컬럼 너비 설정 (0번은 체크박스, 1번부터 데이터 컬럼)
        header.resizeSection(1, 150)  # 키워드
        header.resizeSection(2, 80)   # 월검색량
        header.resizeSection(3, 60)   # 클릭수
        header.resizeSection(4, 60)   # 클릭률
        header.resizeSection(5, 90)   # 1p노출위치
        header.resizeSection(6, 90)   # 1등광고비
        header.resizeSection(7, 100)  # 최소노출가격
        header.resizeSection(8, 80)   # 추천순위
        header.resizeSection(9, 90)   # 상세
        
        # 마지막 컬럼(상세)이 남은 공간을 채우도록 설정 (전체화면에서 늘어남)
        from PySide6.QtWidgets import QHeaderView
        header.setSectionResizeMode(9, QHeaderView.Stretch)
        
        # ModernTableWidget에서 정렬 자동 활성화
        
        return table
    
    def setup_connections(self):
        """시그널 연결"""
        # 관리 버튼
        self.clear_button.clicked.connect(self.clear_all_analysis)
        self.save_analysis_button.clicked.connect(self.save_current_analysis)
        
        # 삭제 버튼
        self.mobile_delete_button.clicked.connect(lambda: self.delete_selected_keywords('mobile'))
        self.pc_delete_button.clicked.connect(lambda: self.delete_selected_keywords('pc'))
        
        # 히스토리 버튼
        self.delete_history_button.clicked.connect(self.delete_selected_history)
        self.view_history_button.clicked.connect(self.view_selected_history)
        self.export_selected_history_button.clicked.connect(self.export_selected_history)
        
        # ModernTableWidget 선택 상태 변경 시그널 연결
        self.mobile_table.selection_changed.connect(self.update_delete_button_state)
        self.pc_table.selection_changed.connect(self.update_delete_button_state)
        self.history_table.selection_changed.connect(self.update_history_button_state)
        
        # 탭 변경 시그널 연결 (이전기록 탭에서 저장 버튼 비활성화)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    
    def update_all_tables(self):
        """모든 테이블 업데이트"""
        self.update_mobile_table()
        self.update_pc_table()
        
    def update_mobile_table(self):
        """모바일 테이블 업데이트 (ModernTableWidget API 사용)"""
        mobile_sorted = powerlink_service.get_mobile_rankings()
        
        # 테이블 클리어
        self.mobile_table.clear_table()
        
        for result in mobile_sorted:
            
            # 데이터 준비
            keyword = result.keyword
            
            # 월검색량
            if result.mobile_search_volume >= 0:
                search_volume = format_int(result.mobile_search_volume)
            else:
                search_volume = "-"
            
            # 추천순위
            if result.mobile_recommendation_rank > 0:
                rank_text = f"{result.mobile_recommendation_rank}위"
            else:
                rank_text = "-"
            
            # 행 데이터 준비 (체크박스 제외)
            row_data = [
                keyword,  # 키워드
                search_volume,  # 월검색량
                format_float(result.mobile_clicks, precision=1) if result.mobile_clicks >= 0 else "-",  # 클릭수
                f"{format_float(result.mobile_ctr, precision=2)}%" if result.mobile_ctr >= 0 else "-",  # 클릭률
                f"{format_int(result.mobile_first_page_positions)}위까지" if result.mobile_first_page_positions >= 0 else "-",  # 1p노출위치
                format_price_krw(result.mobile_first_position_bid) if result.mobile_first_position_bid >= 0 else "-",  # 1등광고비
                format_price_krw(result.mobile_min_exposure_bid) if result.mobile_min_exposure_bid >= 0 else "-",  # 최소노출가격
                rank_text,  # 추천순위
                "상세"  # 상세 버튼
            ]
            
            # ModernTableWidget API 사용하여 행 추가 (반환값으로 행 번호 받기)
            row = self.mobile_table.add_row_with_data(row_data, checkable=True)
            
            # 상세 버튼 (원본과 동일한 초록색 스타일)
            detail_button = QPushButton("상세")
            detail_font_size = tokens.get_font_size('normal')
            detail_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 0px;
                    font-weight: 600;
                    font-size: {detail_font_size}px;
                    margin: 0px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: #059669;
                }}
                QPushButton:pressed {{
                    background-color: #047857;
                }}
            """)
            # 안전한 클로저 생성을 위해 람다로 래핑
            detail_button.clicked.connect(lambda checked, keyword=keyword: self._show_detail_by_keyword(keyword, 'mobile'))
            self.mobile_table.setCellWidget(row, 9, detail_button)
            
    def update_pc_table(self):
        """PC 테이블 업데이트 (ModernTableWidget API 사용)"""
        pc_sorted = powerlink_service.get_pc_rankings()
        
        # 테이블 클리어
        self.pc_table.clear_table()
        
        for result in pc_sorted:
            # 데이터 준비
            keyword = result.keyword
            
            # 월검색량
            if result.pc_search_volume >= 0:
                search_volume = format_int(result.pc_search_volume)
            else:
                search_volume = "-"
            
            # 추천순위
            if result.pc_recommendation_rank > 0:
                rank_text = f"{result.pc_recommendation_rank}위"
            else:
                rank_text = "-"
            
            # 행 데이터 준비 (체크박스 제외)
            row_data = [
                keyword,  # 키워드
                search_volume,  # 월검색량
                format_float(result.pc_clicks, precision=1) if result.pc_clicks >= 0 else "-",  # 클릭수
                f"{format_float(result.pc_ctr, precision=2)}%" if result.pc_ctr >= 0 else "-",  # 클릭률
                f"{format_int(result.pc_first_page_positions)}위까지" if result.pc_first_page_positions >= 0 else "-",  # 1p노출위치
                format_price_krw(result.pc_first_position_bid) if result.pc_first_position_bid >= 0 else "-",  # 1등광고비
                format_price_krw(result.pc_min_exposure_bid) if result.pc_min_exposure_bid >= 0 else "-",  # 최소노출가격
                rank_text,  # 추천순위
                "상세"  # 상세 버튼
            ]
            
            # ModernTableWidget API 사용하여 행 추가 (반환값으로 행 번호 받기)
            row = self.pc_table.add_row_with_data(row_data, checkable=True)
            
            # 상세 버튼 (원본과 동일한 초록색 스타일)
            detail_button = QPushButton("상세")
            detail_font_size = tokens.get_font_size('normal')
            detail_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 0px;
                    font-weight: 600;
                    font-size: {detail_font_size}px;
                    margin: 0px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: #059669;
                }}
                QPushButton:pressed {{
                    background-color: #047857;
                }}
            """)
            # 안전한 클로저 생성을 위해 람다로 래핑
            detail_button.clicked.connect(lambda checked, keyword=keyword: self._show_detail_by_keyword(keyword, 'pc'))
            self.pc_table.setCellWidget(row, 9, detail_button)
    
    
    def update_keyword_row_in_table(self, table: QTableWidget, keyword: str, result, device_type: str):
        """특정 키워드의 테이블 행 업데이트"""
        for row in range(table.rowCount()):
            keyword_item = table.item(row, 1)
            if keyword_item and keyword_item.text() == keyword:
                # 해당 행의 데이터 업데이트
                self.update_table_row_data(table, row, result, device_type)
                break
    
    def _safe_set_item_text(self, table: QTableWidget, row: int, col: int, text: str):
        """안전한 셀 텍스트 설정 (None 체크 후 아이템 생성)"""
        item = table.item(row, col)
        if item is None:
            item = QTableWidgetItem("")
            table.setItem(row, col, item)
        item.setText(text)
    
    def update_table_row_data(self, table: QTableWidget, row: int, result, device_type: str):
        """테이블의 특정 행 데이터 업데이트"""
        try:
            if device_type == 'mobile':
                # 모바일 데이터 업데이트
                self._safe_set_item_text(table, row, 2, format_int(result.mobile_search_volume) if result.mobile_search_volume >= 0 else "-")  # 월검색량
                self._safe_set_item_text(table, row, 3, format_float(result.mobile_clicks, precision=1) if result.mobile_clicks >= 0 else "-")  # 클릭수
                self._safe_set_item_text(table, row, 4, f"{format_float(result.mobile_ctr, precision=2)}%" if result.mobile_ctr >= 0 else "-")  # 클릭률
                self._safe_set_item_text(table, row, 5, f"{format_int(result.mobile_first_page_positions)}위까지" if result.mobile_first_page_positions >= 0 else "-")  # 1p노출위치
                self._safe_set_item_text(table, row, 6, format_price_krw(result.mobile_first_position_bid) if result.mobile_first_position_bid >= 0 else "-")  # 1등광고비
                self._safe_set_item_text(table, row, 7, format_price_krw(result.mobile_min_exposure_bid) if result.mobile_min_exposure_bid >= 0 else "-")  # 최소노출가격
                self._safe_set_item_text(table, row, 8, f"{result.mobile_recommendation_rank}위" if result.mobile_recommendation_rank > 0 else "-")  # 추천순위
            else:  # PC
                # PC 데이터 업데이트
                self._safe_set_item_text(table, row, 2, format_int(result.pc_search_volume) if result.pc_search_volume >= 0 else "-")  # 월검색량
                self._safe_set_item_text(table, row, 3, format_float(result.pc_clicks, precision=1) if result.pc_clicks >= 0 else "-")  # 클릭수
                self._safe_set_item_text(table, row, 4, f"{format_float(result.pc_ctr, precision=2)}%" if result.pc_ctr >= 0 else "-")  # 클릭률
                self._safe_set_item_text(table, row, 5, f"{format_int(result.pc_first_page_positions)}위까지" if result.pc_first_page_positions >= 0 else "-")  # 1p노출위치
                self._safe_set_item_text(table, row, 6, format_price_krw(result.pc_first_position_bid) if result.pc_first_position_bid >= 0 else "-")  # 1등광고비
                self._safe_set_item_text(table, row, 7, format_price_krw(result.pc_min_exposure_bid) if result.pc_min_exposure_bid >= 0 else "-")  # 최소노출가격
                self._safe_set_item_text(table, row, 8, f"{result.pc_recommendation_rank}위" if result.pc_recommendation_rank > 0 else "-")  # 추천순위
        except Exception as e:
            logger.error(f"테이블 행 {row} 업데이트 실패 ({device_type}): {e}")

    def add_keyword_to_table(self, table: ModernTableWidget, result, device_type: str, update_ui: bool = True):
        """테이블에 키워드 분석 결과 추가 (ModernTableWidget 완전 사용)"""
        try:
            # 디바이스별 데이터 준비
            if device_type == 'mobile':
                # 월검색량
                search_volume = f"{result.mobile_search_volume:,}" if hasattr(result, 'mobile_search_volume') and result.mobile_search_volume >= 0 else "-"
                
                # 클릭수
                clicks = f"{result.mobile_clicks:.1f}" if hasattr(result, 'mobile_clicks') and result.mobile_clicks is not None else "-"
                
                # 클릭률
                ctr = f"{result.mobile_ctr:.2f}%" if hasattr(result, 'mobile_ctr') and result.mobile_ctr is not None else "-"
                
                # 1p노출위치
                position = f"{result.mobile_first_page_positions}위까지" if hasattr(result, 'mobile_first_page_positions') and result.mobile_first_page_positions is not None else "-"
                
                # 1등광고비
                first_bid = f"{result.mobile_first_position_bid:,}원" if hasattr(result, 'mobile_first_position_bid') and result.mobile_first_position_bid is not None else "-"
                
                # 최소노출가격
                min_bid = f"{result.mobile_min_exposure_bid:,}원" if hasattr(result, 'mobile_min_exposure_bid') and result.mobile_min_exposure_bid is not None else "-"
                
                # 추천순위
                mobile_rank = getattr(result, 'mobile_recommendation_rank', 0) if hasattr(result, 'mobile_recommendation_rank') else 0
                rank = f"{mobile_rank}위" if mobile_rank > 0 else "-"
                
            else:  # PC
                # 월검색량
                search_volume = f"{result.pc_search_volume:,}" if hasattr(result, 'pc_search_volume') and result.pc_search_volume >= 0 else "-"
                
                # 클릭수
                clicks = f"{result.pc_clicks:.1f}" if hasattr(result, 'pc_clicks') and result.pc_clicks is not None else "-"
                
                # 클릭률
                ctr = f"{result.pc_ctr:.2f}%" if hasattr(result, 'pc_ctr') and result.pc_ctr is not None else "-"
                
                # 1p노출위치
                position = f"{result.pc_first_page_positions}위까지" if hasattr(result, 'pc_first_page_positions') and result.pc_first_page_positions is not None else "-"
                
                # 1등광고비
                first_bid = f"{result.pc_first_position_bid:,}원" if hasattr(result, 'pc_first_position_bid') and result.pc_first_position_bid is not None else "-"
                
                # 최소노출가격
                min_bid = f"{result.pc_min_exposure_bid:,}원" if hasattr(result, 'pc_min_exposure_bid') and result.pc_min_exposure_bid is not None else "-"
                
                # 추천순위
                pc_rank = getattr(result, 'pc_recommendation_rank', 0) if hasattr(result, 'pc_recommendation_rank') else 0
                rank = f"{pc_rank}위" if pc_rank > 0 else "-"
            
            # 행 데이터 준비 (체크박스 제외)
            row_data = [
                result.keyword,    # 키워드
                search_volume,     # 월검색량
                clicks,           # 클릭수
                ctr,              # 클릭률
                position,         # 1p노출위치
                first_bid,        # 1등광고비
                min_bid,          # 최소노출가격
                rank,             # 추천순위
                "상세"            # 상세 버튼
            ]
            
            # ModernTableWidget API 사용하여 행 추가 (반환값으로 행 번호 받기)
            row = table.add_row_with_data(row_data, checkable=True)
            
            # 상세 버튼 추가 (9번 컬럼)
            detail_button = QPushButton("상세")
            detail_button_font_size = tokens.get_font_size('normal')
            detail_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 0px;
                    font-weight: 600;
                    font-size: {detail_button_font_size}px;
                    margin: 0px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: #059669;
                }}
                QPushButton:pressed {{
                    background-color: #047857;
                }}
            """)
            # 안전한 클로저 생성을 위해 람다로 래핑  
            detail_button.clicked.connect(lambda checked, keyword=result.keyword: self._show_detail_by_keyword(keyword, device_type))
            table.setCellWidget(row, 9, detail_button)
            
            # UI 업데이트 (rebuild 중에는 스킵)
            if update_ui:
                # 버튼 상태 업데이트
                self.update_delete_button_state()
                
                # 상태 표시 업데이트
                self.update_status_display()
                
        except Exception as e:
            logger.error(f"테이블 행 추가 실패: row {table.rowCount()}, device {device_type}: {e}")
            raise

    def _show_detail_by_keyword(self, keyword: str, device_type: str):
        """키워드 이름으로 상세 정보 표시 - 간단하고 확실한 방식"""
        try:
            # 서비스에서 해당 키워드의 데이터 조회
            service_keywords = powerlink_service.get_all_keywords()
            if keyword not in service_keywords:
                logger.error(f"키워드를 찾을 수 없음: {keyword}")
                return
            
            result = service_keywords[keyword]
            self.show_bid_details_improved(keyword, result, device_type)
            
        except Exception as e:
            logger.error(f"상세 정보 표시 실패 ({keyword}): {e}")

    def show_bid_details(self, keyword: str, result, device_type: str):
        """입찰가 상세 정보 표시 - 개선된 다이얼로그 사용 (하위 호환용)"""
        self.show_bid_details_improved(keyword, result, device_type)
    
    def update_delete_button_state(self):
        """삭제 버튼 상태 업데이트 및 헤더 체크박스 상태 업데이트"""
        # 모바일 테이블 체크 상태 확인 (ModernTableWidget API 사용)
        mobile_checked_rows = self.mobile_table.get_checked_rows()
        mobile_checked_count = len(mobile_checked_rows)
        mobile_has_checked = mobile_checked_count > 0
        
        # PC 테이블 체크 상태 확인 (ModernTableWidget API 사용)
        pc_checked_rows = self.pc_table.get_checked_rows()
        pc_checked_count = len(pc_checked_rows)
        pc_has_checked = pc_checked_count > 0
                
        # 버튼 상태 업데이트 (체크된 개수 표시)
        if mobile_has_checked:
            self.mobile_delete_button.setText(f"🗑️ 선택 삭제({mobile_checked_count})")
            self.mobile_delete_button.setEnabled(True)
        else:
            self.mobile_delete_button.setText("🗑️ 선택 삭제")
            self.mobile_delete_button.setEnabled(False)
            
        if pc_has_checked:
            self.pc_delete_button.setText(f"🗑️ 선택 삭제({pc_checked_count})")
            self.pc_delete_button.setEnabled(True)
        else:
            self.pc_delete_button.setText("🗑️ 선택 삭제")
            self.pc_delete_button.setEnabled(False)
        
        # 클리어 버튼 상태 업데이트 (테이블에 데이터가 있으면 활성화)
        mobile_total_rows = self.mobile_table.rowCount()
        pc_total_rows = self.pc_table.rowCount()
        has_data = mobile_total_rows > 0 or pc_total_rows > 0
        self.clear_button.setEnabled(has_data)
    
    def update_history_button_state(self):
        """히스토리 버튼 상태 업데이트 (ModernTableWidget API 사용)"""
        # ✅ 체크박스 기준으로 변경
        checked_rows = self.history_table.get_checked_rows()
        checked_count = len(checked_rows)

        has_selection = checked_count > 0
        self.delete_history_button.setEnabled(has_selection)
        self.export_selected_history_button.setEnabled(has_selection)

        # 보기 버튼: 정확히 1개 체크 시 활성화
        self.view_history_button.setEnabled(checked_count == 1)

        # 버튼 텍스트 업데이트
        if checked_count > 0:
            self.delete_history_button.setText(f"🗑️ 선택 삭제 ({checked_count})")
            self.export_selected_history_button.setText(f"💾 선택 저장 ({checked_count})")
        else:
            self.delete_history_button.setText("🗑️ 선택 삭제")
            self.export_selected_history_button.setText("💾 선택 저장")

        self.view_history_button.setText("👀 보기")

    def update_status_display(self):
        """상태 표시 업데이트"""
        # 키워드 개수 업데이트 로직 (필요시 구현)
        pass

    
    
    
    def refresh_history_list(self, show_log=True):
        """히스토리 목록 새로고침"""
        try:
            # Service를 통한 히스토리 조회 (UI → Service 위임)
            sessions = powerlink_service.get_analysis_history_sessions()
            
            if not hasattr(self, 'history_table') or self.history_table is None:
                logger.error("history_table이 초기화되지 않음")
                return
                
            # ModernTableWidget 사용: 기존 데이터 클리어
            self.history_table.clear_table()
            
            for session in sessions:
                # 생성일시 (한국시간으로 변환 - 타임존 안전)
                created_at = session['created_at']
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at)
                    # naive datetime이면 UTC로 가정
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    # KST로 변환
                    kst_time = dt.astimezone(timezone(timedelta(hours=9)))
                else:
                    # 이미 datetime 객체인 경우
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    kst_time = created_at.astimezone(timezone(timedelta(hours=9)))
                
                # ModernTableWidget.add_row_with_data 사용
                row_index = self.history_table.add_row_with_data([
                    session['session_name'],
                    kst_time.strftime('%Y-%m-%d %H:%M:%S'),
                    str(session['keyword_count'])
                ])
                
                # 세션 ID를 세션명 아이템에 저장
                session_name_item = self.history_table.item(row_index, 1)
                if session_name_item:
                    session_name_item.setData(Qt.UserRole, session['id'])
                
            if show_log:
                log_manager.add_log(f"파워링크 히스토리 로드됨: {len(sessions)}개 세션", "info")
            
        except Exception as e:
            log_manager.add_log(f"PowerLink 히스토리 새로고침 실패: {e}", "error")
    
    def delete_selected_history(self):
        """선택된 히스토리 삭제"""
        try:
            # 선택된 세션 ID 목록 가져오기 (ModernTableWidget API 사용)
            checked_rows = self.history_table.get_checked_rows()
            
            if not checked_rows:
                return
            
            # 모던 다이얼로그로 확인 (선택삭제 버튼 근처에 표시)
            from src.toolbox.ui_kit.modern_dialog import ModernConfirmDialog
            dialog = ModernConfirmDialog(
                self, 
                "히스토리 삭제 확인", 
                f"선택된 {len(checked_rows)}개의 분석 기록을 삭제하시겠습니까?\n\n"
                f"이 작업은 되돌릴 수 없습니다.", 
                confirm_text="삭제", 
                cancel_text="취소", 
                icon="🗑️"
            )
            
            if dialog.exec() == ModernConfirmDialog.Accepted:
                # 선택된 세션들의 session_id 추출
                session_ids_to_delete = []
                
                for row in checked_rows:
                    # 테이블에서 session_id 가져오기 (UserRole로 저장된 데이터)
                    session_name_item = self.history_table.item(row, 1)  # 세션명 열
                    if session_name_item:
                        session_id = session_name_item.data(Qt.UserRole)
                        if session_id:
                            session_ids_to_delete.append(session_id)
                
                # Service를 통한 세션 삭제 (UI → Service 위임)
                if session_ids_to_delete:
                    success = powerlink_service.delete_analysis_history_sessions(session_ids_to_delete)
                    if success:
                        # 히스토리 새로고침
                        self.refresh_history_list()
                else:
                    log_manager.add_log("PowerLink 히스토리 삭제 실패: session_id를 찾을 수 없음", "warning")
                
        except Exception as e:
            log_manager.add_log(f"PowerLink 히스토리 삭제 실패: {e}", "error")
    
    def view_selected_history(self):
        """선택된 히스토리 보기 - 모바일/PC 분석 탭에 다시 로드 (ModernTableWidget API 사용)"""
        try:
            # ModernTableWidget API를 사용하여 선택된 행 확인
            selected_rows = self.history_table.get_checked_rows()
            
            if len(selected_rows) != 1:
                from src.toolbox.ui_kit.modern_dialog import ModernInfoDialog
                if len(selected_rows) == 0:
                    ModernInfoDialog.warning(self, "선택 없음", "보려는 기록을 선택해주세요.")
                else:
                    ModernInfoDialog.warning(self, "선택 오류", "하나의 기록만 선택해주세요.")
                return
            
            # 선택된 행의 세션 데이터 가져오기
            row = selected_rows[0]
            session_name_item = self.history_table.item(row, 1)
            
            if not session_name_item:
                from src.toolbox.ui_kit.modern_dialog import ModernInfoDialog
                ModernInfoDialog.warning(self, "데이터 오류", "선택된 기록의 데이터를 찾을 수 없습니다.")
                return
            
            selected_session_id = session_name_item.data(Qt.UserRole)
            selected_session_name = session_name_item.text()
            
            if not selected_session_id:
                from src.toolbox.ui_kit.modern_dialog import ModernInfoDialog
                ModernInfoDialog.warning(self, "데이터 오류", "세션 ID를 찾을 수 없습니다.")
                return
            
            # service를 통해 히스토리 세션 데이터 로드
            loaded_keywords_data = powerlink_service.load_history_session_data(selected_session_id)
            
            if not loaded_keywords_data:
                log_manager.add_log(f"PowerLink 히스토리 로드 실패: 키워드 데이터 없음 - {selected_session_name}", "error")
                return
            
            # 기존 데이터 초기화 및 새 데이터 설정 (서비스 통해)
            self.keywords_data.clear()
            powerlink_service.clear_all_keywords()
            
            # 새 데이터 설정
            self.keywords_data = loaded_keywords_data
            powerlink_service.set_keywords_data(loaded_keywords_data)
            
            # 히스토리에서 로드된 데이터임을 표시 (중복 저장 방지)
            self.is_loaded_from_history = True
            self.loaded_session_id = selected_session_id
            
            # 히스토리 로드 시에는 서비스 데이터를 직접 테이블에 반영 (강제 실행)
            self.refresh_tables_from_database(force=True)
            
            # 즉시 버튼 상태만 업데이트
            self.update_save_button_state()
            
            # 모바일 분석 탭으로 자동 이동
            self.tab_widget.setCurrentIndex(0)  # 모바일 분석 탭
            
            # 성공 메시지 표시
            from src.toolbox.ui_kit.modern_dialog import ModernInfoDialog
            ModernInfoDialog.success(
                self, 
                "기록 로드 완료", 
                f"'{selected_session_name}' 세션이 현재 분석으로 로드되었습니다.\n\n📊 {len(loaded_keywords_data)}개 키워드\n📱 모바일/PC 탭에서 확인하실 수 있습니다."
            )
            
            log_manager.add_log(f"PowerLink 히스토리 로드 완료: {selected_session_name} ({len(loaded_keywords_data)}개 키워드)", "info")
                
        except Exception as e:
            log_manager.add_log(f"PowerLink 히스토리 보기 실패: {e}", "error")
    
    
    
    def _rebuild_tables_from_current_data(self):
        """테이블 중심 간단 재구성 - 테이블에 있는 키워드들만으로 처리"""
        try:
            # 1. 현재 테이블에서 키워드 목록 추출
            current_keywords = set()
            
            # 모바일 테이블에서 키워드 추출
            for row in range(self.mobile_table.rowCount()):
                keyword_item = self.mobile_table.item(row, 1)  # 키워드 컬럼
                if keyword_item:
                    current_keywords.add(keyword_item.text())
            
            # PC 테이블에서도 키워드 추출 (중복 제거를 위해 set 사용)
            for row in range(self.pc_table.rowCount()):
                keyword_item = self.pc_table.item(row, 1)  # 키워드 컬럼  
                if keyword_item:
                    current_keywords.add(keyword_item.text())
            
            logger.info(f"테이블에서 추출된 키워드: {len(current_keywords)}개")
            
            # 2. 서비스에서 해당 키워드들의 데이터만 가져오기
            service_keywords = powerlink_service.get_all_keywords()
            filtered_keywords = []
            
            for keyword in current_keywords:
                if keyword in service_keywords:
                    filtered_keywords.append(service_keywords[keyword])
                else:
                    logger.warning(f"서비스에서 키워드를 찾을 수 없음: {keyword}")
            
            logger.info(f"서비스에서 찾은 키워드: {len(filtered_keywords)}개")
            
            # 3. 테이블 클리어 후 재구성
            self.mobile_table.clear_table()
            self.pc_table.clear_table()
            
            # 4. 필터된 키워드들로 테이블 재구성 (상세 버튼 포함)
            for result in filtered_keywords:
                self._add_keyword_to_both_tables(result)
            
            logger.info(f"테이블 재구성 완료: {len(filtered_keywords)}개 키워드")
            
        except Exception as e:
            logger.error(f"테이블 재구성 실패: {e}")
    
    def _add_keyword_to_both_tables(self, result):
        """키워드를 모바일/PC 테이블 모두에 추가 (상세 버튼 포함)"""
        try:
            # 모바일 테이블 추가
            mobile_search_volume = format_int(result.mobile_search_volume) if result.mobile_search_volume >= 0 else "-"
            mobile_rank_text = f"{result.mobile_recommendation_rank}위" if result.mobile_recommendation_rank > 0 else "-"
            
            mobile_row_data = [
                result.keyword,
                mobile_search_volume,
                format_float(result.mobile_clicks, precision=1) if result.mobile_clicks >= 0 else "-",
                f"{format_float(result.mobile_ctr, precision=2)}%" if result.mobile_ctr >= 0 else "-",
                f"{format_int(result.mobile_first_page_positions)}위까지" if result.mobile_first_page_positions >= 0 else "-",
                format_price_krw(result.mobile_first_position_bid) if result.mobile_first_position_bid >= 0 else "-",
                format_price_krw(result.mobile_min_exposure_bid) if result.mobile_min_exposure_bid >= 0 else "-",
                mobile_rank_text,
                "상세"
            ]
            
            mobile_row = self.mobile_table.add_row_with_data(mobile_row_data, checkable=True)
            
            # 모바일 상세 버튼 추가
            mobile_detail_button = QPushButton("상세")
            mobile_detail_font_size = tokens.get_font_size('normal')
            mobile_detail_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 0px;
                    font-weight: 600;
                    font-size: {mobile_detail_font_size}px;
                    margin: 0px;
                    padding: 0px;
                }}
                QPushButton:hover {{ background-color: #059669; }}
                QPushButton:pressed {{ background-color: #047857; }}
            """)
            # 키워드 이름만 전달 - 클릭 시 서비스에서 데이터 조회
            mobile_detail_button.clicked.connect(lambda checked, keyword=result.keyword: self._show_detail_by_keyword(keyword, 'mobile'))
            self.mobile_table.setCellWidget(mobile_row, 9, mobile_detail_button)
            
            # PC 테이블 추가  
            pc_search_volume = format_int(result.pc_search_volume) if result.pc_search_volume >= 0 else "-"
            pc_rank_text = f"{result.pc_recommendation_rank}위" if result.pc_recommendation_rank > 0 else "-"
            
            pc_row_data = [
                result.keyword,
                pc_search_volume,
                format_float(result.pc_clicks, precision=1) if result.pc_clicks >= 0 else "-",
                f"{format_float(result.pc_ctr, precision=2)}%" if result.pc_ctr >= 0 else "-",
                f"{format_int(result.pc_first_page_positions)}위까지" if result.pc_first_page_positions >= 0 else "-",
                format_price_krw(result.pc_first_position_bid) if result.pc_first_position_bid >= 0 else "-",
                format_price_krw(result.pc_min_exposure_bid) if result.pc_min_exposure_bid >= 0 else "-",
                pc_rank_text,
                "상세"
            ]
            
            pc_row = self.pc_table.add_row_with_data(pc_row_data, checkable=True)
            
            # PC 상세 버튼 추가
            pc_detail_button = QPushButton("상세")
            pc_detail_font_size = tokens.get_font_size('normal')
            pc_detail_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 0px;
                    font-weight: 600;
                    font-size: {pc_detail_font_size}px;
                    margin: 0px;
                    padding: 0px;
                }}
                QPushButton:hover {{ background-color: #059669; }}
                QPushButton:pressed {{ background-color: #047857; }}
            """)
            # 키워드 이름만 전달 - 클릭 시 서비스에서 데이터 조회
            pc_detail_button.clicked.connect(lambda checked, keyword=result.keyword: self._show_detail_by_keyword(keyword, 'pc'))
            self.pc_table.setCellWidget(pc_row, 9, pc_detail_button)
            
        except Exception as e:
            logger.error(f"키워드 테이블 추가 실패 ({result.keyword}): {e}")
    
    def export_selected_history(self):
        """선택된 히스토리 엑셀 내보내기 (UI 로직만)"""
        try:
            # 선택된 세션 정보 가져오기 (ModernTableWidget API 사용)
            selected_sessions = []
            for row in self.history_table.get_checked_rows():
                # 세션 ID 가져오기 (세션명 아이템에서)
                session_name_item = self.history_table.item(row, 1)
                session_id = session_name_item.data(Qt.UserRole)
                session_name = session_name_item.text()
                created_at = self.history_table.item(row, 2).text()
                selected_sessions.append({
                    'id': session_id,
                    'name': session_name,
                    'created_at': created_at
                })
            
            if not selected_sessions:
                return
            
            # service에 위임 (오케스트레이션 + adapters 파일 I/O)
            reference_widget = getattr(self, 'export_selected_history_button', None)
            powerlink_service.export_selected_history_with_dialog(
                sessions_data=selected_sessions,
                parent_widget=self,
                reference_widget=reference_widget
            )
            
        except Exception as e:
            log_manager.add_log(f"PowerLink 히스토리 내보내기 UI 처리 실패: {e}", "error")
    
    def update_button_states(self):
        """버튼 상태 업데이트"""
        has_data = bool(self.keywords_data)
        
        # 테이블에도 데이터가 있는지 확인
        if not has_data:
            if (hasattr(self, 'pc_table') and self.pc_table.rowCount() > 0) or \
               (hasattr(self, 'mobile_table') and self.mobile_table.rowCount() > 0):
                has_data = True
                
        self.save_analysis_button.setEnabled(has_data)
        self.clear_button.setEnabled(has_data)
        
        # 시그널 발생
        self.save_button_state_changed.emit(has_data)
        self.clear_button_state_changed.emit(has_data)
    
    # Legacy header checkbox methods removed - ModernTableWidget handles automatically
    
    def on_tab_changed(self, index):
        """탭 변경 시 처리"""
        # 이전기록 탭(index 2)에서 저장 버튼 비활성화
        if index == 2:  # 이전기록 탭
            self.save_analysis_button.setEnabled(False)
        else:  # 모바일 분석(0) 또는 PC 분석(1) 탭
            self.update_save_button_state()
    
    def update_save_button_state(self):
        """저장 버튼 상태 업데이트"""
        try:
            # self.keywords_data와 서비스 키워드 둘 다 확인
            local_count = len(self.keywords_data) if hasattr(self, 'keywords_data') else 0
            service_count = len(powerlink_service.get_all_keywords())
            has_data = max(local_count, service_count) > 0
            
            self.save_analysis_button.setEnabled(has_data)
            self.clear_button.setEnabled(has_data)
            
            # 간단한 텍스트로 고정 (카운트 제거)
            self.save_analysis_button.setText("💾 현재 분석 저장")
                
        except Exception as e:
            logger.error(f"저장 버튼 상태 업데이트 실패: {e}")
    
    def on_analysis_started(self):
        """분석 시작 시 저장 버튼 비활성화"""
        # 새로운 분석 시작 시 히스토리 플래그 초기화
        self.is_loaded_from_history = False
        if hasattr(self, 'loaded_session_id'):
            delattr(self, 'loaded_session_id')
        
        self.save_analysis_button.setEnabled(False)
        self.save_analysis_button.setText("💾 분석 중...")
        log_manager.add_log("PowerLink 분석 시작 - 저장 버튼 비활성화", "info")
    
    def on_analysis_finished(self):
        """분석 완료 시 저장 버튼 활성화"""
        self.save_analysis_button.setText("💾 현재 분석 저장")
        # 저장 가능한 데이터가 있으면 버튼 활성화
        self.update_save_button_state()
        log_manager.add_log("PowerLink 분석 완료 - 저장 버튼 상태 업데이트", "info")
    
    def save_current_analysis(self):
        """현재 분석 결과 저장 - service 위임"""
        try:
            # 히스토리에서 로드된 데이터인지 확인
            if hasattr(self, 'is_loaded_from_history') and self.is_loaded_from_history:
                from src.toolbox.ui_kit.modern_dialog import ModernConfirmDialog
                dialog = ModernConfirmDialog(
                    self,
                    "저장 불가",
                    "이미 저장된 히스토리 데이터입니다.\n\n새로운 분석을 실행한 후 저장해주세요.",
                    confirm_text="확인",
                    cancel_text=None,
                    icon="⚠️"
                )
                dialog.exec()
                return
            
            # service를 통해 저장 처리
            success, session_id, session_name, is_duplicate = powerlink_service.save_current_analysis_to_db()
            
            if not success:
                from src.toolbox.ui_kit.modern_dialog import ModernConfirmDialog
                dialog = ModernConfirmDialog(
                    self,
                    "저장 실패",
                    "저장할 분석 결과가 없습니다.\n\n키워드 분석을 먼저 실행해주세요.",
                    confirm_text="확인",
                    cancel_text=None,
                    icon="⚠️"
                )
                dialog.exec()
                return
            
            # 키워드 개수 가져오기
            keyword_count = len(powerlink_service.get_all_keywords())
            
            # 저장 다이얼로그 표시
            save_dialog = PowerLinkSaveDialog(
                session_id=session_id,
                session_name=session_name,
                keyword_count=keyword_count,
                is_duplicate=is_duplicate,
                parent=self
            )
            save_dialog.exec()
            
            # 저장이 성공했고 중복이 아닌 경우에만 히스토리 새로고침
            if not is_duplicate:
                self.refresh_history_list()
            
        except Exception as e:
            logger.error(f"PowerLink 분석 세션 저장 실패: {e}")
            log_manager.add_log(f"PowerLink 분석 세션 저장 실패: {e}", "error")
    
    def clear_all_analysis(self):
        """전체 분석 결과 클리어"""
        try:
            # 데이터가 있는지 확인
            if not powerlink_service.get_all_keywords():
                return
            
            # 모던 확인 다이얼로그 (키워드분석기와 동일한 방식)
            from src.toolbox.ui_kit.modern_dialog import ModernConfirmDialog
            try:
                confirmed = ModernConfirmDialog.warning(
                    self, 
                    "분석 결과 삭제", 
                    f"모든 분석 데이터를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                    "삭제", 
                    "취소"
                )
            except:
                # fallback: 생성자 사용하여 ⚠️ 이모티콘 표시
                dialog = ModernConfirmDialog(
                    self,
                    "분석 결과 삭제",
                    f"모든 분석 데이터를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                    confirm_text="삭제",
                    cancel_text="취소",
                    icon="⚠️"
                )
                confirmed = dialog.exec()
            
            if confirmed:
                # 히스토리 플래그 초기화
                self.is_loaded_from_history = False
                if hasattr(self, 'loaded_session_id'):
                    delattr(self, 'loaded_session_id')
                
                # 메모리 데이터베이스 클리어 (안전한 클리어)
                keywords_before = len(powerlink_service.get_all_keywords())
                powerlink_service.clear_all_keywords()
                keywords_after = len(powerlink_service.get_all_keywords())
                logger.info(f"메모리 DB 클리어: {keywords_before}개 → {keywords_after}개")
                
                # 테이블 클리어 (ModernTableWidget API 사용)
                mobile_rows_before = self.mobile_table.rowCount()
                pc_rows_before = self.pc_table.rowCount()
                
                self.mobile_table.clear_table()
                self.pc_table.clear_table()
                
                mobile_rows_after = self.mobile_table.rowCount()
                pc_rows_after = self.pc_table.rowCount()
                logger.info(f"테이블 클리어: 모바일 {mobile_rows_before}→{mobile_rows_after}, PC {pc_rows_before}→{pc_rows_after}")
                
                # 버튼 상태 업데이트
                self.update_save_button_state()
                
                log_manager.add_log("PowerLink 분석 결과 전체 클리어", "success")
                
        except Exception as e:
            logger.error(f"전체 클리어 실패: {e}")
            log_manager.add_log(f"PowerLink 전체 클리어 실패: {e}", "error")
    
    
    
    def update_keyword_data(self, keyword: str, result: KeywordAnalysisResult):
        """실시간으로 키워드 데이터 업데이트"""
        try:
            # 모바일 테이블에서 키워드 행 찾기
            mobile_row = self.find_keyword_row_in_table(self.mobile_table, keyword)
            if mobile_row >= 0:
                self.update_table_row_data(self.mobile_table, mobile_row, result, 'mobile')
                logger.debug(f"모바일 테이블 행 {mobile_row} 업데이트: {keyword}")
            
            # PC 테이블에서 키워드 행 찾기
            pc_row = self.find_keyword_row_in_table(self.pc_table, keyword)
            if pc_row >= 0:
                self.update_table_row_data(self.pc_table, pc_row, result, 'pc')
                logger.debug(f"PC 테이블 행 {pc_row} 업데이트: {keyword}")
            
            if mobile_row < 0 and pc_row < 0:
                logger.warning(f"키워드 '{keyword}' 테이블에서 찾을 수 없음")
                
            # 저장 버튼 상태 업데이트
            self.update_save_button_state()
                
        except Exception as e:
            logger.error(f"키워드 데이터 업데이트 실패: {keyword}: {e}")
    
    def find_keyword_row_in_table(self, table: QTableWidget, keyword: str) -> int:
        """테이블에서 특정 키워드의 행 번호 찾기"""
        for row in range(table.rowCount()):
            item = table.item(row, 1)  # 키워드는 1번 컬럼
            if item and item.text() == keyword:
                return row
        return -1
    
    def set_keywords_data(self, keywords_data):
        """키워드 데이터 설정 (교체 방식 - 히스토리 로드용)"""
        # 서비스를 통해 키워드 데이터 설정 (기존 데이터 교체)
        powerlink_service.set_keywords_data(keywords_data)
        
        # 테이블 새로고침
        self.refresh_tables_from_database()
        
        # 버튼 상태 업데이트
        self.update_save_button_state()
        self.update_delete_button_state()
    
    def add_keywords_data(self, keywords_data):
        """키워드 데이터 추가 (누적 방식 - 새로운 분석용)"""
        # 서비스를 통해 키워드 데이터 추가 (기존 데이터 유지)
        powerlink_service.add_keywords_data(keywords_data)
        
        # 히스토리 로드 플래그 해제 (새 데이터가 추가되었으므로)
        self.is_loaded_from_history = False
        if hasattr(self, 'loaded_session_id'):
            delattr(self, 'loaded_session_id')
        
        # 테이블 새로고침 (새 키워드 추가 시 전체 순위 재계산 필요)
        self.refresh_tables_from_database(force=True)
        
        # 버튼 상태 업데이트
        self.update_save_button_state()
        self.update_delete_button_state()
    
    def refresh_tables_from_database(self, force=False):
        """데이터베이스에서 테이블 전체 새로고침 (ModernTableWidget API 사용)"""
        try:
            # 이미 갱신 중이면 건너뛰기 (중복 실행 방지) - force 옵션으로 무시 가능
            if not force and hasattr(self, '_table_refreshing') and self._table_refreshing:
                logger.info("테이블 갱신이 이미 진행 중 - 건너뛰기")
                return
            
            # 갱신 플래그 설정
            self._table_refreshing = True
            
            # 🔧 정렬 기능 비활성화 (데이터 추가 중 정렬로 인한 row 인덱스 충돌 방지)
            mobile_sorting_was_enabled = self.mobile_table.isSortingEnabled()
            pc_sorting_was_enabled = self.pc_table.isSortingEnabled()
            
            self.mobile_table.setSortingEnabled(False)
            self.pc_table.setSortingEnabled(False)
            
            
            # 기존 테이블 데이터 클리어
            self.mobile_table.clear_table()
            self.pc_table.clear_table()
            
            # 서비스를 통해 모든 키워드 가져오기 (안전성 강화)
            service_keywords_dict = powerlink_service.get_all_keywords()
            all_keywords = list(service_keywords_dict.values()) if service_keywords_dict else []
            
            logger.info(f"refresh_tables_from_database: {len(all_keywords)}개 키워드 로드 (force={force})")
            if all_keywords:
                keyword_list = [k.keyword for k in all_keywords]
                logger.info(f"로드된 키워드 목록: {keyword_list[:5]}..." if len(keyword_list) > 5 else f"로드된 키워드 목록: {keyword_list}")
            
            # 테이블에 재추가 (update_mobile_table/update_pc_table과 동일한 방식)
            for result in all_keywords:
                # 모바일 테이블에 추가
                # 월검색량
                if result.mobile_search_volume >= 0:
                    mobile_search_volume = format_int(result.mobile_search_volume)
                else:
                    mobile_search_volume = "-"
                
                # 추천순위
                if result.mobile_recommendation_rank > 0:
                    mobile_rank_text = f"{result.mobile_recommendation_rank}위"
                else:
                    mobile_rank_text = "-"
                
                # 모바일 행 데이터 준비 (체크박스 제외)
                mobile_row_data = [
                    result.keyword,  # 키워드
                    mobile_search_volume,  # 월검색량
                    format_float(result.mobile_clicks, precision=1) if result.mobile_clicks >= 0 else "-",  # 클릭수
                    f"{format_float(result.mobile_ctr, precision=2)}%" if result.mobile_ctr >= 0 else "-",  # 클릭률
                    f"{format_int(result.mobile_first_page_positions)}위까지" if result.mobile_first_page_positions >= 0 else "-",  # 1p노출위치
                    format_price_krw(result.mobile_first_position_bid) if result.mobile_first_position_bid >= 0 else "-",  # 1등광고비
                    format_price_krw(result.mobile_min_exposure_bid) if result.mobile_min_exposure_bid >= 0 else "-",  # 최소노출가격
                    mobile_rank_text,  # 추천순위
                    "상세"  # 상세 버튼
                ]
                
                # ModernTableWidget API 사용하여 행 추가
                mobile_row = self.mobile_table.add_row_with_data(mobile_row_data, checkable=True)
                
                # 모바일 테이블 데이터 검증 및 강제 재설정 (간헐적 데이터 누락 문제 해결)
                from PySide6.QtCore import QCoreApplication
                QCoreApplication.processEvents()  # UI 업데이트 강제 처리
                
                # 각 셀의 데이터가 제대로 설정되었는지 확인
                missing_data_cols = []
                for col_idx, expected_data in enumerate(mobile_row_data):
                    if col_idx == 0:  # 체크박스 컬럼은 건너뛰기
                        continue
                    actual_item = self.mobile_table.item(mobile_row, col_idx)
                    if actual_item is None or actual_item.text().strip() == "":
                        missing_data_cols.append(col_idx)
                
                # 누락된 데이터가 있으면 강제로 다시 설정
                if missing_data_cols:
                    
                    for col_idx in missing_data_cols:
                        try:
                            from PySide6.QtWidgets import QTableWidgetItem
                            item = QTableWidgetItem(str(mobile_row_data[col_idx]))
                            self.mobile_table.setItem(mobile_row, col_idx, item)
                        except Exception as set_error:
                            pass
                
                # 모바일 상세 버튼 추가
                mobile_detail_button = QPushButton("상세")
                mobile_detail_font_size = tokens.get_font_size('normal')
                mobile_detail_button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #10b981;
                        color: white;
                        border: none;
                        border-radius: 0px;
                        font-weight: 600;
                        font-size: {mobile_detail_font_size}px;
                        margin: 0px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: #059669;
                    }}
                    QPushButton:pressed {{
                        background-color: #047857;
                    }}
                """)
                # 안전한 클로저 생성을 위해 람다로 래핑
                # 키워드 이름만 전달 - 클릭 시 서비스에서 데이터 조회
                mobile_detail_button.clicked.connect(lambda checked, keyword=result.keyword: self._show_detail_by_keyword(keyword, 'mobile'))
                
                # 상세 버튼 배치 시도 및 디버깅
                try:
                    
                    # 테이블 행 수 확인
                    total_rows = self.mobile_table.rowCount()
                    total_cols = self.mobile_table.columnCount()
                    
                    # 버튼 배치
                    self.mobile_table.setCellWidget(mobile_row, 9, mobile_detail_button)
                    
                    # Qt 이벤트 루프 처리 강제 실행
                    from PySide6.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
                    
                    # 버튼 표시 강제 (show() 호출)
                    mobile_detail_button.show()
                    mobile_detail_button.setVisible(True)
                    
                    # 배치 후 확인
                    placed_widget = self.mobile_table.cellWidget(mobile_row, 9)
                    if placed_widget is not None:
                        pass
                    else:
                        pass
                        
                except Exception as btn_error:
                    pass
                
                # PC 테이블에 추가
                # 월검색량
                if result.pc_search_volume >= 0:
                    pc_search_volume = format_int(result.pc_search_volume)
                else:
                    pc_search_volume = "-"
                
                # 추천순위
                if result.pc_recommendation_rank > 0:
                    pc_rank_text = f"{result.pc_recommendation_rank}위"
                else:
                    pc_rank_text = "-"
                
                # PC 행 데이터 준비 (체크박스 제외)
                pc_row_data = [
                    result.keyword,  # 키워드
                    pc_search_volume,  # 월검색량
                    format_float(result.pc_clicks, precision=1) if result.pc_clicks >= 0 else "-",  # 클릭수
                    f"{format_float(result.pc_ctr, precision=2)}%" if result.pc_ctr >= 0 else "-",  # 클릭률
                    f"{format_int(result.pc_first_page_positions)}위까지" if result.pc_first_page_positions >= 0 else "-",  # 1p노출위치
                    format_price_krw(result.pc_first_position_bid) if result.pc_first_position_bid >= 0 else "-",  # 1등광고비
                    format_price_krw(result.pc_min_exposure_bid) if result.pc_min_exposure_bid >= 0 else "-",  # 최소노출가격
                    pc_rank_text,  # 추천순위
                    "상세"  # 상세 버튼
                ]
                
                # ModernTableWidget API 사용하여 행 추가
                pc_row = self.pc_table.add_row_with_data(pc_row_data, checkable=True)
                
                # PC 상세 버튼 추가
                pc_detail_button = QPushButton("상세")
                pc_detail_font_size = tokens.get_font_size('normal')
                pc_detail_button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #10b981;
                        color: white;
                        border: none;
                        border-radius: 0px;
                        font-weight: 600;
                        font-size: {pc_detail_font_size}px;
                        margin: 0px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: #059669;
                    }}
                    QPushButton:pressed {{
                        background-color: #047857;
                    }}
                """)
                # 안전한 클로저 생성을 위해 람다로 래핑  
                # 키워드 이름만 전달 - 클릭 시 서비스에서 데이터 조회
                pc_detail_button.clicked.connect(lambda checked, keyword=result.keyword: self._show_detail_by_keyword(keyword, 'pc'))
                
                # 상세 버튼 배치 시도 및 디버깅
                try:
                    
                    # 테이블 행 수 확인
                    total_rows = self.pc_table.rowCount()
                    total_cols = self.pc_table.columnCount()
                    
                    # 버튼 배치
                    self.pc_table.setCellWidget(pc_row, 9, pc_detail_button)
                    
                    # Qt 이벤트 루프 처리 강제 실행
                    from PySide6.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
                    
                    # 버튼 표시 강제 (show() 호출)
                    pc_detail_button.show()
                    pc_detail_button.setVisible(True)
                    
                    # 배치 후 확인
                    placed_widget = self.pc_table.cellWidget(pc_row, 9)
                        
                except Exception as btn_error:
                    pass
            
            logger.info(f"테이블 새로고침 완료: {len(all_keywords)}개 키워드")
            logger.info(f"최종 테이블 행 수 - 모바일: {self.mobile_table.rowCount()}, PC: {self.pc_table.rowCount()}")
            
            # 모든 버튼 추가 완료 후 전체 테이블 업데이트 강제 실행
            from PySide6.QtCore import QCoreApplication, QTimer
            QCoreApplication.processEvents()
            
            # 약간의 지연 후 최종 버튼 확인 및 복구
            QTimer.singleShot(100, self._ensure_all_detail_buttons)
            
        except Exception as e:
            logger.error(f"테이블 새로고침 실패: {e}")
        finally:
            # 🔧 정렬 기능 복원
            try:
                if 'mobile_sorting_was_enabled' in locals():
                    self.mobile_table.setSortingEnabled(mobile_sorting_was_enabled)
                    self.pc_table.setSortingEnabled(pc_sorting_was_enabled)
                else:
                    # 예외가 발생해서 변수가 설정되지 않은 경우 기본값으로 복원
                    self.mobile_table.setSortingEnabled(True)
                    self.pc_table.setSortingEnabled(True)
            except Exception as sort_error:
                pass
            
            # 갱신 플래그 해제
            self._table_refreshing = False
    
    def _ensure_all_detail_buttons(self):
        """모든 행의 상세 버튼이 제대로 표시되는지 확인하고 복구"""
        try:
            
            # 서비스에서 모든 키워드 데이터 가져오기
            service_keywords_dict = powerlink_service.get_all_keywords()
            all_keywords = list(service_keywords_dict.values()) if service_keywords_dict else []
            
            # 모바일 테이블 버튼 확인 및 복구
            mobile_missing_count = 0
            for row in range(self.mobile_table.rowCount()):
                widget = self.mobile_table.cellWidget(row, 9)
                if widget is None:
                    # 버튼이 없으면 키워드 찾아서 다시 생성
                    keyword_item = self.mobile_table.item(row, 1)  # 키워드 컬럼
                    if keyword_item:
                        keyword = keyword_item.text().strip()
                        # 해당 키워드의 데이터 찾기
                        result = None
                        for kw_result in all_keywords:
                            if kw_result.keyword == keyword:
                                result = kw_result
                                break
                        
                        if result:
                            # 모바일 상세 버튼 재생성
                            mobile_detail_button = QPushButton("상세")
                            mobile_detail_font_size = tokens.get_font_size('normal')
                            mobile_detail_button.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: #10b981;
                                    color: white;
                                    border: none;
                                    border-radius: 0px;
                                    font-weight: 600;
                                    font-size: {mobile_detail_font_size}px;
                                    margin: 0px;
                                    padding: 0px;
                                }}
                                QPushButton:hover {{
                                    background-color: #059669;
                                }}
                                QPushButton:pressed {{
                                    background-color: #047857;
                                }}
                            """)
                            mobile_detail_button.clicked.connect(lambda checked, kw=keyword: self._show_detail_by_keyword(kw, 'mobile'))
                            
                            self.mobile_table.setCellWidget(row, 9, mobile_detail_button)
                            mobile_detail_button.show()
                            mobile_detail_button.setVisible(True)
                            mobile_missing_count += 1
            
            # PC 테이블 버튼 확인 및 복구
            pc_missing_count = 0
            for row in range(self.pc_table.rowCount()):
                widget = self.pc_table.cellWidget(row, 9)
                if widget is None:
                    # 버튼이 없으면 키워드 찾아서 다시 생성
                    keyword_item = self.pc_table.item(row, 1)  # 키워드 컬럼
                    if keyword_item:
                        keyword = keyword_item.text().strip()
                        # 해당 키워드의 데이터 찾기
                        result = None
                        for kw_result in all_keywords:
                            if kw_result.keyword == keyword:
                                result = kw_result
                                break
                        
                        if result:
                            # PC 상세 버튼 재생성
                            pc_detail_button = QPushButton("상세")
                            pc_detail_font_size = tokens.get_font_size('normal')
                            pc_detail_button.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: #10b981;
                                    color: white;
                                    border: none;
                                    border-radius: 0px;
                                    font-weight: 600;
                                    font-size: {pc_detail_font_size}px;
                                    margin: 0px;
                                    padding: 0px;
                                }}
                                QPushButton:hover {{
                                    background-color: #059669;
                                }}
                                QPushButton:pressed {{
                                    background-color: #047857;
                                }}
                            """)
                            pc_detail_button.clicked.connect(lambda checked, kw=keyword: self._show_detail_by_keyword(kw, 'pc'))
                            
                            self.pc_table.setCellWidget(row, 9, pc_detail_button)
                            pc_detail_button.show()
                            pc_detail_button.setVisible(True)
                            pc_missing_count += 1
            
            if mobile_missing_count > 0 or pc_missing_count > 0:
                pass
            else:
                pass
                
        except Exception as e:
            pass

    def clear_all_tables(self):
        """모든 테이블 클리어 (전체 클리어 시 사용)"""
        try:
            # ✅ ModernTableWidget API로 통일
            self.mobile_table.clear_table()
            self.pc_table.clear_table()
            powerlink_service.clear_all_keywords()
            self.update_save_button_state()
            logger.info("모든 테이블 클리어 완료")
        except Exception as e:
            logger.error(f"테이블 클리어 실패: {e}")
    
    
    def show_bid_details_improved(self, keyword: str, result, device_type: str):
        """순위별 입찰가 상세 다이얼로그 표시 (개선된 버전)"""
        try:
            # 디바이스별 입찰가 데이터 가져오기
            if device_type == 'mobile':
                bid_positions = result.mobile_bid_positions
                title = f"{keyword} - 모바일 순위별 입찰가"
            else:
                bid_positions = result.pc_bid_positions
                title = f"{keyword} - PC 순위별 입찰가"
            
            if not bid_positions:
                # 모던 다이얼로그로 에러 표시
                from src.toolbox.ui_kit.modern_dialog import ModernConfirmDialog
                error_dialog = ModernConfirmDialog(
                    self,
                    "정보 없음",
                    f"{device_type.upper()} 순위별 입찰가 정보가 없습니다.",
                    confirm_text="확인",
                    cancel_text=None,
                    icon="ℹ️"
                )
                error_dialog.exec()
                return
            
            # 상세 다이얼로그 생성
            dialog = QDialog(self)
            dialog.setWindowTitle(title)
            dialog.setModal(True)
            dialog.resize(420, 480)
            dialog.setStyleSheet(f"""
                QDialog {{
                    background-color: {ModernStyle.COLORS['bg_primary']};
                }}
            """)
            
            # 메인 레이아웃
            layout = QVBoxLayout()
            layout.setSpacing(16)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 심플한 헤더
            header_layout = QVBoxLayout()
            header_layout.setSpacing(4)
            
            # 키워드 이름 (심플하게)
            keyword_label = QLabel(keyword)
            keyword_font_size = tokens.get_font_size('header')
            keyword_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {keyword_font_size}px;
                    font-weight: 600;
                    color: {ModernStyle.COLORS['text_primary']};
                    margin: 0;
                }}
            """)
            
            # 디바이스 타입 (이모지 제거)
            device_label = QLabel(f"{device_type.upper()} 순위별 입찰가")
            device_label_font_size = tokens.get_font_size('normal')
            device_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {device_label_font_size}px;
                    font-weight: 400;
                    color: {ModernStyle.COLORS['text_secondary']};
                    margin: 0;
                }}
            """)
            
            header_layout.addWidget(keyword_label)
            header_layout.addWidget(device_label)
            layout.addLayout(header_layout)
            
            # 테이블 생성 (심플한 스타일)
            table = QTableWidget()
            table.setRowCount(len(bid_positions))
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["순위", "입찰가"])
            
            # 미니멀한 테이블 스타일 (아이템 색상 우선순위 허용)
            table_font_size = tokens.get_font_size('normal')
            header_font_size = tokens.get_font_size('normal')
            table.setStyleSheet(f"""
                QTableWidget {{
                    gridline-color: {ModernStyle.COLORS['border']};
                    background-color: {ModernStyle.COLORS['bg_card']};
                    border: 1px solid {ModernStyle.COLORS['border']};
                    border-radius: 6px;
                    font-size: {table_font_size}px;
                }}
                QTableWidget::item {{
                    padding: 12px 10px;
                    border-bottom: 1px solid {ModernStyle.COLORS['border']};
                    color: {ModernStyle.COLORS['text_primary']};
                }}
                QHeaderView::section {{
                    background-color: {ModernStyle.COLORS['bg_secondary']};
                    color: {ModernStyle.COLORS['text_primary']};
                    padding: 10px;
                    border: none;
                    border-bottom: 1px solid {ModernStyle.COLORS['border']};
                    font-weight: 500;
                    font-size: {header_font_size}px;
                }}
            """)
            
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setStretchLastSection(True)
            table.setAlternatingRowColors(False)
            table.setSelectionMode(QTableWidget.NoSelection)  # 선택 비활성화
            table.setEditTriggers(QTableWidget.NoEditTriggers)  # 편집 비활성화
            table.setFocusPolicy(Qt.NoFocus)  # 포커스 비활성화 (점선 테두리 제거)
            table.setShowGrid(False)
            
            # 컬럼 크기 설정
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.resizeSection(0, 80)  # 순위 컬럼 너비
            
            # 최소노출가격 확인
            if device_type == 'mobile':
                min_exposure_bid = result.mobile_min_exposure_bid
            else:
                min_exposure_bid = result.pc_min_exposure_bid
            
            
            # 최소노출가격과 일치하는 입찰가 중 가장 낮은 순위(가장 큰 position) 찾기
            min_exposure_position = None
            if min_exposure_bid >= 0:
                matching_positions = [bp.position for bp in bid_positions if bp.bid_price == min_exposure_bid]
                if matching_positions:
                    min_exposure_position = max(matching_positions)  # 가장 낮은 순위 (큰 숫자)
            
            # 데이터 추가 (최소노출가격 표시 개선)
            for row, bid_pos in enumerate(bid_positions):
                # 최소노출가격에 해당하는 특정 순위인지 확인
                is_min_exposure = (min_exposure_position is not None and bid_pos.position == min_exposure_position)
                
                # 순위 표시 (최소노출가격이면 이모지 추가)
                if is_min_exposure:
                    rank_text = f"🎯 {bid_pos.position}위"
                    rank_item = QTableWidgetItem(rank_text)
                    rank_item.setToolTip("💰 최소노출가격 - 이 금액으로 입찰하면 광고가 노출됩니다!")
                else:
                    rank_item = QTableWidgetItem(f"{bid_pos.position}위")
                rank_item.setTextAlignment(Qt.AlignCenter)
                
                # 가격 표시 (최소노출가격이면 강조 표시)
                if is_min_exposure:
                    price_text = f"⭐ {format_price_krw(bid_pos.bid_price)}"
                    price_item = QTableWidgetItem(price_text)
                    price_item.setToolTip("💰 최소노출가격 - 이 금액으로 입찰하면 광고가 노출됩니다!")
                else:
                    price_item = QTableWidgetItem(format_price_krw(bid_pos.bid_price))
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                
                table.setItem(row, 0, rank_item)
                table.setItem(row, 1, price_item)
            
            layout.addWidget(table)
            
            # 최소노출가격 정보 표시
            if min_exposure_position is not None:
                info_layout = QHBoxLayout()
                info_layout.setContentsMargins(0, 8, 0, 0)
                
                info_label = QLabel(f"💡 최소노출가격: {format_price_krw(min_exposure_bid)} ({min_exposure_position}위)")
                info_font_size = tokens.get_font_size('normal')
                info_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: #f0f9ff;
                        color: #0369a1;
                        padding: 8px 12px;
                        border-radius: 6px;
                        border: 1px solid #bae6fd;
                        font-size: {info_font_size}px;
                        font-weight: 500;
                    }}
                """)
                info_layout.addWidget(info_label)
                layout.addLayout(info_layout)
            
            # 확인 버튼 (미니멀하게)
            from src.toolbox.ui_kit.components import ModernButton
            confirm_button = ModernButton("확인", "primary")
            confirm_button.clicked.connect(dialog.accept)
            confirm_button.setMinimumHeight(36)
            
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(0, 12, 0, 0)
            button_layout.addStretch()
            button_layout.addWidget(confirm_button)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            print(f"상세 다이얼로그 표시 오류: {e}")
            # 에러 다이얼로그 표시
            from src.toolbox.ui_kit.modern_dialog import ModernInfoDialog
            ModernInfoDialog.error(self, "오류", f"상세 정보를 표시할 수 없습니다: {e}")
    
    def update_all_tables(self):
        """모든 테이블 업데이트 (모바일 + PC)"""
        try:
            logger.info("모든 테이블 업데이트 시작")
            
            # 데이터 존재 확인
            service_keywords = powerlink_service.get_all_keywords()
            logger.info(f"서비스에서 {len(service_keywords)}개 키워드 확인")
            
            if not service_keywords:
                logger.warning("서비스에 키워드 데이터가 없음 - 빈 테이블로 설정")
                self.mobile_table.clear_table()
                self.pc_table.clear_table()
                return
            
            # 각 테이블 개별 업데이트
            self.update_mobile_table()
            self.update_pc_table()
            
            # 업데이트 결과 로깅
            mobile_rows = self.mobile_table.rowCount()
            pc_rows = self.pc_table.rowCount()
            logger.info(f"테이블 업데이트 완료: 모바일 {mobile_rows}행, PC {pc_rows}행")
            
        except Exception as e:
            logger.error(f"테이블 업데이트 실패: {e}")
            # 실패 시 refresh_tables_from_database로 대체 시도
            try:
                logger.info("대체 방법으로 테이블 새로고침 시도")
                self.refresh_tables_from_database()
            except Exception as fallback_error:
                logger.error(f"대체 테이블 새로고침도 실패: {fallback_error}")
    
    def _recalculate_rankings_for_table(self, table, device_type: str):
        """테이블에 남은 키워드들로만 순위 재계산 후 순위 컬럼 업데이트"""
        was_sorting = True  # 기본값 설정
        try:
            logger.info(f"_recalculate_rankings_for_table 호출됨: {device_type}, 행 수: {table.rowCount()}")
            if table.rowCount() == 0:
                logger.info(f"{device_type} 테이블이 비어있음, 순위 재계산 생략")
                return
            
            # 정렬 상태 저장 후 비활성화 (순위 업데이트 중 행 이동 방지)
            was_sorting = table.isSortingEnabled()
            table.setSortingEnabled(False)
            logger.info(f"{device_type} 테이블 정렬 비활성화 (원래 상태: {was_sorting})")
            
            # 컬럼 인덱스 찾기
            keyword_col = self._get_column_index(table, "키워드", 1)
            rank_col = self._get_column_index(table, "추천순위", 8)
            
            
            # 테이블에서 키워드와 데이터를 추출 (점수와 함께)
            table_keywords = []
            
            for row in range(table.rowCount()):
                
                keyword_item = table.item(row, keyword_col)
                
                if keyword_item and keyword_item.text():
                    keyword = keyword_item.text().strip()
                    
                    # 서비스에서 해당 키워드의 전체 데이터 가져오기
                    keyword_data = keyword_database.get_keyword(keyword)
                    
                    if keyword_data:
                        # 점수 계산
                        if device_type == 'mobile':
                            from .engine_local import hybrid_score_mobile
                            score = hybrid_score_mobile(keyword_data)
                        else:
                            from .engine_local import hybrid_score_pc
                            score = hybrid_score_pc(keyword_data)
                        
                        table_keywords.append((keyword, keyword_data, score))
                    else:
                        pass
                    
                        
            
            if not table_keywords:
                return
            
            # 점수 기준으로 내림차순 정렬 (높은 점수가 1위)
            table_keywords.sort(key=lambda x: x[2], reverse=True)
            
            # 테이블에서 키워드를 찾아 순위 업데이트
            for rank, (keyword, data, score) in enumerate(table_keywords, 1):
                
                # 테이블에서 해당 키워드의 행을 찾기
                found = False
                for row in range(table.rowCount()):
                    keyword_item = table.item(row, keyword_col)
                    if keyword_item and keyword_item.text().strip() == keyword:
                        # 순위 컬럼 업데이트
                        rank_item = table.item(row, rank_col)
                        if rank_item:
                            rank_item.setText(f"{rank}위")
                        else:
                            # 아이템이 없으면 새로 생성
                            from PySide6.QtWidgets import QTableWidgetItem
                            rank_item = QTableWidgetItem(f"{rank}위")
                            table.setItem(row, rank_col, rank_item)
                        found = True
                        break
                        
                if not found:
                    pass
            
            logger.info(f"{device_type} 테이블 순위 재계산 완료: {len(table_keywords)}개 키워드")
            
        except Exception as e:
            logger.error(f"테이블 순위 재계산 실패 ({device_type}): {e}")
        finally:
            # 정렬 상태 복원
            table.setSortingEnabled(was_sorting)
            logger.info(f"{device_type} 테이블 정렬 상태 복원: {was_sorting}")
    
    def _get_column_index(self, table, header_text: str, default: int = -1) -> int:
        """헤더 텍스트로 컬럼 인덱스 찾기 (model.headerData 기반으로 안전한 검색)"""
        from PySide6.QtCore import Qt
        
        model = table.model()
        if model is None:
            logger.warning(f"테이블 모델이 없음, 기본값 {default} 반환")
            return default
            
        for c in range(table.columnCount()):
            header_value = model.headerData(c, Qt.Horizontal, Qt.DisplayRole)
            if header_value is not None and str(header_value).strip() == header_text:
                logger.debug(f"헤더 '{header_text}' 찾음: 컬럼 {c}")
                return c
                
        # 대체 방법: horizontalHeaderItem으로도 시도
        for c in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(c)
            if header_item and header_item.text().strip() == header_text:
                logger.debug(f"헤더 '{header_text}' 찾음 (대체방법): 컬럼 {c}")
                return c
                
        logger.warning(f"헤더 '{header_text}'를 찾을 수 없음, 기본값 {default} 반환")
        return default
    
    def delete_selected_keywords(self, device_type: str):
        """선택된 키워드만 삭제 (실제 선택삭제)"""
        try:
            
            # 디바이스 타입에 따라 해당 테이블 선택
            if device_type == 'mobile':
                table = self.mobile_table
                other_table = self.pc_table
            else:  # device_type == 'pc'
                table = self.pc_table
                other_table = self.mobile_table
                
                
            # 선택된 행 확인
            
            checked_rows = table.get_checked_rows()
            
            if not checked_rows:
                return
                
            
            # 컬럼 인덱스 찾기
            
            keyword_col = self._get_column_index(table, "키워드", 1)
            
            # 삭제할 키워드들 수집 (모바일/PC는 한몸이므로)
            
            keywords_to_delete = []
            for row_index in checked_rows:
                keyword_item = table.item(row_index, keyword_col)
                
                if keyword_item and keyword_item.text():
                    keyword = keyword_item.text().strip()
                    keywords_to_delete.append(keyword)
                    
            
            if not keywords_to_delete:
                return
            
            
            # 역순으로 행 삭제 (인덱스 변화 방지)
            checked_rows.sort(reverse=True)
            for row_index in checked_rows:
                table.removeRow(row_index)
            
            
            # 동일한 키워드들을 상대방 테이블에서도 삭제 (모바일/PC는 한몸)
            other_keyword_col = self._get_column_index(other_table, "키워드", 1)
            
            for keyword in keywords_to_delete:
                
                for row in range(other_table.rowCount() - 1, -1, -1):  # 역순으로 탐색
                    keyword_item = other_table.item(row, other_keyword_col)
                    if keyword_item and keyword_item.text().strip() == keyword:
                        other_table.removeRow(row)
                        other_device_type = 'pc' if device_type == 'mobile' else 'mobile'
                        break
            
            
            # 서비스 데이터에서도 키워드들 삭제
            for keyword in keywords_to_delete:
                try:
                    keyword_database.remove_keyword(keyword)
                except Exception as e:
                    pass
            
            
            # 두 테이블 모두의 순위 재계산
            self._recalculate_rankings_for_table(self.mobile_table, 'mobile')
            
            self._recalculate_rankings_for_table(self.pc_table, 'pc')
            
            
            # 버튼 상태 업데이트
            self.update_delete_button_state()
            self.update_save_button_state()
            
            # 🔧 히스토리 로드 플래그 해제 (키워드 삭제로 인한 데이터 변경이 발생했으므로)
            logger.error("🔧 키워드 삭제로 인한 히스토리 플래그 해제")
            print("🔧 키워드 삭제로 인한 히스토리 플래그 해제")
            self.is_loaded_from_history = False
            if hasattr(self, 'loaded_session_id'):
                delattr(self, 'loaded_session_id')
                logger.error("🔧 loaded_session_id 속성 제거 완료")
                print("🔧 loaded_session_id 속성 제거 완료")
            
            logger.error(f"🎉 === {len(keywords_to_delete)}개 키워드 삭제 및 순위 재계산 완료 ===")
            print(f"🎉 === {len(keywords_to_delete)}개 키워드 삭제 및 순위 재계산 완료 ===")
            
        except Exception as e:
            logger.error(f"❌ 선택된 키워드 삭제 실패 ({device_type}): {e}")
            print(f"❌ 선택된 키워드 삭제 실패 ({device_type}): {e}")
            import traceback
            logger.error(f"❌ 삭제 상세 오류: {traceback.format_exc()}")
            print(f"❌ 삭제 상세 오류: {traceback.format_exc()}")
    
    
    def update_history_button_state(self):
        """히스토리 테이블 선택 상태에 따른 버튼 활성화/비활성화 및 개수 표시"""
        try:
            if not hasattr(self, 'history_table'):
                return
                
            checked_rows = self.history_table.get_checked_rows()
            count = len(checked_rows)
            has_selection = count > 0
            has_single_selection = count == 1
            
            # 선택삭제 버튼: 1개 이상 선택 시 활성화 + 개수 표시
            if hasattr(self, 'delete_history_button'):
                if has_selection:
                    self.delete_history_button.setText(f"🗑️ 선택 삭제 ({count})")
                    self.delete_history_button.setEnabled(True)
                else:
                    self.delete_history_button.setText("🗑️ 선택 삭제")
                    self.delete_history_button.setEnabled(False)
                
            # 보기 버튼: 정확히 1개 선택 시만 활성화
            if hasattr(self, 'view_history_button'):
                if has_single_selection:
                    self.view_history_button.setText("👀 보기 (1)")
                    self.view_history_button.setEnabled(True)
                else:
                    self.view_history_button.setText("👀 보기")
                    self.view_history_button.setEnabled(False)
                
            # 선택 저장 버튼: 1개 이상 선택 시 활성화 + 개수 표시
            if hasattr(self, 'export_selected_history_button'):
                if has_selection:
                    self.export_selected_history_button.setText(f"💾 선택 저장 ({count})")
                    self.export_selected_history_button.setEnabled(True)
                else:
                    self.export_selected_history_button.setText("💾 선택 저장")
                    self.export_selected_history_button.setEnabled(False)
                
            logger.debug(f"히스토리 버튼 상태 업데이트: 선택된 행 {count}개")
            
        except Exception as e:
            logger.error(f"히스토리 버튼 상태 업데이트 실패: {e}")
    
    def update_delete_button_state(self):
        """모바일/PC 테이블 선택 상태에 따른 선택삭제 버튼 활성화/비활성화 및 개수 표시"""
        try:
            # 모바일 테이블 선택 상태 확인
            mobile_count = 0
            if hasattr(self, 'mobile_table'):
                mobile_checked_rows = self.mobile_table.get_checked_rows()
                mobile_count = len(mobile_checked_rows)
                
            # PC 테이블 선택 상태 확인  
            pc_count = 0
            if hasattr(self, 'pc_table'):
                pc_checked_rows = self.pc_table.get_checked_rows()
                pc_count = len(pc_checked_rows)
                
            # 모바일 선택삭제 버튼 업데이트
            if hasattr(self, 'mobile_delete_button'):
                if mobile_count > 0:
                    self.mobile_delete_button.setText(f"🗑️ 선택 삭제 ({mobile_count})")
                    self.mobile_delete_button.setEnabled(True)
                else:
                    self.mobile_delete_button.setText("🗑️ 선택 삭제")
                    self.mobile_delete_button.setEnabled(False)
                    
            # PC 선택삭제 버튼 업데이트
            if hasattr(self, 'pc_delete_button'):
                if pc_count > 0:
                    self.pc_delete_button.setText(f"🗑️ 선택 삭제 ({pc_count})")
                    self.pc_delete_button.setEnabled(True)
                else:
                    self.pc_delete_button.setText("🗑️ 선택 삭제")
                    self.pc_delete_button.setEnabled(False)
                
            logger.debug(f"선택삭제 버튼 상태 업데이트: 모바일 {mobile_count}개, PC {pc_count}개")
            
        except Exception as e:
            logger.error(f"선택삭제 버튼 상태 업데이트 실패: {e}")
    
