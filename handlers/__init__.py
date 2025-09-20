
"""
حزمة معالجات البوت
"""

from .user import router as user_router
from .admin import router as admin_router
from .pricing_admin import router as pricing_router

__all__ = ['user_router', 'admin_router', 'pricing_router']
