from pathlib import Path

from PySide6.QtCore import QObject, Slot, QUrl

from voc_app.logging_config import get_logger

logger = get_logger(__name__)


class FilePreviewController(QObject):
    """Expose helper slots to QML for loading file contents."""

    @Slot(str, result=str)
    def readFile(self, path: str) -> str:
        target = Path(path)
        if not target.is_file():
            logger.debug(f"文件不存在: {path}")
            return ""
        try:
            content = target.read_text(encoding="utf-8")
            logger.debug(f"读取文件成功: {path} ({len(content)} 字节)")
            return content
        except UnicodeDecodeError:
            logger.warning(f"无法以 UTF-8 读取文件: {path}")
            return "[无法以 UTF-8 读取该文件]"
        except OSError as exc:  # e.g. 权限问题
            logger.error(f"读取文件出错: {path} - {exc}")
            return f"[读取文件时出错: {exc}]"

    @Slot(str, result=str)
    def pathToUrl(self, path: str) -> str:
        if not path:
            return ""
        return QUrl.fromLocalFile(path).toString()

    @Slot(str, result=str)
    def urlToPath(self, url: str) -> str:
        if not url:
            return ""
        return QUrl(url).toLocalFile()
