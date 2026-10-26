# 铁丝迷宫检测程序

完整安装与运行说明请查看 [仓库首页](../README.md)。

| 文件 | 作用 |
| --- | --- |
| `main.py` | 在 XIAO ESP32C3 上运行的 MicroPython 程序，D1 / GPIO3 检测 |
| `web_server.py` | 本机 USB 串口桥接与 HTTP/SSE 服务 |
| `monitor.py` | 单独运行的串口监视工具，不与网页服务同时使用 |
| `web/index.html` | 完整页面和 CSS，绿色 / 红色闪烁 |
| `web/app.js` | SSE 数据订阅、全屏切换 |
| `web/state.mjs` | 使用固件防抖状态决定页面显示 |

在仓库根目录启动：

```sh
python3 maze-detector/web_server.py
```

打开 <http://127.0.0.1:8765/>。默认自动选择 `/dev/cu.usbmodem*`，可通过 `--serial` 指定。

- [接线和电路图](../docs/wiring.md)
- [串口及 HTTP/SSE 协议](../docs/protocol.md)
- [排查与恢复原固件](../docs/troubleshooting.md)

运行时生成的 `backups/`、`logs/` 和 `firmware/` 不提交到仓库。
