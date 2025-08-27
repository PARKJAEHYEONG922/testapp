"""
버전 관리 시스템
앱 버전 정보와 업데이트 관련 설정 관리
"""
from datetime import datetime
from typing import Dict, Any, Optional

# 현재 앱 버전 정보
VERSION = "1.0.0"
BUILD_DATE = datetime.now().strftime("%Y-%m-%d")
BUILD_NUMBER = "1"

# 업데이트 관련 설정
UPDATE_CHECK_URL = "https://drive.google.com/uc?id=1G16TCJc40lmakzU5f9lR5N4CcK0x4Igb"
UPDATE_DOWNLOAD_BASE_URL = "https://drive.google.com/uc?id="

# 앱 식별 정보
APP_NAME = "통합관리프로그램"
APP_INTERNAL_NAME = "integrated_management_system"
COMPANY_NAME = "YourTeam"

class VersionInfo:
    """버전 정보 클래스"""
    
    def __init__(self):
        self.current_version = VERSION
        self.build_date = BUILD_DATE
        self.build_number = BUILD_NUMBER
    
    def get_version_string(self) -> str:
        """표시용 버전 문자열 반환"""
        return f"v{self.current_version} (빌드 {self.build_number})"
    
    def get_full_version_info(self) -> Dict[str, str]:
        """전체 버전 정보 반환"""
        return {
            "version": self.current_version,
            "build_date": self.build_date,
            "build_number": self.build_number,
            "app_name": APP_NAME,
            "internal_name": APP_INTERNAL_NAME
        }
    
    def is_newer_version(self, remote_version: str) -> bool:
        """원격 버전이 현재 버전보다 새로운지 확인"""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            remote_parts = [int(x) for x in remote_version.split('.')]
            
            # 버전 길이 맞추기 (1.0 vs 1.0.0)
            max_len = max(len(current_parts), len(remote_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            remote_parts.extend([0] * (max_len - len(remote_parts)))
            
            return remote_parts > current_parts
            
        except (ValueError, AttributeError):
            return False

# 전역 버전 정보 인스턴스
version_info = VersionInfo()

def get_version_info() -> VersionInfo:
    """버전 정보 인스턴스 반환"""
    return version_info