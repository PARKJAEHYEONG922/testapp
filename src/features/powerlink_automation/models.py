"""
파워링크 자동화 데이터 모델
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class CampaignType(Enum):
    WEB_SITE = "WEB_SITE"
    SHOPPING = "SHOPPING"


class DisplayType(Enum):
    PC = "PC"
    MOBILE = "Mobile"
    PC_MOBILE = "PC & Mobile"


@dataclass
class Campaign:
    """캠페인 정보"""
    ncc_campaign_id: str
    name: str
    campaign_type: CampaignType
    status: str = ""


@dataclass
class AdGroup:
    """광고그룹 정보"""
    ncc_adgroup_id: str
    ncc_campaign_id: str
    name: str
    display_type: DisplayType = DisplayType.PC


@dataclass
class KeywordInfo:
    """키워드 정보"""
    ncc_keyword_id: str
    ncc_adgroup_id: str
    ncc_campaign_id: str
    keyword: str
    bid_amount: int
    user_lock: bool
    power_link_count: int = 0
    target_rank: int = 1
    current_rank: Optional[int] = None
    max_bid: int = 1000
    ad_ids: List[str] = field(default_factory=list)


@dataclass
class BidLog:
    """입찰 로그"""
    keyword_id: str
    timestamp: str
    target_rank: int
    current_rank: str
    current_bid: int
    new_bid: int
    target_reached: bool = False
    max_bid_reached: bool = False


@dataclass
class AutomationSettings:
    """자동화 설정"""
    default_increment: int = 10
    large_diff_increment: int = 30
    wait_time_minutes: int = 3
    min_bid: int = 70
    max_rank_threshold: int = 4


@dataclass
class ApiCredentials:
    """API 인증 정보"""
    api_key: str = ""
    secret_key: str = ""
    customer_id: str = ""
    
    def is_valid(self) -> bool:
        return bool(self.api_key and self.secret_key and self.customer_id)