"""测试 alarm_store 模块"""
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import Qt

from voc_app.gui.alarm_store import AlarmModel, AlarmStore


class TestAlarmModel(unittest.TestCase):
    """测试 AlarmModel 类"""

    def setUp(self) -> None:
        self.model = AlarmModel()

    def test_initial_state(self) -> None:
        """测试初始状态"""
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.count, 0)

    def test_add_alarm(self) -> None:
        """测试添加告警"""
        self.model.add_alarm("2024-01-01 12:00:00", "测试告警")
        self.assertEqual(self.model.rowCount(), 1)
        self.assertEqual(self.model.count, 1)

    def test_add_multiple_alarms(self) -> None:
        """测试添加多个告警"""
        for i in range(5):
            self.model.add_alarm(f"2024-01-01 12:00:0{i}", f"告警 {i}")
        self.assertEqual(self.model.rowCount(), 5)
        self.assertEqual(self.model.count, 5)

    def test_data_timestamp_role(self) -> None:
        """测试获取时间戳数据"""
        self.model.add_alarm("2024-01-01 12:00:00", "测试告警")
        index = self.model.index(0, 0)
        timestamp = self.model.data(index, AlarmModel.TimestampRole)
        self.assertEqual(timestamp, "2024-01-01 12:00:00")

    def test_data_message_role(self) -> None:
        """测试获取消息数据"""
        self.model.add_alarm("2024-01-01 12:00:00", "测试告警消息")
        index = self.model.index(0, 0)
        message = self.model.data(index, AlarmModel.MessageRole)
        self.assertEqual(message, "测试告警消息")

    def test_data_invalid_index(self) -> None:
        """测试无效索引"""
        index = self.model.index(-1, 0)
        result = self.model.data(index, AlarmModel.TimestampRole)
        self.assertIsNone(result)

    def test_data_out_of_range(self) -> None:
        """测试越界索引"""
        self.model.add_alarm("2024-01-01 12:00:00", "测试")
        index = self.model.index(10, 0)  # 越界
        result = self.model.data(index, AlarmModel.TimestampRole)
        self.assertIsNone(result)

    def test_data_invalid_role(self) -> None:
        """测试无效角色"""
        self.model.add_alarm("2024-01-01 12:00:00", "测试")
        index = self.model.index(0, 0)
        result = self.model.data(index, Qt.ItemDataRole.DisplayRole)
        self.assertIsNone(result)

    def test_role_names(self) -> None:
        """测试角色名称"""
        roles = self.model.roleNames()
        self.assertIn(AlarmModel.TimestampRole, roles)
        self.assertIn(AlarmModel.MessageRole, roles)
        self.assertEqual(roles[AlarmModel.TimestampRole], b"timestamp")
        self.assertEqual(roles[AlarmModel.MessageRole], b"message")

    def test_clear(self) -> None:
        """测试清空告警"""
        self.model.add_alarm("2024-01-01 12:00:00", "告警1")
        self.model.add_alarm("2024-01-01 12:00:01", "告警2")
        self.model.clear()
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.count, 0)

    def test_clear_empty(self) -> None:
        """测试清空空列表"""
        self.model.clear()  # 不应该崩溃
        self.assertEqual(self.model.rowCount(), 0)

    def test_row_count_with_parent(self) -> None:
        """测试带父索引的 rowCount"""
        self.model.add_alarm("2024-01-01 12:00:00", "测试")
        # 有效的父索引应该返回 0
        parent_index = self.model.index(0, 0)
        self.assertEqual(self.model.rowCount(parent_index), 0)

    def test_count_changed_signal(self) -> None:
        """测试 countChanged 信号"""
        signal_received = []

        def on_count_changed():
            signal_received.append(True)

        self.model.countChanged.connect(on_count_changed)
        self.model.add_alarm("2024-01-01 12:00:00", "测试")
        self.assertTrue(len(signal_received) > 0)


