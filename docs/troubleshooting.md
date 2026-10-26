# 常见问题

## 铁环贴着铁丝，仍然显示未接触

先访问 <http://127.0.0.1:8765/api/status> 查看实际读数。

- `connected: false`：先排查 USB 和开发板程序。
- `connected: true, raw: 1, state: CLEAR`：检测脚没有持续被拉低。
- `raw: 1, state: TOUCH`：处于短暂断开期间，释放防抖仍保持接触状态。
- `raw: 0, state: TOUCH`：当前电气接触正常。

看得见接触不代表电路导通。依次检查：

1. 铁丝和铁环是否有绝缘漆、涂层或氧化；接触处可打磨至裸露金属。
2. 红黑线连接金属件的位置是否可靠，不能仅压在涂层上。
3. 电阻下端、红线、绿线是否插在面包板同一半边的同一数字行。
4. 绿线是否接 D1 / GPIO3，黑线是否接 GND。

方便时可将红黑线的裸露末端直接相碰，保持几秒。若页面变红，问题集中在金属接触面或线头固定；若仍不变红，继续检查面包板和引脚。不要把 3V3 与 GND 直接短接。

## 晃动时红绿跳变

程序已经包含 200ms 释放确认。若断开超过 200ms，会按真实输入恢复绿色。需要更长容忍时间时，可调整 `main.py` 的 `RELEASE_DEBOUNCE_MS` 并重新上传，但这也会延迟正常分开后的显示。

## 找不到串口

```sh
ls /dev/cu.usbmodem*
```

确认 USB-C 线支持数据传输，重新连接后再次检查。串口名可能变化，运行服务或安装工具时更新 `--serial` / `--port`。

## 串口能识别，但是网页等待连接

- 关闭其他串口工具，避免同时读取。
- 确认开发板已上传本项目的 `main.py`。
- 首次使用新板时需先安装 MicroPython，再上传 `main.py`。
- 网页服务启动后会等待有效的 `D1/GPIO3` JSON 消息，识别到串口不等于程序已正常输出。

## 烧录连接失败

先停止网页服务和其他串口程序。自动进入下载模式失败时，可按住 BOOT，再按一下 RESET，释放 BOOT 后重试。不要在服务仍占用串口时同时烧录。

## 恢复原有固件

`scripts/setup_board.py --install-runtime` 会在 `maze-detector/backups/` 生成带时间戳的完整备份。备份仅保存在运行安装工具的电脑，不包含在仓库内。

停止网页服务后，使用实际备份文件名：

```sh
source .venv/bin/activate
python -m esptool --chip esp32c3 --port /dev/cu.usbmodem1101 --baud 460800 write_flash --erase-all 0 maze-detector/backups/original-flash-YYYYMMDD-HHMMSS.bin
```

恢复会替换当前 MicroPython 和检测程序。不要使用其他设备的备份。
