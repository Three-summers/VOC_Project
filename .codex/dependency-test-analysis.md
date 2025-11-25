# 依賴與測試覆蓋評估（2025-11-24T10:45:00+08:00）

## 依賴現況

| 元件 | 來源 | 作用 | 狀態 | 證據 |
| --- | --- | --- | --- | --- |
| PySide6 | `src/voc_app/gui/app.py`, `src/voc_app/loadport/main.py` | 提供 QApplication/QCoreApplication、QQml 渲染與訊號槽 | **缺失**：`verification.md` 與 `.codex/testing.md` 多次記錄 ModuleNotFoundError | `verification.md` 中 GUI/CLI 命令皆因 `No module named 'PySide6'` 中止 |
| RPi.GPIO | `src/voc_app/loadport/GPIOController.py` | 控制 loadport 硬體輸入輸出 | **缺失**：`testing.md` 早期記錄 `No module named 'RPi'` | `src/voc_app/loadport/GPIOController.py` 頂部 `import RPi.GPIO as GPIO` 無 try/except；`.codex/testing.md` 第一條命令失敗 |
| pyserial (可選) | `src/voc_app/loadport/serial_device.py` | GenericSerialDevice 預設串口實現 | **可選**：若未安裝需傳入 `serial_factory` | `serial_device.py` 中 `try: import serial ... except ImportError: serial=None`，單測利用內存串口通過 |

## 測試與驗證覆蓋

| 類型 | 命令 | 狀態 | 覆蓋內容 | 缺口 |
| --- | --- | --- | --- | --- |
| 單元測試 | `python3 -m unittest tests/test_serial_device.py` | ✅ 通過（見 `.codex/testing.md` 2025-11-19T16:09:05） | 驗證 GenericSerialDevice 的命令發送和響應處理 | 僅覆蓋串口模組，不含 GUI/E84 |
| GUI 冒煙 | `QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app` | ⚠️ 阻塞（PySide6 缺失） | 預期檢查 GUI 與 LoadportBridge 交互 | 目前無法在此環境執行；需安裝 PySide6 並提供 RPi.GPIO 模擬 |
| Loadport CLI | `python3 -m voc_app.loadport.main`（或 QT_QPA_PLATFORM=offscreen） | ⚠️ 阻塞（PySide6 缺失） | 驗證 E84ControllerThread 與 ConsoleBridge 事件 | 同上 |
| 手動示例 | `python examples/ascii_serial_demo.py --port ...` | ⚪ 未在此環境嘗試 | 演示 GenericSerialDevice ASCII 命令流 | 需物理串口設備；可在實機測試 |

## 小結

- 目前僅串口單元測試可在容器中重複；GUI 與 loadport 均受 PySide6/RPi.GPIO 缺失阻塞。
- 如果目標是驗證 GUI + E84 控制，需要提供：
  1. 可安裝 PySide6 的環境（或允許透過系統套件）。
  2. 對 RPi.GPIO 的模擬層，或在實際 Raspberry Pi 上執行。
  3. 專用的冒煙腳本或自動化測試，避免純手動檢查。
- 串口庫可藉由目前的單元測試與 ASCII 示範證明可用性，惟建議再增加更多命令/錯誤路徑測試。
