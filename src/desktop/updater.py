"""
자동 업데이트 모듈
Google Drive 기반 업데이트 시스템
"""
import json
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta

try:
    from PySide6.QtCore import QObject, Signal, QThread, QTimer
    from PySide6.QtWidgets import QMessageBox, QProgressDialog
    from PySide6.QtGui import QPixmap
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    Signal = None

import requests

from ..foundation.logging import get_logger
from ..foundation.version import version_info, UPDATE_CHECK_URL, UPDATE_DOWNLOAD_BASE_URL
# from ..toolbox.ui_kit.modern_dialog import ModernProgressDialog

logger = get_logger("desktop.updater")

class UpdateInfo:
    """업데이트 정보 클래스"""
    
    def __init__(self, data: Dict[str, Any]):
        self.latest_version = data.get("latest_version", "")
        self.download_url = data.get("download_url", "")
        self.release_notes = data.get("release_notes", "")
        self.release_date = data.get("release_date", "")
        self.file_size = data.get("file_size_mb", 0)
        self.minimum_version = data.get("minimum_version", "")
        self.force_update = data.get("force_update", False)
    
    def is_valid(self) -> bool:
        """업데이트 정보가 유효한지 확인"""
        return bool(self.latest_version and self.download_url)
    
    def is_force_update_required(self) -> bool:
        """강제 업데이트가 필요한지 확인"""
        return self.force_update


class UpdateDownloader(QObject if QT_AVAILABLE else object):
    """업데이트 다운로더 (스레드 안전)"""
    
    if QT_AVAILABLE:
        progress_updated = Signal(int)  # 진행률 (0-100)
        download_completed = Signal(str)  # 다운로드된 파일 경로
        download_failed = Signal(str)  # 에러 메시지
    
    def __init__(self):
        if QT_AVAILABLE:
            super().__init__()
        self.cancelled = False
    
    def download_update(self, url: str, file_size_mb: int = 0):
        """업데이트 파일 다운로드"""
        try:
            # 임시 파일 경로 생성
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.exe")
            
            logger.info(f"업데이트 다운로드 시작: {url}")
            
            # 다운로드 시작
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            if total_size == 0 and file_size_mb > 0:
                total_size = file_size_mb * 1024 * 1024  # MB를 바이트로 변환
            
            downloaded = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancelled:
                        logger.info("다운로드 취소됨")
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                        return
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 진행률 업데이트
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            if QT_AVAILABLE and hasattr(self, 'progress_updated'):
                                self.progress_updated.emit(progress)
            
            logger.info(f"다운로드 완료: {temp_file}")
            if QT_AVAILABLE and hasattr(self, 'download_completed'):
                self.download_completed.emit(temp_file)
            
        except Exception as e:
            error_msg = f"다운로드 실패: {str(e)}"
            logger.error(error_msg)
            if QT_AVAILABLE and hasattr(self, 'download_failed'):
                self.download_failed.emit(error_msg)
    
    def cancel_download(self):
        """다운로드 취소"""
        self.cancelled = True


