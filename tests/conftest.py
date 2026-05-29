import sys
from pathlib import Path

# 添加后端路径到sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))
