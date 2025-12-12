from pprint import pprint
from pathlib import Path
import time
from PySide6.QtCore import (
    QObject,
    Property,
    Signal,
    QAbstractListModel,
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    Slot,
    QByteArray,
)
import random
import csv

from voc_app.logging_config import get_logger

logger = get_logger(__name__)


# 暴露列名和数据
class ColumnData(QObject):
    columnNameChanged = Signal()
    dataPointsChanged = Signal()

    def __init__(self, name="", points=None, parent=None):
        super().__init__(parent)
        self._column_name = name
        self._data_points = points if points is not None else []

    @Property(str, notify=columnNameChanged)
    def columnName(self):
        return self._column_name

    @Property("QVariantList", notify=dataPointsChanged)  # pyright: ignore
    def dataPoints(self):
        return self._data_points


class SeriesTableModel(QAbstractTableModel):
    """二维表格模型，供 VXYModelMapper 动态映射 X/Y 数据。"""

    boundsChanged = Signal()

    def __init__(self, max_rows=120, parent=None):
        super().__init__(parent)
        self._rows = []
        self._max_rows = max_rows
        self._min_x = 0.0
        self._max_x = 0.0
        self._min_y = 0.0
        self._max_y = 0.0
        self._has_data = False

    @Property(int)
    def maxRows(self):  # pyright: ignore[reportRedeclaration]
        return self._max_rows

    @maxRows.setter
    def maxRows(self, value):
        if value <= 0 or value == self._max_rows:
            return
        self._max_rows = value
        if len(self._rows) > self._max_rows:
            # 超出限制后主动裁剪，确保内存可控
            overflow = len(self._rows) - self._max_rows
            self.beginRemoveRows(QModelIndex(), 0, overflow - 1)
            del self._rows[:overflow]
            self.endRemoveRows()
            if self._recalculate_bounds():
                self.boundsChanged.emit()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return 0 if parent.isValid() else 2

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole):
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        return row[index.column()]

    @Property(float, notify=boundsChanged)
    def minX(self):
        return self._min_x

    @Property(float, notify=boundsChanged)
    def maxX(self):
        return self._max_x

    @Property(float, notify=boundsChanged)
    def minY(self):
        return self._min_y

    @Property(float, notify=boundsChanged)
    def maxY(self):
        return self._max_y

    @Property(bool, notify=boundsChanged)
    def hasData(self):
        return bool(self._rows)

    @Slot(float, float)
    def append_point(self, x, y):
        """向表格追加一条新数据，同时维护最大行数和坐标范围。"""
        x = float(x)
        y = float(y)
        bounds_changed = False

        if len(self._rows) == self._max_rows and self._rows:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self._rows.pop(0)
            self.endRemoveRows()
            bounds_changed = self._recalculate_bounds()

        row_index = len(self._rows)
        self.beginInsertRows(QModelIndex(), row_index, row_index)
        self._rows.append([x, y])
        self.endInsertRows()
        bounds_changed = self._update_bounds(x, y) or bounds_changed

        if bounds_changed:
            self.boundsChanged.emit()

    @Slot()
    def clear(self):
        """清空全部数据并重置坐标范围。"""
        if (
            not self._rows
            and self._min_x == self._max_x == self._min_y == self._max_y == 0.0
            and not self._has_data
        ):
            return

        self.beginResetModel()
        self._rows.clear()
        self._min_x = self._max_x = 0.0
        self._min_y = self._max_y = 0.0
        self._has_data = False
        self.endResetModel()
        self.boundsChanged.emit()

    @Slot()
    def force_rebuild(self):
        """强制 QML 视图完全重建模型，用于解决动态加载后无法显示存量数据的问题。"""
        self.beginResetModel()
        self.endResetModel()

    def _update_bounds(self, x, y):
        """增量更新坐标边界，减少不必要的遍历。"""
        if not self._rows:
            return False

        changed = False
        if len(self._rows) == 1:
            if (
                self._min_x != x
                or self._max_x != x
                or self._min_y != y
                or self._max_y != y
            ):
                self._min_x = self._max_x = x
                self._min_y = self._max_y = y
                self._has_data = True
                changed = True
            return changed

        if x < self._min_x:
            self._min_x = x
            changed = True
        if x > self._max_x:
            self._max_x = x
            changed = True
        if y < self._min_y:
            self._min_y = y
            changed = True
        if y > self._max_y:
            self._max_y = y
            changed = True
        self._has_data = True
        return changed

    def _recalculate_bounds(self):
        """当移除旧数据后重算一次边界。"""
        if not self._rows:
            changed = any(
                value != 0.0
                for value in (self._min_x, self._max_x, self._min_y, self._max_y)
            )
            self._min_x = self._max_x = 0.0
            self._min_y = self._max_y = 0.0
            self._has_data = False
            return changed

        xs = [row[0] for row in self._rows]
        ys = [row[1] for row in self._rows]
        new_min_x = min(xs)
        new_max_x = max(xs)
        new_min_y = min(ys)
        new_max_y = max(ys)
        self._has_data = True
        if (
            new_min_x == self._min_x
            and new_max_x == self._max_x
            and new_min_y == self._min_y
            and new_max_y == self._max_y
        ):
            return False
        self._min_x = new_min_x
        self._max_x = new_max_x
        self._min_y = new_min_y
        self._max_y = new_max_y
        return True