class AutoUpdater(QObject if QT_AVAILABLE else object):
    """자동 업데이트 관리자"""
    
    if QT_AVAILABLE:
        update_available = Signal(object)  # UpdateInfo 객체
        update_check_failed = Signal(str)  # 에러 메시지
    
    def __init__(self, parent=None):
        if QT_AVAILABLE:
            super().__init__(parent)
        
        self.last_check_time = None
        self.check_interval_hours = 4  # 4시간마다 체크
        self.update_dialog = None
        
        # 자동 체크 타이머 (Qt 사용 가능시)
        if QT_AVAILABLE:
            self.check_timer = QTimer()
            self.check_timer.timeout.connect(self.check_for_updates)
            self.check_timer.start(self.check_interval_hours * 60 * 60 * 1000)  # ms 단위
    
    def should_check_for_updates(self) -> bool:
        """업데이트 체크가 필요한지 확인"""
        if not self.last_check_time:
            return True
        
        time_diff = datetime.now() - self.last_check_time
        return time_diff.total_seconds() > (self.check_interval_hours * 3600)
    
    def check_for_updates(self, force: bool = False) -> Optional[UpdateInfo]:
        """업데이트 확인"""
        try:
            if not force and not self.should_check_for_updates():
                logger.debug("업데이트 체크 스킵 (시간 간격)")
                return None
            
            logger.info("업데이트 체크 시작")
            
            # 원격 버전 정보 가져오기
            response = requests.get(UPDATE_CHECK_URL, timeout=10)
            response.raise_for_status()
            
            remote_data = response.json()
            update_info = UpdateInfo(remote_data)
            
            self.last_check_time = datetime.now()
            
            if not update_info.is_valid():
                logger.warning("유효하지 않은 업데이트 정보")
                return None
            
            # 버전 비교
            if version_info.is_newer_version(update_info.latest_version):
                logger.info(f"새로운 버전 발견: {update_info.latest_version}")
                
                if QT_AVAILABLE and hasattr(self, 'update_available'):
                    self.update_available.emit(update_info)
                
                return update_info
            else:
                logger.info("최신 버전입니다")
                return None
                
        except Exception as e:
            error_msg = f"업데이트 체크 실패: {str(e)}"
            logger.error(error_msg)
            
            if QT_AVAILABLE and hasattr(self, 'update_check_failed'):
                self.update_check_failed.emit(error_msg)
            
            return None
    
    def show_update_dialog(self, update_info: UpdateInfo):
        """업데이트 알림 다이얼로그 표시"""
        if not QT_AVAILABLE:
            return
        
        from PySide6.QtWidgets import QApplication
        
        if not QApplication.instance():
            return
        
        # 강제 업데이트인 경우
        if update_info.is_force_update_required():
            title = "필수 업데이트"
            message = f"""
새로운 버전 {update_info.latest_version}이 출시되었습니다.
이 업데이트는 필수입니다.

업데이트 내용:
{update_info.release_notes}

파일 크기: {update_info.file_size}MB
출시일: {update_info.release_date}

지금 업데이트하시겠습니까?
            """.strip()
            
            reply = QMessageBox.critical(
                None, title, message,
                QMessageBox.Yes, QMessageBox.Yes  # 강제 업데이트는 선택권 없음
            )
        else:
            # 일반 업데이트
            title = "업데이트 알림"
            message = f"""
새로운 버전 {update_info.latest_version}이 출시되었습니다.

업데이트 내용:
{update_info.release_notes}

파일 크기: {update_info.file_size}MB
출시일: {update_info.release_date}

지금 업데이트하시겠습니까?
            """.strip()
            
            reply = QMessageBox.question(
                None, title, message,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
        
        if reply == QMessageBox.Yes:
            self.start_update(update_info)
    
    def start_update(self, update_info: UpdateInfo):
        """업데이트 시작"""
        if not QT_AVAILABLE:
            return
        
        # 간단한 진행률 다이얼로그 생성 (QProgressDialog 사용)
        from PySide6.QtWidgets import QProgressDialog
        self.update_dialog = QProgressDialog(
            f"버전 {update_info.latest_version} 다운로드 중...",
            "취소", 0, 100, None
        )
        self.update_dialog.setWindowTitle("업데이트 다운로드")
        self.update_dialog.setModal(True)
        
        # 다운로더 생성
        self.downloader = UpdateDownloader()
        self.downloader.progress_updated.connect(self.update_dialog.setValue)
        self.downloader.download_completed.connect(self.on_download_completed)
        self.downloader.download_failed.connect(self.on_download_failed)
        
        # 취소 버튼 연결
        self.update_dialog.canceled.connect(self.downloader.cancel_download)
        
        self.update_dialog.show()
        
        # 다운로드 시작 (별도 스레드에서)
        from PySide6.QtCore import QThreadPool, QRunnable
        
        class DownloadTask(QRunnable):
            def __init__(self, downloader, url, file_size):
                super().__init__()
                self.downloader = downloader
                self.url = url
                self.file_size = file_size
            
            def run(self):
                self.downloader.download_update(self.url, self.file_size)
        
        task = DownloadTask(self.downloader, update_info.download_url, update_info.file_size)
        QThreadPool.globalInstance().start(task)
    
    def on_download_completed(self, file_path: str):
        """다운로드 완료 처리"""
        logger.info(f"업데이트 다운로드 완료: {file_path}")
        
        if self.update_dialog:
            self.update_dialog.close()
        
        # 업데이트 설치 확인
        reply = QMessageBox.question(
            None, "업데이트 설치",
            "다운로드가 완료되었습니다.\n지금 설치하고 프로그램을 재시작하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.install_update(file_path)
    
    def on_download_failed(self, error_message: str):
        """다운로드 실패 처리"""
        logger.error(f"업데이트 다운로드 실패: {error_message}")
        
        if self.update_dialog:
            self.update_dialog.close()
        
        QMessageBox.critical(
            None, "업데이트 실패",
            f"업데이트 다운로드에 실패했습니다:\n{error_message}"
        )
    
    def install_update(self, update_file_path: str):
        """업데이트 설치"""
        try:
            current_exe = sys.executable
            
            # 현재 실행 파일의 백업 생성
            backup_path = current_exe + ".backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            shutil.copy2(current_exe, backup_path)
            
            # 새 파일로 교체
            shutil.copy2(update_file_path, current_exe)
            
            # 임시 파일 삭제
            os.remove(update_file_path)
            
            logger.info("업데이트 설치 완료, 프로그램 재시작")
            
            # 프로그램 재시작
            subprocess.Popen([current_exe])
            
            # 현재 프로그램 종료
            if QT_AVAILABLE:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    app.quit()
            else:
                sys.exit(0)
                
        except Exception as e:
            error_msg = f"업데이트 설치 실패: {str(e)}"
            logger.error(error_msg)
            
            if QT_AVAILABLE:
                QMessageBox.critical(
                    None, "설치 실패", 
                    f"{error_msg}\n수동으로 업데이트 파일을 실행해 주세요:\n{update_file_path}"
                )

# 전역 업데이트 관리자 인스턴스
auto_updater = None

def get_auto_updater() -> AutoUpdater:
    """업데이트 관리자 인스턴스 반환"""
    global auto_updater
    if auto_updater is None:
        auto_updater = AutoUpdater()
    return auto_updater