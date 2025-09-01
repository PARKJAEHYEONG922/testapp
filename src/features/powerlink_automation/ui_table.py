"""
파워링크 자동화 키워드 테이블 UI
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
                              QTableWidgetItem, QHeaderView, QAbstractItemView,
                              QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from src.toolbox.ui_kit.modern_table import ModernTableWidget
from src.toolbox.ui_kit.components import ModernButton
from src.toolbox.ui_kit.modern_style import ModernStyle
from src.foundation.logging import get_logger
from .service import PowerlinkAutomationService
from .models import Campaign, AdGroup, KeywordInfo, BidLog
from .worker import KeywordStatusWorker
from .adapters import PowerlinkRankAdapter
from typing import List, Dict

logger = get_logger("powerlink_automation.ui_table")


class KeywordTableWidget(ModernTableWidget):
    """키워드 테이블 위젯"""
    
    def __init__(self, service: PowerlinkAutomationService):
        columns = [
            "선택", "상태", "캠페인 유형", "캠페인", "광고그룹", 
            "키워드", "매체", "1p노출수", "목표순위", "현재순위", 
            "상한가", "현재가격", "로그"
        ]
        super().__init__(columns, has_checkboxes=True, has_header_checkbox=True)
        
        self.service = service
        self.rank_adapter = PowerlinkRankAdapter()
        self.campaigns: List[Campaign] = []
        self.adgroups_data: Dict[str, List[AdGroup]] = {}
        self.keywords_data: Dict[str, List[KeywordInfo]] = {}
        self.worker_threads: Dict[str, KeywordStatusWorker] = {}
        self.keyword_logs: Dict[str, List[BidLog]] = {}
        self.ad_ids_per_row: Dict[int, List[str]] = {}
        
        self.setup_table()
        
    def setup_table(self):
        """테이블 추가 설정"""
        # 컬럼 너비 설정
        column_widths = [50, 50, 100, 100, 100, 100, 50, 60, 60, 60, 60, 60, 80]
        for i, width in enumerate(column_widths):
            self.setColumnWidth(i, width)
            
        # 편집 가능한 컬럼 설정 (목표순위, 상한가)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)
        
        # 헤더 더블클릭 이벤트
        self.horizontalHeader().sectionDoubleClicked.connect(self.set_bid_limit_all)
        
    def set_campaigns(self, campaigns: List[Campaign]):
        """캠페인 목록 설정"""
        self.campaigns = campaigns
        
    def load_adgroups(self, campaign_id: str):
        """광고그룹 로드"""
        if campaign_id == "":  # 전체 캠페인
            return
            
        if campaign_id not in self.adgroups_data:
            adgroups = self.service.fetch_adgroups(campaign_id)
            self.adgroups_data[campaign_id] = adgroups
            
    def load_keywords(self, campaign_id: str, adgroup_id: str = None):
        """키워드 로드"""
        self.clearContents()
        self.setRowCount(0)
        self.ad_ids_per_row.clear()
        
        row_count = 0
        
        if campaign_id == "":  # 전체 캠페인
            for campaign in self.campaigns:
                adgroups = self.adgroups_data.get(campaign.ncc_campaign_id, [])
                for adgroup in adgroups:
                    keywords = self._load_keywords_for_adgroup(adgroup.ncc_adgroup_id)
                    for keyword in keywords:
                        self._add_keyword_row(row_count, campaign, adgroup, keyword)
                        row_count += 1
        else:
            adgroups = self.adgroups_data.get(campaign_id, [])
            campaign = next((c for c in self.campaigns if c.ncc_campaign_id == campaign_id), None)
            
            if adgroup_id:  # 특정 광고그룹
                adgroup = next((ag for ag in adgroups if ag.ncc_adgroup_id == adgroup_id), None)
                if adgroup:
                    keywords = self._load_keywords_for_adgroup(adgroup_id)
                    for keyword in keywords:
                        self._add_keyword_row(row_count, campaign, adgroup, keyword)
                        row_count += 1
            else:  # 캠페인의 모든 광고그룹
                for adgroup in adgroups:
                    keywords = self._load_keywords_for_adgroup(adgroup.ncc_adgroup_id)
                    for keyword in keywords:
                        self._add_keyword_row(row_count, campaign, adgroup, keyword)
                        row_count += 1
                        
    def _load_keywords_for_adgroup(self, adgroup_id: str) -> List[KeywordInfo]:
        """광고그룹의 키워드 로드"""
        if adgroup_id not in self.keywords_data:
            keywords = self.service.fetch_keywords(adgroup_id)
            # 파워링크 개수 조회
            for keyword in keywords:
                from .models import DisplayType
                display_type = DisplayType.PC  # 기본값, 실제로는 광고그룹에서 가져와야 함
                power_link_count = self.rank_adapter.get_powerlink_count(keyword.keyword, display_type)
                keyword.power_link_count = power_link_count
                # 목표순위 자동 설정
                keyword.target_rank = 6 if power_link_count >= 6 else max(1, power_link_count)
                
            self.keywords_data[adgroup_id] = keywords
            
        return self.keywords_data[adgroup_id]
        
    def _add_keyword_row(self, row: int, campaign: Campaign, adgroup: AdGroup, keyword: KeywordInfo):
        """키워드 행 추가"""
        # ModernTableWidget.add_row() 사용
        row_data = [
            not keyword.user_lock,         # 0. 선택 (체크박스)
            "ON" if not keyword.user_lock else "OFF",  # 1. 상태
            campaign.campaign_type.value,  # 2. 캠페인 유형
            campaign.name,                 # 3. 캠페인
            adgroup.name,                  # 4. 광고그룹  
            keyword.keyword,               # 5. 키워드
            adgroup.display_type.value,    # 6. 매체
            str(keyword.power_link_count), # 7. 1p노출수
            str(keyword.target_rank),      # 8. 목표순위
            "",                            # 9. 현재순위
            str(keyword.max_bid),          # 10. 상한가
            str(keyword.bid_amount),       # 11. 현재가격
            "로그"                         # 12. 로그 버튼
        ]
        
        # ModernTableWidget의 add_row 사용
        actual_row = self.add_row(row_data)
        
        # 상태 토글 버튼 (1번 컬럼)
        status_text = "ON" if not keyword.user_lock else "OFF"
        toggle_button = ModernButton(status_text)
        toggle_button.setStyleSheet(
            f"background-color: {ModernStyle.COLORS['success']}; color: white;" 
            if not keyword.user_lock else 
            f"background-color: {ModernStyle.COLORS['danger']}; color: white;"
        )
        toggle_button.clicked.connect(
            lambda checked, k_id=keyword.ncc_keyword_id: self.toggle_keyword_status(k_id, toggle_button)
        )
        toggle_button.setProperty("row", actual_row)
        self.setCellWidget(actual_row, 1, toggle_button)
        
        # 로그 버튼 (12번 컬럼)
        log_button = ModernButton("로그")
        log_button.clicked.connect(
            lambda: self.show_keyword_log(keyword.ncc_keyword_id)
        )
        self.setCellWidget(actual_row, 12, log_button)
        
        # 편집 가능한 컬럼 설정 (목표순위, 상한가)
        editable_columns = [8, 10]
        for col in editable_columns:
            item = self.item(actual_row, col)
            if item:
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        
        # 사용자 데이터 저장
        if self.item(actual_row, 4):  # 광고그룹
            self.item(actual_row, 4).setData(Qt.UserRole, adgroup.ncc_adgroup_id)
        if self.item(actual_row, 5):  # 키워드
            self.item(actual_row, 5).setData(Qt.UserRole, keyword.ncc_keyword_id)
            
        # 광고 ID 저장
        self.ad_ids_per_row[actual_row] = keyword.ad_ids
        
    def toggle_keyword_status(self, keyword_id: str, toggle_button):
        """키워드 상태 토글"""
        current_status = toggle_button.text() == "OFF"
        
        worker = KeywordStatusWorker(self.service, keyword_id, current_status)
        worker.finished.connect(
            lambda success, k_id: self.update_keyword_status(success, k_id, toggle_button)
        )
        self.worker_threads[keyword_id] = worker
        worker.start()
        
    def update_keyword_status(self, success: bool, keyword_id: str, toggle_button):
        """키워드 상태 업데이트"""
        if success:
            new_status = "ON" if toggle_button.text() == "OFF" else "OFF"
            toggle_button.setText(new_status)
            is_on = new_status == "ON"
            
            # 토글 버튼 스타일 업데이트
            toggle_button.setStyleSheet(
                f"background-color: {ModernStyle.COLORS['success']}; color: white;" 
                if is_on else 
                f"background-color: {ModernStyle.COLORS['danger']}; color: white;"
            )
            
            # 체크박스 동기화
            row = toggle_button.property("row")
            if row is not None:
                checkbox_widget = self.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.layout().itemAt(0).widget()
                    checkbox.setChecked(is_on)
                    
            QMessageBox.information(self, "완료", "상태가 업데이트되었습니다.")
            
            # 키워드 데이터 업데이트
            self._update_keyword_data(keyword_id, not is_on)  # user_lock은 반대
            
        else:
            QMessageBox.critical(self, "실패", "상태 업데이트에 실패했습니다.")
            
        # 워커 정리
        if keyword_id in self.worker_threads:
            del self.worker_threads[keyword_id]
            
    def _update_keyword_data(self, keyword_id: str, user_lock: bool):
        """키워드 데이터 업데이트"""
        for keywords in self.keywords_data.values():
            for keyword in keywords:
                if keyword.ncc_keyword_id == keyword_id:
                    keyword.user_lock = user_lock
                    break
                    
    def get_selected_keywords(self) -> List[tuple]:
        """선택된 키워드 정보 반환"""
        selected = []
        selected_rows = self.get_checked_rows()  # ModernTableWidget 메서드 사용
        
        for row in selected_rows:
            # 필요한 데이터 수집
            ad_ids = self.ad_ids_per_row.get(row, [])
            adgroup_id = self.item(row, 4).data(Qt.UserRole) if self.item(row, 4) else ""
            keyword_id = self.item(row, 5).data(Qt.UserRole) if self.item(row, 5) else ""
            keyword = self.item(row, 5).text() if self.item(row, 5) else ""
            display_type = self.item(row, 6).text() if self.item(row, 6) else ""
            target_rank = int(self.item(row, 8).text()) if self.item(row, 8) and self.item(row, 8).text().isdigit() else 1
            max_bid = int(self.item(row, 10).text()) if self.item(row, 10) and self.item(row, 10).text().isdigit() else 1000
            current_bid = int(self.item(row, 11).text()) if self.item(row, 11) and self.item(row, 11).text().isdigit() else 70
            campaign_type = self.item(row, 2).text() if self.item(row, 2) else ""
            
            selected.append((
                row, ad_ids, adgroup_id, keyword_id, keyword,
                display_type, target_rank, current_bid, max_bid, campaign_type
            ))
                    
        return selected
        
    def update_rank(self, row: int, rank_text: str):
        """순위 업데이트"""
        item = QTableWidgetItem(rank_text)
        self.setItem(row, 9, item)
        
    def update_bid(self, row: int, new_bid: int, max_bid_reached: bool):
        """입찰가 업데이트"""
        item = QTableWidgetItem(str(new_bid))
        self.setItem(row, 11, item)
        
        # 로그 추가
        keyword_id = self.item(row, 5).data(Qt.UserRole)
        if keyword_id:
            self._add_bid_log(keyword_id, row, new_bid, max_bid_reached)
            
    def log_target_reached(self, row: int, bid: int, rank: str, timestamp: str, max_bid_reached: bool):
        """목표 달성 로그"""
        keyword_id = self.item(row, 5).data(Qt.UserRole)
        if keyword_id:
            self._add_target_log(keyword_id, row, bid, rank, timestamp, max_bid_reached)
            
    def _add_bid_log(self, keyword_id: str, row: int, new_bid: int, max_bid_reached: bool):
        """입찰 로그 추가"""
        if keyword_id not in self.keyword_logs:
            self.keyword_logs[keyword_id] = []
            
        current_bid_item = self.item(row, 11)
        current_bid = int(current_bid_item.text()) if current_bid_item else 0
        target_rank = self.item(row, 8).text()
        current_rank = self.item(row, 9).text()
        
        from datetime import datetime
        log = BidLog(
            keyword_id=keyword_id,
            timestamp=datetime.now().strftime('%m-%d %H:%M'),
            target_rank=int(target_rank),
            current_rank=current_rank,
            current_bid=current_bid,
            new_bid=new_bid,
            max_bid_reached=max_bid_reached
        )
        
        self.keyword_logs[keyword_id].append(log)
        
    def _add_target_log(self, keyword_id: str, row: int, bid: int, rank: str, timestamp: str, max_bid_reached: bool):
        """목표 달성 로그 추가"""
        if keyword_id not in self.keyword_logs:
            self.keyword_logs[keyword_id] = []
            
        target_rank = self.item(row, 8).text()
        
        log = BidLog(
            keyword_id=keyword_id,
            timestamp=timestamp,
            target_rank=int(target_rank),
            current_rank=rank,
            current_bid=bid,
            new_bid=bid,
            target_reached=not max_bid_reached,
            max_bid_reached=max_bid_reached
        )
        
        self.keyword_logs[keyword_id].append(log)
        
    def show_keyword_log(self, keyword_id: str):
        """키워드 로그 표시"""
        logs = self.keyword_logs.get(keyword_id, [])
        if not logs:
            QMessageBox.information(self, "로그 없음", "해당 키워드에 대한 로그가 없습니다.")
            return
            
        # 키워드명 찾기
        keyword_name = "키워드 로그"
        for row in range(self.rowCount()):
            item = self.item(row, 5)
            if item and item.data(Qt.UserRole) == keyword_id:
                keyword_name = item.text()
                break
                
        # 로그 텍스트 구성
        log_lines = []
        for log in logs:
            if log.target_reached:
                log_lines.append(f"{log.timestamp} - 목표순위 달성! 현재순위: {log.current_rank}")
            elif log.max_bid_reached:
                log_lines.append(f"{log.timestamp} - 상한가 도달! 입찰가: {log.new_bid}원")
            else:
                log_lines.append(
                    f"{log.timestamp} - 목표: {log.target_rank}위, 현재: {log.current_rank}위, "
                    f"입찰가: {log.current_bid}원 → {log.new_bid}원"
                )
                
        log_text = "\n".join(log_lines)
        QMessageBox.information(self, keyword_name, log_text)
        
    def set_bid_limit_all(self, column: int):
        """일괄 설정"""
        if column == 8:  # 목표순위
            title = "목표순위 일괄 설정"
            prompt = "목표순위를 입력하세요:"
        elif column == 10:  # 상한가
            title = "상한가 일괄 설정"
            prompt = "상한가를 입력하세요:"
        else:
            return
            
        value, ok = QInputDialog.getText(self, title, prompt)
        if ok and value.isdigit():
            for row in range(self.rowCount()):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                self.setItem(row, column, item)
                
    def apply_filter(self, filter_text: str):
        """키워드 필터 적용"""
        filter_text = filter_text.lower()
        
        for row in range(self.rowCount()):
            keyword_item = self.item(row, 5)
            if keyword_item:
                should_show = filter_text in keyword_item.text().lower()
                self.setRowHidden(row, not should_show)
            else:
                self.setRowHidden(row, True)