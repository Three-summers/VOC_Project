from pathlib import Path

from PySide6.QtCore import QObject, Slot, QUrl


class FilePreviewController(QObject):
    """Expose helper slots to QML for loading file contents."""

    @Slot(str, result=str)
    def readFile(self, path: str) -> str:
        target = Path(path)
        if not target.is_file():
            return ""
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "[无法以 UTF-8 读取该文件]"
        except OSError as exc:  # e.g. 权限问题
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
