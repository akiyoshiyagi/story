"""
設定関連のパッケージ
"""
from .criteria_mapping import CRITERIA_MAPPING, CRITERIA_PRIORITY
from .settings import get_settings

__all__ = [
    'CRITERIA_MAPPING',
    'CRITERIA_PRIORITY',
    'get_settings'
] 