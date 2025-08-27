"""
간단한 업데이트 테스트 프로그램
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QTextEdit
    from PySide6.QtCore import Qt, QTimer
    
    from src.foundation.version import version_info
    # 간단한 업데이트 체크만 테스트
    from src.foundation.version import UPDATE_CHECK_URL
    import requests
    from src.foundation.logging import get_logger
    
    logger = get_logger("test_updater")
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"업데이트 테스트 {version_info.get_version_string()}")
            self.resize(600, 400)
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QVBoxLayout()
            central_widget.setLayout(layout)
            
            # 타이틀
            title = QLabel(f"🔄 자동 업데이트 시스템 테스트")
            title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
            layout.addWidget(title)
            
            # 버전 정보
            version_label = QLabel(f"현재 버전: {version_info.get_version_string()}")
            version_label.setStyleSheet("font-size: 14px; margin: 5px;")
            layout.addWidget(version_label)
            
            # 업데이트 체크 버튼
            self.check_button = QPushButton("수동 업데이트 체크")
            self.check_button.clicked.connect(self.manual_update_check)
            layout.addWidget(self.check_button)
            
            # 로그 영역
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            layout.addWidget(self.log_area)
            
            # 자동 업데이트 시스템 설정
            self.setup_updater()
            
        def setup_updater(self):
            """업데이트 시스템 설정"""
            self.add_log("✅ 간단 업데이트 체크 시스템 초기화")
            self.add_log(f"📡 체크 URL: {UPDATE_CHECK_URL}")
            
            # 3초 후 자동 체크
            QTimer.singleShot(3000, self.auto_check)
            self.add_log("⏱️ 3초 후 업데이트 자동 체크 시작...")
        
        def auto_check(self):
            """자동 업데이트 체크"""
            self.add_log("🔄 자동 업데이트 체크 중...")
            self.manual_update_check()
        
        def manual_update_check(self):
            """수동 업데이트 체크"""
            self.add_log("🔍 수동 업데이트 체크 시작...")
            try:
                response = requests.get(UPDATE_CHECK_URL, timeout=10)
                response.raise_for_status()
                
                remote_data = response.json()
                remote_version = remote_data.get("latest_version", "")
                current_version = version_info.current_version
                
                self.add_log(f"📍 현재 버전: {current_version}")
                self.add_log(f"🌐 원격 버전: {remote_version}")
                
                if version_info.is_newer_version(remote_version):
                    self.add_log(f"🆙 새로운 버전 발견: {remote_version}")
                    self.add_log(f"📝 릴리즈 노트: {remote_data.get('release_notes', '정보 없음')}")
                    self.add_log(f"📦 파일 크기: {remote_data.get('file_size_mb', 0)}MB")
                    self.add_log(f"🔗 다운로드: {remote_data.get('download_url', '')}")
                else:
                    self.add_log("✅ 최신 버전입니다!")
                    
            except Exception as e:
                self.add_log(f"❌ 업데이트 체크 실패: {e}")
        
        def on_update_available(self, update_info):
            """업데이트 발견시 처리 (사용 안함)"""
            pass
        
        def on_update_check_failed(self, error_message):
            """업데이트 체크 실패시 처리 (사용 안함)"""
            pass
        
        def add_log(self, message):
            """로그 추가"""
            self.log_area.append(f"[{QTimer().currentTime().toString()}] {message}")
    
    def main():
        app = QApplication(sys.argv)
        
        window = TestWindow()
        window.show()
        
        sys.exit(app.exec())
    
    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"필수 패키지가 누락되었습니다: {e}")
    print("PySide6를 설치해주세요: pip install PySide6")
    sys.exit(1)