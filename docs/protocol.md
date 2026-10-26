# 数据协议

## USB 串口

115200 波特率，UTF-8，每行一个 JSON 对象。启动日志可能含非 JSON 文本，读取端应忽略。

```json
{"event":"heartbeat","pin":"D1/GPIO3","raw":1,"state":"CLEAR","contacts":0,"uptime_ms":1046}
```

| 字段 | 含义 |
| --- | --- |
| `event` | `ready` 启动、`contact` 接触、`released` 释放确认、`heartbeat` 心跳 |
| `pin` | 本项目为 `D1/GPIO3` |
| `raw` | 原始数字输入；0 为接通 GND，1 为高电平 |
| `state` | 防抖后的 `TOUCH` 或 `CLEAR` |
| `contacts` | 本次启动以来的接触次数；连续接触不重复累计 |
| `uptime_ms` | MicroPython 的 `ticks_ms()`，不是墙上时钟，长时间运行后会回绕 |

接触即时生效；连续高电平保持 200ms 后才确认分开。因此短暂断开时可能出现 `raw: 1, state: TOUCH`，网页应优先使用 `state`。

## 本机 HTTP

默认地址：`http://127.0.0.1:8765`。

### GET /api/status

```json
{
  "connected": true,
  "reading": {
    "event": "heartbeat",
    "pin": "D1/GPIO3",
    "raw": 0,
    "state": "TOUCH",
    "contacts": 1,
    "uptime_ms": 2046
  }
}
```

```sh
curl http://127.0.0.1:8765/api/status
```

`reading` 在第一次有效数据到来之前为 `null`。设备断开后可能保留最后一次读数，**必须先检查 `connected`**，不能把旧读数当成当前状态。

### GET /events

返回 `text/event-stream`，每条消息的 `data` 是与 `/api/status` 同结构的 JSON。开发板报告新事件时立即推送，无新事件时约每秒发送一次当前快照。

```js
const events = new EventSource('/events');
events.onmessage = event => {
  const snapshot = JSON.parse(event.data);
  if (!snapshot.connected) return console.log('检测暂停');
  console.log(snapshot.reading.state);
};
```

服务不提供向 GPIO 写入数据的 HTTP 接口；网页通过本机服务读取数据，不直接占用 USB 串口。
