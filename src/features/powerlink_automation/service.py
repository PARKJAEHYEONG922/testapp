"""
파워링크 자동화 서비스
"""
import time
import hmac
import hashlib
import base64
from typing import List, Dict, Optional, Tuple
from src.foundation.logging import get_logger
from src.foundation.http_client import HTTPClient
from .models import Campaign, AdGroup, KeywordInfo, ApiCredentials, CampaignType, DisplayType

logger = get_logger("powerlink_automation.service")


class PowerlinkAutomationService:
    """파워링크 자동화 서비스"""
    
    BASE_URL = 'https://api.searchad.naver.com'
    
    def __init__(self):
        self.http_client = HTTPClient()
        self.credentials = ApiCredentials()
        
    def set_credentials(self, api_key: str, secret_key: str, customer_id: str):
        """API 인증 정보 설정"""
        self.credentials = ApiCredentials(api_key, secret_key, customer_id)
        
    def _get_header(self, method: str, uri: str) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        if not self.credentials.is_valid():
            raise ValueError("API 인증 정보가 설정되지 않았습니다")
            
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}.{method}.{uri}"
        signature = hmac.new(
            self.credentials.secret_key.encode('utf-8'), 
            message.encode('utf-8'), 
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature).decode('utf-8')

        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": self.credentials.api_key,
            "X-Customer": str(self.credentials.customer_id),
            "X-Signature": signature
        }
    
    def test_connection(self) -> Tuple[bool, str]:
        """API 연결 테스트"""
        try:
            headers = self._get_header('GET', '/ncc/campaigns')
            response = self.http_client.get(
                f"{self.BASE_URL}/ncc/campaigns",
                headers=headers
            )
            
            if response.status_code == 200:
                return True, "연결 성공"
            else:
                return False, f"연결 실패: {response.status_code}"
                
        except Exception as e:
            logger.error(f"API 연결 테스트 실패: {e}")
            return False, f"연결 오류: {str(e)}"
    
    def get_bizmoney_balance(self) -> str:
        """비즈머니 잔액 조회"""
        try:
            headers = self._get_header('GET', '/billing/bizmoney')
            response = self.http_client.get(
                f"{self.BASE_URL}/billing/bizmoney",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return str(data.get('bizmoney', '알 수 없음'))
            else:
                return "조회 실패"
                
        except Exception as e:
            logger.error(f"비즈머니 조회 실패: {e}")
            return "오류"
    
    def fetch_campaigns(self) -> List[Campaign]:
        """캠페인 목록 조회 (웹사이트/파워링크만)"""
        try:
            headers = self._get_header('GET', '/ncc/campaigns')
            response = self.http_client.get(
                f"{self.BASE_URL}/ncc/campaigns",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"캠페인 조회 실패: {response.status_code}")
                return []
                
            campaigns_data = response.json()
            campaigns = []
            
            for campaign_data in campaigns_data:
                campaign_id = campaign_data['nccCampaignId']
                
                # 캠페인 상세 정보로 타입 확인
                campaign_type = self._get_campaign_type(campaign_id)
                
                # 웹사이트(파워링크) 캠페인만 추가
                if campaign_type == CampaignType.WEB_SITE:
                    campaign = Campaign(
                        ncc_campaign_id=campaign_id,
                        name=campaign_data['name'],
                        campaign_type=campaign_type,
                        status=campaign_data.get('status', '')
                    )
                    campaigns.append(campaign)
                    
            return campaigns
            
        except Exception as e:
            logger.error(f"캠페인 조회 오류: {e}")
            return []
    
    def _get_campaign_type(self, campaign_id: str) -> CampaignType:
        """캠페인 타입 조회"""
        try:
            headers = self._get_header('GET', f'/ncc/campaigns/{campaign_id}')
            response = self.http_client.get(
                f"{self.BASE_URL}/ncc/campaigns/{campaign_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                campaign_tp = data.get('campaignTp', 'UNKNOWN')
                return CampaignType.WEB_SITE if campaign_tp == 'WEB_SITE' else CampaignType.SHOPPING
            else:
                return CampaignType.SHOPPING  # 기본적으로 제외
                
        except Exception as e:
            logger.error(f"캠페인 타입 조회 오류: {e}")
            return CampaignType.SHOPPING
    
    def fetch_adgroups(self, campaign_id: str) -> List[AdGroup]:
        """광고그룹 목록 조회"""
        try:
            headers = self._get_header('GET', '/ncc/adgroups')
            response = self.http_client.get(
                f"{self.BASE_URL}/ncc/adgroups?nccCampaignId={campaign_id}",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"광고그룹 조회 실패: {response.status_code}")
                return []
                
            adgroups_data = response.json()
            adgroups = []
            
            for adgroup_data in adgroups_data:
                adgroup_id = adgroup_data['nccAdgroupId']
                display_type = self._get_display_type(adgroup_id)
                
                adgroup = AdGroup(
                    ncc_adgroup_id=adgroup_id,
                    ncc_campaign_id=campaign_id,
                    name=adgroup_data['name'],
                    display_type=display_type
                )
                adgroups.append(adgroup)
                
            return adgroups
            
        except Exception as e:
            logger.error(f"광고그룹 조회 오류: {e}")
            return []
    
    def _get_display_type(self, adgroup_id: str) -> DisplayType:
        """광고그룹의 디스플레이 타입 조회"""
        try:
            headers = self._get_header('GET', f'/ncc/adgroups/{adgroup_id}')
            response = self.http_client.get(
                f"{self.BASE_URL}/ncc/adgroups/{adgroup_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                targets = data.get('targets', [])
                
                for target in targets:
                    if target['targetTp'] == 'PC_MOBILE_TARGET':
                        pc = target.get('target', {}).get('pc', False)
                        mobile = target.get('target', {}).get('mobile', False)
                        
                        if pc and mobile:
                            return DisplayType.PC_MOBILE
                        elif pc:
                            return DisplayType.PC
                        elif mobile:
                            return DisplayType.MOBILE
                            
            return DisplayType.PC  # 기본값
            
        except Exception as e:
            logger.error(f"디스플레이 타입 조회 오류: {e}")
            return DisplayType.PC
    
    def fetch_keywords(self, adgroup_id: str) -> List[KeywordInfo]:
        """키워드 목록 조회"""
        try:
            headers = self._get_header('GET', '/ncc/keywords')
            response = self.http_client.get(
                f"{self.BASE_URL}/ncc/keywords?nccAdgroupId={adgroup_id}",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"키워드 조회 실패: {response.status_code}")
                return []
                
            keywords_data = response.json()
            keywords = []
            
            # 광고 ID 목록도 가져오기
            ad_ids = self._fetch_ad_ids(adgroup_id)
            
            for keyword_data in keywords_data:
                keyword = KeywordInfo(
                    ncc_keyword_id=keyword_data['nccKeywordId'],
                    ncc_adgroup_id=adgroup_id,
                    ncc_campaign_id=keyword_data['nccCampaignId'],
                    keyword=keyword_data['keyword'],
                    bid_amount=keyword_data.get('bidAmt', 0),
                    user_lock=keyword_data.get('userLock', True),
                    ad_ids=ad_ids
                )
                keywords.append(keyword)
                
            return keywords
            
        except Exception as e:
            logger.error(f"키워드 조회 오류: {e}")
            return []
    
    def _fetch_ad_ids(self, adgroup_id: str) -> List[str]:
        """광고 ID 목록 조회"""
        try:
            headers = self._get_header('GET', '/ncc/ads')
            response = self.http_client.get(
                f"{self.BASE_URL}/ncc/ads?nccAdgroupId={adgroup_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                ads_data = response.json()
                return [ad['nccAdId'] for ad in ads_data]
            else:
                return []
                
        except Exception as e:
            logger.error(f"광고 ID 조회 오류: {e}")
            return []
    
    def update_keyword_status(self, keyword_id: str, user_lock: bool) -> bool:
        """키워드 상태 업데이트"""
        try:
            endpoint = f"/ncc/keywords/{keyword_id}"
            headers = self._get_header('PUT', endpoint)
            payload = {'userLock': user_lock}
            fields = 'userLock'
            
            response = self.http_client.put(
                f"{self.BASE_URL}{endpoint}?fields={fields}",
                headers=headers,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"키워드 상태 업데이트 오류: {e}")
            return False
    
    def update_bid_amount(self, adgroup_id: str, keyword_id: str, new_bid: int) -> bool:
        """입찰가 업데이트"""
        try:
            keyword_data = {
                "nccAdgroupId": adgroup_id,
                "bidAmt": new_bid,
                "useGroupBidAmt": False
            }
            endpoint = f"/ncc/keywords/{keyword_id}"
            fields = 'bidAmt,nccAdgroupId,useGroupBidAmt'
            headers = self._get_header('PUT', endpoint)
            
            response = self.http_client.put(
                f"{self.BASE_URL}{endpoint}?fields={fields}",
                headers=headers,
                json=keyword_data
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"입찰가 업데이트 오류: {e}")
            return False