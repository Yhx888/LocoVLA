# H09 WebSocket、遥测与安全

统一遥测契约位于 `src/upkie_mujoco_course/hardware/telemetry.py`。每帧必须包含 `schema_version`、严格递增的 `sequence` 与 `timestamp`、`proprioception`、6 维 `action`、左右轮力矩/电流、电池电压、急停、故障码和元数据。

实机发送前先在本地用 `write_telemetry_jsonl` 写入，再用 `load_telemetry_jsonl` 回读。过期序号、时间倒退、非有限数值或错误动作维度必须被拒绝，不能仅在仪表盘上隐藏异常点。

## 岗位任务

让网页遥控和遥测可用，同时保证网络断开、重复包、旧命令和默认凭据不会让机器人持续运动。

原仓库提供 AP/STA 两种 Wi-Fi 模式、WebSocket JSON 和 `192.168.1.11` 页面，并说明默认 Wi-Fi 密码由小写 Wi-Fi 名称派生。复刻时必须修改默认 Wi-Fi 凭据，不能把可预测密码带到公开场所。

每条命令包含序号、发送时间、有效期和目标值。控制器只接受序号递增且未过期的命令；超过心跳超时立即把高层速度清零，但低层平衡与急停仍在本地 MCU 执行。

故意错误：断开浏览器网络、重放旧 JSON、发送 NaN 和超范围值，确认都不会绕过限幅和急停。

验收：消息契约、断连制动时间、默认凭据整改、网络威胁模型和遥测丢包统计。
