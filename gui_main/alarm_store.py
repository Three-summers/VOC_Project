from PySide6.QtCore import (
    QObject,
    QAbstractListModel,
    QModelIndex,
    Qt,
    QByteArray,
    Property,
    Signal,
    Slot,
)


class AlarmModel(QAbstractListModel):
    TimestampRole = Qt.ItemDataRole.UserRole + 1
    MessageRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        try:
            item = self._items[index.row()]
        except IndexError:
            return None

        if role == self.TimestampRole:
            return item["timestamp"]
        if role == self.MessageRole:
            return item["message"]
        return None

    def roleNames(self):
        return {
            self.TimestampRole: QByteArray(b"timestamp"),
            self.MessageRole: QByteArray(b"message"),
        }

    def add_alarm(self, timestamp: str, message: str):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._items.append({"timestamp": timestamp, "message": message})
        self.endInsertRows()

    def clear(self):
        if not self._items:
            return
        self.beginResetModel()
        self._items = []
        self.endResetModel()


class AlarmStore(QObject):
    # 用于响应式，当信号被触发会直接引起 QML 响应
    hasActiveAlarmChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = AlarmModel(self)
        self._acknowledged = False

    @Property(QObject, constant=True)
    def alarmModel(self):
        return self._model

    # 执行流程是，当信号被发送，QML 会意识到值可能会发生变化，会调用其 getter 函数，这个函数就会被调用
    @Property(bool, notify=hasActiveAlarmChanged)
    def hasActiveAlarm(self):
        return self._model.rowCount() > 0 and not self._acknowledged

    @Slot(str, str)
    def addAlarm(self, timestamp: str, message: str):
        self._model.add_alarm(timestamp, message)
        self._acknowledged = False
        self.hasActiveAlarmChanged.emit()

    @Slot()
    def closeAlarms(self):
        if self._model.rowCount() == 0:
            return
        if not self._acknowledged:
            self._acknowledged = True
            self.hasActiveAlarmChanged.emit()

    @Slot()
    def clearAlarms(self):
        if self._model.rowCount() == 0 and not self._acknowledged:
            return
        self._model.clear()
        self._acknowledged = False
        self.hasActiveAlarmChanged.emit()
