"""
파워링크 자동화 어댑터
"""
import time
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchWindowException
from typing import List, Optional
from src.foundation.logging import get_logger
from .models import KeywordInfo, DisplayType

logger = get_logger("powerlink_automation.adapters")


class PowerlinkRankAdapter:
    """파워링크 순위 조회 어댑터"""
    
    def __init__(self):
        self.driver = None
        
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        if self.driver is None:
            options = Options()
            options.headless = True
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            options.add_argument(f"user-agent={user_agent}")
            options.add_argument("Accept-Language=ko,en-US;q=0.9,en;q=0.8")
            self.driver = webdriver.Chrome(options=options)
        return self.driver
    
    def close_driver(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def get_powerlink_count(self, keyword: str, display_type: DisplayType) -> int:
        """파워링크 개수 조회 (HTTP 요청 방식)"""
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                    if display_type == DisplayType.PC
                    else 'Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Mobile Safari/537.36'
                ),
                'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8'
            }
            
            url = (
                f"https://search.naver.com/search.naver?query={keyword}"
                if display_type == DisplayType.PC
                else f"https://m.search.naver.com/search.naver?query={keyword}"
            )
            
            max_attempts = 5
            for attempt in range(max_attempts):
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    if display_type == DisplayType.PC:
                        power_link_count = len(soup.find_all('div', class_='title_url_area'))
                    else:
                        power_link_count = len(soup.find_all('div', class_='url_area'))
                        
                    if power_link_count > 0:
                        return power_link_count
                        
                time.sleep(7)  # 요청 간격
                
            return 0
            
        except Exception as e:
            logger.error(f"파워링크 개수 조회 오류: {e}")
            return 0
    
    def get_current_rank(self, keyword_info: KeywordInfo, display_type: DisplayType) -> Optional[int]:
        """현재 순위 조회 (Selenium 방식)"""
        try:
            if not self.driver:
                self.setup_driver()
                
            base_url = (
                "https://ad.search.naver.com/search.naver?where=ad&query="
                if display_type == DisplayType.PC
                else "https://m.ad.search.naver.com/search.naver?where=m_expd&query="
            )
            
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    self.driver.get(base_url + keyword_info.keyword)
                    time.sleep(1)
                    
                    elements = self.driver.find_elements(By.TAG_NAME, 'a')
                    for element in elements:
                        onclick_attr = element.get_attribute('onclick')
                        if onclick_attr:
                            for ad_id in keyword_info.ad_ids:
                                if display_type == DisplayType.PC:
                                    pattern = rf"clickcr\(this, '.*','{ad_id}','(\d+)',event\);"
                                else:
                                    pattern = rf"nclk\(this, 'sct.desc', '{ad_id}', (\d+)\);"
                                
                                match = re.search(pattern, onclick_attr)
                                if match:
                                    rank_str = match.group(1)
                                    if rank_str.isdigit():
                                        return int(rank_str)
                                        
                except Exception as e:
                    logger.warning(f"순위 조회 시도 {attempt + 1} 실패: {e}")
                    
            return None
            
        except Exception as e:
            logger.error(f"순위 조회 오류: {e}")
            return None