class TestAlarmStore(unittest.TestCase):
    """测试 AlarmStore 类"""

    def setUp(self) -> None:
        self.store = AlarmStore()

    def test_initial_state(self) -> None:
        """测试初始状态"""
        self.assertFalse(self.store.hasActiveAlarm)

    def test_alarm_model_property(self) -> None:
        """测试 alarmModel 属性"""
        model = self.store.alarmModel
        self.assertIsInstance(model, AlarmModel)

    def test_add_alarm(self) -> None:
        """测试添加告警"""
        self.store.addAlarm("2024-01-01 12:00:00", "测试告警")
        self.assertTrue(self.store.hasActiveAlarm)

    def test_add_alarm_resets_acknowledged(self) -> None:
        """测试添加告警重置确认状态"""
        self.store.addAlarm("2024-01-01 12:00:00", "告警1")
        self.store.closeAlarms()
        self.assertFalse(self.store.hasActiveAlarm)

        self.store.addAlarm("2024-01-01 12:00:01", "告警2")
        self.assertTrue(self.store.hasActiveAlarm)

    def test_close_alarms(self) -> None:
        """测试关闭告警"""
        self.store.addAlarm("2024-01-01 12:00:00", "测试告警")
        self.assertTrue(self.store.hasActiveAlarm)

        self.store.closeAlarms()
        self.assertFalse(self.store.hasActiveAlarm)
        # 数据应该还在
        self.assertEqual(self.store.alarmModel.rowCount(), 1)

    def test_close_alarms_empty(self) -> None:
        """测试关闭空告警列表"""
        self.store.closeAlarms()  # 不应该崩溃
        self.assertFalse(self.store.hasActiveAlarm)

    def test_close_alarms_already_closed(self) -> None:
        """测试重复关闭"""
        self.store.addAlarm("2024-01-01 12:00:00", "测试告警")
        self.store.closeAlarms()
        self.store.closeAlarms()  # 再次关闭不应该崩溃
        self.assertFalse(self.store.hasActiveAlarm)

    def test_clear_alarms(self) -> None:
        """测试清空告警"""
        self.store.addAlarm("2024-01-01 12:00:00", "测试告警")
        self.store.clearAlarms()
        self.assertFalse(self.store.hasActiveAlarm)
        self.assertEqual(self.store.alarmModel.rowCount(), 0)

    def test_clear_alarms_empty(self) -> None:
        """测试清空空列表"""
        self.store.clearAlarms()  # 不应该崩溃
        self.assertFalse(self.store.hasActiveAlarm)

    def test_clear_alarms_after_close(self) -> None:
        """测试关闭后清空"""
        self.store.addAlarm("2024-01-01 12:00:00", "测试告警")
        self.store.closeAlarms()
        self.store.clearAlarms()
        self.assertEqual(self.store.alarmModel.rowCount(), 0)

    def test_has_active_alarm_signal(self) -> None:
        """测试 hasActiveAlarmChanged 信号"""
        signal_received = []

        def on_changed():
            signal_received.append(True)

        self.store.hasActiveAlarmChanged.connect(on_changed)
        self.store.addAlarm("2024-01-01 12:00:00", "测试")
        self.assertTrue(len(signal_received) > 0)

    def test_workflow_add_close_clear(self) -> None:
        """测试完整工作流"""
        # 添加告警
        self.store.addAlarm("2024-01-01 12:00:00", "告警1")
        self.store.addAlarm("2024-01-01 12:00:01", "告警2")
        self.assertTrue(self.store.hasActiveAlarm)
        self.assertEqual(self.store.alarmModel.rowCount(), 2)

        # 关闭告警（用户确认看到了）
        self.store.closeAlarms()
        self.assertFalse(self.store.hasActiveAlarm)
        self.assertEqual(self.store.alarmModel.rowCount(), 2)

        # 清空告警
        self.store.clearAlarms()
        self.assertFalse(self.store.hasActiveAlarm)
        self.assertEqual(self.store.alarmModel.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
