import threading
from typing import Optional, List

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer


class QmlSocketClientBridge(QObject):
    """
    面向 QML 的桥接类（仅 Socket）：
    - 暴露 runShell / getFile 同步与异步槽
    - 提供 connectSocket/close 管理连接
    - 提供 connected / busy 只读属性与状态信号
    - 不改动原始 Client/SocketCommunicator 代码

    典型用法（Python）:
        bridge = QmlSocketClientBridge(Client, SocketCommunicator)
        engine.rootContext().setContextProperty("ClientBridge", bridge)

    典型用法（QML）:
        // 连接
        // ClientBridge.connectSocket("127.0.0.1", 9000)

        // 异步执行命令
        // ClientBridge.runShellAsync("ls -la")
        // ClientBridge.runShellFinished.connect(function(out) { console.log(out) })

        // 异步下载
        // ClientBridge.getFileAsync("/remote/path", "/local/save")
        // ClientBridge.getFileFinished.connect(function(paths) { console.log(paths) })
    """

    # 结果信号
    runShellFinished = Signal(str)
    getFileFinished = Signal(list)  # QVariantList in QML

    # 状态/错误信号
    errorOccurred = Signal(str)
    connectedChanged = Signal(bool)
    busyChanged = Signal(bool)

    def __init__(
        self,
        client_cls,  # 传入你的 Client 类
        socket_cls,  # 传入你的 SocketCommunicator 类
        parent: Optional[QObject] = None,
        max_message_size: int = 1024 * 1024,
    ):
        super().__init__(parent)
        self._client_cls = client_cls
        self._socket_cls = socket_cls
        self._client: Optional[object] = None
        self._connected = False
        self._busy = False
        self._lock = threading.RLock()
        self._max_message_size = int(max_message_size)

    # ---------- 属性 ----------

    def _get_connected(self) -> bool:
        return self._connected

    connected = Property(bool, fget=_get_connected, notify=connectedChanged)

    def _get_busy(self) -> bool:
        return self._busy

    busy = Property(bool, fget=_get_busy, notify=busyChanged)

    # ---------- 内部工具 ----------

    def _post(self, fn, *args, **kwargs):
        # 将调用切回主线程
        QTimer.singleShot(0, lambda: fn(*args, **kwargs))

    def _set_connected(self, v: bool):
        if self._connected != v:
            self._connected = v
            self.connectedChanged.emit(v)

    def _set_busy(self, v: bool):
        if self._busy != v:
            self._busy = v
            self.busyChanged.emit(v)

    def _ensure_connected(self):
        if not self._client:
            raise RuntimeError("尚未连接：请先调用 connectSocket(host, port)")

    def _run_async(self, func, on_success_signal: Optional[Signal], *args, **kwargs):
        # 简单串行化，避免并发操作
        with self._lock:
            if self._busy:
                self.errorOccurred.emit("忙碌中：上一个操作尚未完成")
                return
            # 在主线程标记 busy
            self._set_busy(True)

        def worker():
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                self.errorOccurred.emit(str(e))
            else:
                if on_success_signal is not None:
                    on_success_signal.emit(result)
            finally:
                # 切回主线程清除 busy
                self._post(self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, int, result=bool)
    def connectSocket(self, host: str, port: int) -> bool:
        try:
            with self._lock:
                if self._client:
                    self.close()
                comm = self._socket_cls(host, int(port))
                self._client = self._client_cls(
                    comm, max_message_size=self._max_message_size
                )
                self._set_connected(True)
            return True
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self._set_connected(False)
            return False

    @Slot()
    def close(self):
        with self._lock:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
                self._set_connected(False)

    @Slot(int)
    def setMaxMessageSize(self, size: int):
        # 仅影响后续创建的新 Client；已存在实例不变
        self._max_message_size = int(size)

    # ---------- 同步槽（可能阻塞 UI，谨慎使用） ----------

    @Slot(str, result=str)
    def runShell(self, command: str) -> str:
        try:
            self._ensure_connected()
            out = self._client.run_shell(command)
            if out is None:
                self.errorOccurred.emit("连接中断或超时")
                return ""
            return str(out)
        except Exception as e:
            self.errorOccurred.emit(str(e))
            return ""

    @Slot(str, str, result=list)
    def getFile(self, remote_path: str, dest_root: str = "") -> List[str]:
        try:
            self._ensure_connected()
            dest = dest_root or None
            paths = self._client.get_file(remote_path, dest)
            return list(paths or [])
        except Exception as e:
            self.errorOccurred.emit(str(e))
            return []

    # ---------- 异步槽（推荐） ----------

    @Slot(str)
    def runShellAsync(self, command: str):
        def _op(cmd: str) -> str:
            self._ensure_connected()
            out = self._client.run_shell(cmd)
            return "" if out is None else str(out)

        self._run_async(_op, self.runShellFinished, command)

    @Slot(str, str)
    def getFileAsync(self, remote_path: str, dest_root: str = ""):
        def _op(rp: str, dr: str) -> List[str]:
            self._ensure_connected()
            dest = dr or None
            return list(self._client.get_file(rp, dest))

        self._run_async(_op, self.getFileFinished, remote_path, dest_root)
