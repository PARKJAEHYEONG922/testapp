"""
API 연결 상태 체크 및 로그 출력
시작 시 API 설정 확인하여 로그 창에 결과 표시
"""
from src.foundation.config import config_manager
from src.foundation.logging import get_logger
from src.desktop.common_log import log_manager

logger = get_logger("desktop.api_checker")


class APIChecker:
    """API 연결 상태 확인"""
    _last_check_result = None
    _last_check_ts = 0
    _last_overall_ready = False
    AI_FEATURES_ENABLED = True  # AI API도 처음부터 확인
    
    @staticmethod
    def get_last_overall_ready() -> bool:
        return bool(APIChecker._last_overall_ready)
    
    @staticmethod
    def invalidate_all_caches():
        APIChecker._last_check_result = None
        APIChecker._last_check_ts = 0
        APIChecker._last_overall_ready = False
    
    @staticmethod
    def check_all_apis_on_startup():
        """시작 시 모든 API 상태 확인 (조용한 모드)"""
        try:
            # API 설정 로드
            api_config = config_manager.load_api_config()
            
            # 각 API 상태 확인
            naver_developer_status = APIChecker._check_naver_developer(api_config)
            naver_searchad_status = APIChecker._check_naver_searchad(api_config)
            ai_api_status = APIChecker._check_ai_apis(api_config)
            
            # 조용한 요약만 출력 (개별 API 상태는 생략)
            APIChecker._log_summary_quiet(api_config, naver_developer_status, naver_searchad_status, ai_api_status)
            
            result = api_config.is_complete() and api_config.is_shopping_valid() and api_config.is_searchad_valid()
            APIChecker._last_overall_ready = result
            return result
            
        except Exception as e:
            logger.error(f"API 상태 확인 오류: {e}")
            log_manager.add_log(f"❌ API 상태 확인 중 오류 발생: {str(e)}", "error")
            return False
    
    @staticmethod  
    def check_all_apis_detailed():
        """상세한 API 상태 확인 (API 설정 변경 후 사용)"""
        try:
            log_manager.add_log("🔗 API 연결 상태를 확인하는 중...", "info")
            
            # API 설정 로드
            api_config = config_manager.load_api_config()
            
            # 각 API 상태 확인
            naver_developer_status = APIChecker._check_naver_developer(api_config)
            naver_searchad_status = APIChecker._check_naver_searchad(api_config)
            ai_api_status = APIChecker._check_ai_apis(api_config)
            
            # 상세 로그 출력 (네이버 API는 필수, AI API는 선택)
            APIChecker._log_api_status("네이버 개발자 API", naver_developer_status, required=True)
            APIChecker._log_api_status("네이버 검색광고 API", naver_searchad_status, required=True)
            APIChecker._log_api_status("AI API", ai_api_status, required=False)
            
            # 상세 전체 상태 요약
            APIChecker._log_summary(api_config)
            
            result = api_config.is_complete() and api_config.is_shopping_valid() and api_config.is_searchad_valid()
            APIChecker._last_overall_ready = result
            return result
            
        except Exception as e:
            logger.error(f"API 상태 확인 오류: {e}")
            log_manager.add_log(f"❌ API 상태 확인 중 오류 발생: {str(e)}", "error")
            return False
    
    @staticmethod
    def _check_naver_developer(api_config) -> dict:
        """네이버 개발자 API 상태 확인 (쇼핑 API)"""
        if not api_config.is_shopping_valid():
            return {
                "configured": False,
                "connected": False,
                "message": "API 키가 설정되지 않음"
            }
        
        try:
            # 간단한 연결 테스트 (실제 API 호출 없이 설정만 확인)
            return {
                "configured": True,
                "connected": True,
                "message": "설정 완료"
            }
        except Exception as e:
            return {
                "configured": True,
                "connected": False,
                "message": f"연결 오류: {str(e)}"
            }
    
    @staticmethod
    def _check_naver_searchad(api_config) -> dict:
        """네이버 검색광고 API 상태 확인"""
        if not api_config.is_searchad_valid():
            return {
                "configured": False,
                "connected": False,
                "message": "API 키가 설정되지 않음"
            }
        
        try:
            return {
                "configured": True,
                "connected": True,
                "message": "설정 완료"
            }
        except Exception as e:
            return {
                "configured": True,
                "connected": False,
                "message": f"연결 오류: {str(e)}"
            }
    
    @staticmethod
    def _check_ai_apis(api_config) -> dict:
        """AI API 통합 상태 확인 (OpenAI, Claude, Gemini 중 하나라도 설정되면 OK)"""
        # Gemini API 키도 확인해야 함 (api_config에 gemini_api_key 필드가 있다고 가정)
        gemini_key = getattr(api_config, 'gemini_api_key', '')
        
        # 하나라도 설정되어 있으면 OK
        if api_config.openai_api_key or api_config.claude_api_key or gemini_key:
            configured_apis = []
            if api_config.openai_api_key:
                configured_apis.append("OpenAI")
            if api_config.claude_api_key:
                configured_apis.append("Claude")
            if gemini_key:
                configured_apis.append("Gemini")
            
            # 현재 선택된 AI 모델 정보 추가
            current_model = getattr(api_config, 'current_ai_model', '')
            if current_model and current_model != "AI 제공자를 선택하세요":
                message = f"설정 완료 ({', '.join(configured_apis)}) - 현재 모델: {current_model}"
            else:
                message = f"설정 완료 ({', '.join(configured_apis)}) - 모델 미선택"
            
            return {
                "configured": True,
                "connected": True,
                "message": message
            }
        else:
            return {
                "configured": False,
                "connected": False,
                "message": "미설정 (선택사항)"
            }
    
    @staticmethod
    def _log_api_status(api_name: str, status: dict, required: bool = True):
        """API 상태를 로그에 출력"""
        if status["configured"] and status["connected"]:
            # 정상 설정됨
            log_manager.add_log(f"✅ {api_name}: {status['message']}", "success")
        elif status["configured"] and not status["connected"]:
            # 설정됨but 연결 오류
            log_manager.add_log(f"⚠️ {api_name}: {status['message']}", "warning")
        else:
            # 설정되지 않음
            if required:
                log_manager.add_log(f"❌ {api_name}: {status['message']} (필수)", "error")
            else:
                log_manager.add_log(f"⚪ {api_name}: {status['message']}", "info")
    
    @staticmethod
    def _log_summary_quiet(api_config, naver_dev_status, naver_search_status, ai_status):
        """전체 API 상태 조용한 요약 (시작 시 사용)"""
        # 네이버 API 상태 확인
        naver_dev_ready = naver_dev_status["configured"] and naver_dev_status["connected"]
        naver_search_ready = naver_search_status["configured"] and naver_search_status["connected"]
        ai_ready = ai_status["configured"] and ai_status["connected"]
        
        if naver_dev_ready and naver_search_ready:
            # AI 상태도 함께 표시
            if ai_ready:
                log_manager.add_log("✅ 모든 API 설정 완료 (네이버 + AI)", "success")
            else:
                log_manager.add_log("✅ 필수 API 설정 완료 (AI 미설정)", "success")
        else:
            # 구체적인 API 이름으로 안내
            missing_apis = []
            if not naver_dev_ready:
                missing_apis.append("네이버 개발자 API")
            if not naver_search_ready:
                missing_apis.append("네이버 검색광고 API")
            
            missing_text = ", ".join(missing_apis)
            log_manager.add_log(f"⚠️ {missing_text} 미설정", "warning")
    
    @staticmethod
    def _log_summary(api_config):
        """전체 API 상태 상세 요약 (API 설정 변경 시 사용)"""
        # 네이버 개발자 API와 검색광고 API 둘 다 필수
        naver_dev_ready = api_config.is_shopping_valid()
        naver_search_ready = api_config.is_searchad_valid()
        
        if naver_dev_ready and naver_search_ready:
            log_manager.add_log("🎉 모든 필수 네이버 API가 설정되었습니다! 키워드 분석 기능을 정상 사용할 수 있습니다.", "success")
        else:
            missing_apis = []
            if not naver_dev_ready:
                missing_apis.append("네이버 개발자 API")
            if not naver_search_ready:
                missing_apis.append("네이버 검색광고 API")
            
            log_manager.add_log(f"⚠️ 필수 API {len(missing_apis)}개가 설정되지 않았습니다: {', '.join(missing_apis)}", "warning")
            log_manager.add_log("📋 상단 메뉴의 'API 설정'에서 누락된 API를 설정해주세요.", "info")
            log_manager.add_log("💡 일부 키워드 분석 기능이 제한될 수 있습니다.", "info")
    
    @staticmethod
    def get_missing_required_apis() -> list:
        """설정되지 않은 필수 API 목록 반환"""
        api_config = config_manager.load_api_config()
        missing = []
        
        # 네이버 개발자 API와 검색광고 API 둘 다 확인
        if not api_config.is_shopping_valid():
            missing.append("네이버 개발자 API")
        
        if not api_config.is_searchad_valid():
            missing.append("네이버 검색광고 API")
        
        return missing
    
    @staticmethod
    def is_ready_for_full_functionality() -> bool:
        """모든 기능 사용 가능한지 확인"""
        api_config = config_manager.load_api_config()
        # 네이버 API 둘 다 설정되어 있어야 완전한 기능 사용 가능
        return api_config.is_shopping_valid() and api_config.is_searchad_valid()
    
    @staticmethod
    def show_api_setup_dialog(parent_widget, feature_name: str = "기능") -> bool:
        """
        API 설정 안내 다이얼로그 표시 - 공용 메서드
        
        Args:
            parent_widget: 부모 위젯
            feature_name: 기능명 (예: "순위 확인", "키워드 추가", "새 프로젝트 생성")
            
        Returns:
            bool: API 설정이 완료되었거나 사용자가 계속 진행을 선택했으면 True
        """
        try:
            logger.info(f"API 설정 확인 시작 - {feature_name}")
            
            # API 준비 상태 확인
            if APIChecker.is_ready_for_full_functionality():
                logger.info("API 설정이 완료되어 있음")
                return True
                
            # 설정되지 않은 API 목록 가져오기
            missing_apis = APIChecker.get_missing_required_apis()
            logger.info(f"누락된 API: {missing_apis}")
            
            if not missing_apis:
                logger.info("누락된 API 없음")
                return True
                
            from src.toolbox.ui_kit.modern_dialog import ModernConfirmDialog
            
            apis_text = ", ".join(missing_apis)
            logger.info(f"API 설정 다이얼로그 표시 중: {apis_text}")
            
            result = ModernConfirmDialog.question(
                parent_widget,
                "API 설정 필요", 
                f"🔑 {apis_text}가 설정되지 않았습니다.\n\n"
                f"{feature_name} 기능을 사용하기 위해서는\n"
                "네이버 API 설정이 필요합니다.\n\n"
                "지금 API 설정 창으로 이동하시겠습니까?",
                confirm_text="API 설정하기",
                cancel_text="나중에"
            )
            
            logger.info(f"사용자 선택 결과: {result}")
            
            if result == ModernConfirmDialog.Accepted:
                # API 설정 다이얼로그 열기
                APIChecker._open_api_settings_dialog(parent_widget)
            
            return False
            
        except Exception as e:
            logger.error(f"API 설정 다이얼로그 표시 중 오류: {e}")
            import traceback
            logger.error(f"전체 traceback: {traceback.format_exc()}")
            return False  # 오류 발생시 진행하지 않도록
    
    @staticmethod
    def _open_api_settings_dialog(parent_widget):
        """API 설정 다이얼로그 열기 - 내부 메서드"""
        try:
            from src.desktop.api_dialog import APISettingsDialog
            
            # 메인 윈도우 찾기
            main_window = parent_widget.window() if parent_widget else None
            dialog = APISettingsDialog(main_window)
            
            if dialog.exec() == dialog.Accepted:
                log_manager.add_log("✅ API 설정이 완료되었습니다.", "success")
                # 캐시 무효화 (새로운 설정 반영)
                APIChecker.invalidate_all_caches()
            
        except Exception as e:
            logger.error(f"API 설정 다이얼로그 열기 실패: {e}")
            log_manager.add_log(f"❌ API 설정 창을 열 수 없습니다: {str(e)}", "error")


def check_api_status_on_startup():
    """
    시작 시 API 상태 확인 (메인 함수)
    애플리케이션 시작 시 호출
    """
    return APIChecker.check_all_apis_on_startup()


def log_api_requirements_reminder():
    """API 설정 필요성 알림 (주기적 호출용)"""
    missing = APIChecker.get_missing_required_apis()
    
    if missing:
        apis_text = ", ".join(missing)
        log_manager.add_log(f"🔔 알림: {apis_text} 설정이 필요합니다.", "warning")
        log_manager.add_log("⚙️ 상단 메뉴 → API 설정에서 설정할 수 있습니다.", "info")