class ChartDataGenerator(QObject):
    """简单的随机数发生器，用于演示动态追加数据。"""

    def __init__(self, series_model, parent=None):
        super().__init__(parent)
        self._series_model = series_model
        self._last_timestamp_ms = 0.0

    @Property(QObject, constant=True)
    def seriesModel(self):
        return self._series_model

    @Slot()
    def generate_new_point(self):
        raw_ts = time.time() * 1000.0
        # 确保时间戳单调递增，避免瞬时多次调用时出现相同值
        if raw_ts <= self._last_timestamp_ms:
            raw_ts = self._last_timestamp_ms + 1.0
        self._last_timestamp_ms = raw_ts
        new_y = random.uniform(0, 100)
        self._series_model.append_point(raw_ts, new_y)


# QML 的 model.x 实际上是通过暴露 roleNames 的返回值来查到对应的角色值，再调用 data 方法获取数据
class ChartDataListModel(QAbstractListModel):
    """为 QML 提供多条曲线的元数据，便于拓展更多图表。"""

    TitleRole = Qt.ItemDataRole.UserRole + 1
    SeriesModelRole = Qt.ItemDataRole.UserRole + 2
    XColumnRole = Qt.ItemDataRole.UserRole + 3
    YColumnRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return 0 if parent.isValid() else len(self._entries)

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._entries)):
            return None

        entry = self._entries[index.row()]
        if role == self.TitleRole:
            return entry["title"]
        if role == self.SeriesModelRole:
            return entry["series_model"]
        if role == self.XColumnRole:
            return entry["x_column"]
        if role == self.YColumnRole:
            return entry["y_column"]
        return None

    def roleNames(self):
        return {
            self.TitleRole: QByteArray(b"title"),
            self.SeriesModelRole: QByteArray(b"seriesModel"),
            self.XColumnRole: QByteArray(b"xColumn"),
            self.YColumnRole: QByteArray(b"yColumn"),
        }

    def addSeries(self, title, series_model, x_column=0, y_column=1):
        """向模型追加一条曲线描述，方便 QML 动态显示。"""
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._entries.append(
            {
                "title": title,
                "series_model": series_model,
                "x_column": x_column,
                "y_column": y_column,
            }
        )
        self.endInsertRows()

    @Slot(int, result="QVariantMap") # pyright: ignore
    def get(self, row):
        """允许 QML 通过索引读取单条曲线的详细信息。"""
        if not (0 <= row < len(self._entries)):
            return {}
        entry = self._entries[row]
        return {
            "title": entry["title"],
            "seriesModel": entry["series_model"],
            "xColumn": entry["x_column"],
            "yColumn": entry["y_column"],
        }


