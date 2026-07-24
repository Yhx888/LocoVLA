"""工程部署阶段的可复现构建与数值一致性实验。"""

REQUIRED_LOG_FIELDS: tuple[str, ...] = (
    "timestamp_ns",
    "episode_id",
    "git_commit",
    "pitch_rad",
    "pitch_rate_rad_s",
    "raw_torque_common_nm",
    "clamped_torque_common_nm",
    "safety_flag",
    "loop_cycle_ms",
)
