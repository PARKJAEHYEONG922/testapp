"""
파워링크 자동화 워커
"""
import time
from datetime import datetime
from PySide6.QtCore import QThread, Signal
from typing import List, Dict, Set, Optional
from src.foundation.logging import get_logger
from .models import KeywordInfo, AutomationSettings, BidLog, DisplayType
from .service import PowerlinkAutomationService
from .adapters import PowerlinkRankAdapter

logger = get_logger("powerlink_automation.worker")


class AutoBiddingWorker(QThread):
    """자동 입찰 워커 스레드"""
    
    # 시그널 정의
    rank_updated = Signal(int, str)  # row, rank_text
    bid_updated = Signal(int, int, bool)  # row, new_bid, max_bid_reached
    remaining_seconds = Signal(int)  # remaining_seconds
    target_reached = Signal(int, int, str, str, bool)  # row, bid, rank, timestamp, max_bid_reached
    status_message = Signal(str)  # status message
    
    def __init__(self, keywords_info: List[tuple], settings: AutomationSettings, 
                 service: PowerlinkAutomationService):
        super().__init__()
        self.keywords_info = keywords_info
        self.settings = settings
        self.service = service
        self.rank_adapter = PowerlinkRankAdapter()
        self._stop_flag = False
        
        # 상태 추적
        self.finished_keywords: Set[str] = set()
        self.keyword_state: Dict[str, str] = {}
        self.prev_states: Dict[str, str] = {}
        self.toggle_counts: Dict[str, int] = {}
        
        # 초기화
        for info in keywords_info:
            keyword_id = info[3]  # keyword_id는 4번째 요소
            self.keyword_state[keyword_id] = 'initial'
            self.prev_states[keyword_id] = None
            self.toggle_counts[keyword_id] = 0
    
    def run(self):
        """워커 실행"""
        try:
            self.status_message.emit("자동입찰 진행 중...")
            self.rank_adapter.setup_driver()
            
            while not self._stop_flag and len(self.finished_keywords) < len(self.keywords_info):
                # 첫 번째 라운드: 키워드 처리
                self._process_keywords()
                if self._stop_flag:
                    break
                    
                # 대기 시간
                self._wait_with_signal(self.settings.wait_time_minutes * 60)
                if self._stop_flag:
                    break
                    
                # 두 번째 라운드: 재확인
                self._recheck_keywords()
                if self._stop_flag:
                    break
                    
                # 대기 시간
                self._wait_with_signal(self.settings.wait_time_minutes * 60)
                
            self.status_message.emit("자동입찰이 완료되었습니다.")
            
        except Exception as e:
            logger.error(f"자동입찰 실행 오류: {e}")
            self.status_message.emit(f"오류 발생: {str(e)}")
        finally:
            self.rank_adapter.close_driver()
    
    def _process_keywords(self):
        """키워드 처리"""
        for index, info in enumerate(self.keywords_info):
            if self._stop_flag:
                break
                
            row, ad_ids, adgroup_id, keyword_id, keyword, display_type, target_rank, current_bid, max_bid, campaign_type = info
            
            if keyword_id in self.finished_keywords:
                continue
                
            # 현재 순위 조회
            keyword_info = KeywordInfo(
                ncc_keyword_id=keyword_id,
                ncc_adgroup_id=adgroup_id,
                ncc_campaign_id="",  # 필요시 추가
                keyword=keyword,
                bid_amount=current_bid,
                user_lock=False,
                ad_ids=ad_ids
            )
            
            display_enum = DisplayType.PC if display_type == "PC" else DisplayType.MOBILE
            rank = self.rank_adapter.get_current_rank(keyword_info, display_enum)
            rank_text = str(rank) if rank is not None else "순위밖"
            self.rank_updated.emit(row, rank_text)
            
            # 목표 순위 달성 확인
            if rank == target_rank:
                self.finished_keywords.add(keyword_id)
                self.target_reached.emit(
                    row, current_bid, rank_text,
                    datetime.now().strftime('%m-%d %H:%M'), False
                )
                continue
            
            # 입찰가 조정 로직
            new_bid = self._calculate_new_bid(rank, target_rank, current_bid, max_bid)
            
            if new_bid != current_bid:
                success = self.service.update_bid_amount(adgroup_id, keyword_id, new_bid)
                if success:
                    self.bid_updated.emit(row, new_bid, (new_bid == max_bid))
                    # 키워드 정보 업데이트
                    self.keywords_info[index] = (
                        row, ad_ids, adgroup_id, keyword_id, keyword,
                        display_type, target_rank, new_bid, max_bid, campaign_type
                    )
    
    def _recheck_keywords(self):
        """키워드 재확인"""
        for index, info in enumerate(self.keywords_info):
            if self._stop_flag:
                break
                
            row, ad_ids, adgroup_id, keyword_id, keyword, display_type, target_rank, current_bid, max_bid, campaign_type = info
            
            if keyword_id in self.finished_keywords:
                continue
                
            # 현재 순위 재조회
            keyword_info = KeywordInfo(
                ncc_keyword_id=keyword_id,
                ncc_adgroup_id=adgroup_id,
                ncc_campaign_id="",
                keyword=keyword,
                bid_amount=current_bid,
                user_lock=False,
                ad_ids=ad_ids
            )
            
            display_enum = DisplayType.PC if display_type == "PC" else DisplayType.MOBILE
            rank = self.rank_adapter.get_current_rank(keyword_info, display_enum)
            rank_text = str(rank) if rank is not None else "순위밖"
            self.rank_updated.emit(row, rank_text)
            
            # 목표 달성 확인
            if rank == target_rank:
                self.finished_keywords.add(keyword_id)
                self.target_reached.emit(
                    row, current_bid, rank_text,
                    datetime.now().strftime('%m-%d %H:%M'), False
                )
                continue
                
            # 무한루프 방지 로직
            diff_state = 'worse' if (rank is None or rank > target_rank) else 'better'
            prev = self.prev_states[keyword_id]
            
            if prev is not None and prev != diff_state and prev != 'initial':
                self.toggle_counts[keyword_id] += 1
                if self.toggle_counts[keyword_id] >= 3:
                    logger.warning(f"무한루프 의심으로 키워드 제외: {keyword}")
                    self.finished_keywords.add(keyword_id)
                    continue
                    
            self.prev_states[keyword_id] = diff_state
            self.keyword_state[keyword_id] = diff_state
            
            # 입찰가 조정
            new_bid = self._calculate_new_bid(rank, target_rank, current_bid, max_bid)
            
            if new_bid != current_bid:
                success = self.service.update_bid_amount(adgroup_id, keyword_id, new_bid)
                if success:
                    self.bid_updated.emit(row, new_bid, (new_bid == max_bid))
                    self.keywords_info[index] = (
                        row, ad_ids, adgroup_id, keyword_id, keyword,
                        display_type, target_rank, new_bid, max_bid, campaign_type
                    )
    
    def _calculate_new_bid(self, current_rank: Optional[int], target_rank: int, 
                          current_bid: int, max_bid: int) -> int:
        """새로운 입찰가 계산"""
        if current_rank is None:
            # 순위밖인 경우 대폭 증가
            diff = 999
            increment = self.settings.large_diff_increment
            new_bid = min(current_bid + increment, max_bid)
        elif current_rank > target_rank:
            # 순위가 낮은 경우 입찰가 증가
            diff = current_rank - target_rank
            increment = (self.settings.large_diff_increment 
                        if diff >= self.settings.max_rank_threshold 
                        else self.settings.default_increment)
            new_bid = min(current_bid + increment, max_bid)
        else:
            # 순위가 높은 경우 입찰가 감소
            diff = target_rank - current_rank
            increment = (self.settings.large_diff_increment 
                        if diff >= self.settings.max_rank_threshold 
                        else self.settings.default_increment)
            new_bid = max(current_bid - increment, self.settings.min_bid)
            
        return new_bid
    
    def _wait_with_signal(self, seconds: int):
        """대기 시간 동안 시그널 발생"""
        for i in range(seconds):
            if self._stop_flag:
                self.remaining_seconds.emit(0)
                return
            time.sleep(1)
            self.remaining_seconds.emit(seconds - i)
    
    def stop(self):
        """워커 중지"""
        self._stop_flag = True
        self.remaining_seconds.emit(0)


class KeywordStatusWorker(QThread):
    """키워드 상태 변경 워커"""
    
    finished = Signal(bool, str)  # success, keyword_id
    
    def __init__(self, service: PowerlinkAutomationService, keyword_id: str, new_status: bool):
        super().__init__()
        self.service = service
        self.keyword_id = keyword_id
        self.new_status = new_status
    
    def run(self):
        """상태 변경 실행"""
        success = self.service.update_keyword_status(self.keyword_id, self.new_status)
        self.finished.emit(success, self.keyword_id)