class CsvDataModel(QAbstractListModel):
    ColumnNameRole = Qt.ItemDataRole.UserRole + 1
    DataPointsRole = Qt.ItemDataRole.UserRole + 2
    columnNamesChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._column_names = []

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        item = self._data[index.row()]
        if role == self.ColumnNameRole:
            return item.columnName
        if role == self.DataPointsRole:
            return item.dataPoints
        return None

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return len(self._data)

    def roleNames(self):
        return {
            self.ColumnNameRole: QByteArray(b"columnName"),
            self.DataPointsRole: QByteArray(b"dataPoints"),
        }

    @Property("QStringList", notify=columnNamesChanged) # pyright: ignore
    def columnNames(self):
        return self._column_names

    def resetModelData(self, data):
        # 告诉视图模型数据即将要被重置
        self.beginResetModel()
        self._data = data
        self.endResetModel()
        new_names = [item.columnName for item in self._data]
        if new_names != self._column_names:
            self._column_names = new_names
            self.columnNamesChanged.emit()

    @Slot(int, result="QVariantMap") # pyright: ignore
    def get(self, row):
        if not (0 <= row < len(self._data)):
            return {}
        item = self._data[row]
        return {"columnName": item.columnName, "dataPoints": item.dataPoints}


class CsvFileManager(QObject):
    csvFilesChanged = Signal()
    activeFileChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_dir = Path(__file__).parent / "Log"
        self._csv_files = []
        self._data_model = CsvDataModel(self)
        self._active_file = ""
        self.list_csv_files()

    @Property(list, notify=csvFilesChanged)
    def csvFiles(self):
        return self._csv_files

    @Property(str, notify=activeFileChanged)
    def activeFile(self):
        return self._active_file

    # constant 表示属性值不会改变
    @Property(QObject, constant=True)
    def dataModel(self):
        return self._data_model

    def list_csv_files(self):
        if not self._log_dir.exists():
            logger.debug(f"创建日志目录: {self._log_dir}")
            self._log_dir.mkdir()

        files = []
        for path in self._log_dir.rglob("*.csv"):
            if path.is_file():
                files.append(path.relative_to(self._log_dir).as_posix())
        files.sort()
        # 更新文件列表并发出信号
        if self._csv_files != files:
            logger.debug(f"发现 {len(files)} 个 CSV 文件")
            self._csv_files = files
            self.csvFilesChanged.emit()

    @Slot(str)
    def parse_csv_file(self, filename):
        relative_path = Path(filename)
        file_path = self._log_dir / relative_path
        if not file_path.exists():
            logger.warning(f"CSV 文件不存在: {file_path}")
            self._data_model.resetModelData([])
            return

        logger.info(f"解析 CSV 文件: {file_path}")

        def to_milliseconds(value: float) -> float:
            """将时间值归一化为毫秒时间戳，支持秒/毫秒或相对秒。"""
            if value > 1e12:
                return value  # 已是毫秒
            if value > 1e9:
                return value * 1000.0  # 秒级时间戳
            return value * 1000.0  # 相对秒

        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            # 读取第一行作为列名
            header = next(reader)

            parsed_data = []
            # 跳过第一列（时间列）
            column_names = header[1:]
            # 每列一个列表
            for name in column_names:
                parsed_data.append([])

            for row in reader:
                try:
                    time_val = to_milliseconds(float(row[0]))
                    for i in range(1, len(row)):
                        parsed_data[i - 1].append({"x": time_val, "y": float(row[i])})
                except (ValueError, IndexError):
                    continue

        final_data = []
        for i, name in enumerate(column_names):
            final_data.append(
                ColumnData(name=name, points=parsed_data[i], parent=self._data_model)
            )

        self._data_model.resetModelData(final_data)

        normalized = relative_path.as_posix()
        if self._active_file != normalized:
            self._active_file = normalized
            self.activeFileChanged.emit()
