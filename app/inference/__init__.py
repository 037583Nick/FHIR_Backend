# 使用更明確的導入方式
import os

# 設置環境變數（如果需要）
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

try:
    from .stemi import inference as stemiInf, STEMI_ICD_DICT
except ImportError as e:
    # 如果相對導入失敗，嘗試絕對導入
    try:
        from app.inference.stemi import inference as stemiInf, STEMI_ICD_DICT
    except ImportError:
        # 如果都失敗，提供錯誤信息
        import warnings
        warnings.warn(f"Cannot import stemiInf and STEMI_ICD_DICT: {e}")
        stemiInf = None
        STEMI_ICD_DICT = None

# 確保導出到模組命名空間
__all__ = ['stemiInf', 'STEMI_ICD_DICT']
