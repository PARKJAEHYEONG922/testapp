"""
파워링크 자동화 모듈
"""

def register(app):
    """메인 앱에 파워링크 자동화 모듈 등록"""
    from .ui_main import PowerlinkAutomationWidget
    
    widget = PowerlinkAutomationWidget()
    app.add_feature_tab(widget, '🚀 파워링크 자동입찰')