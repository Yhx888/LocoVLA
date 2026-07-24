"""第 27 与 31 关学习控制实验的可复现实证。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.course.lab_io import finalize_lab_artifacts
from upkie_mujoco_course.envs.standing_env import StandingEnv
from upkie_mujoco_course.rl.evaluate import evaluate_policy
from upkie_mujoco_course.rl.train_sb3 import train_ppo_residual_standing, train_ppo_standing
from upkie_mujoco_course.utils.paths import project_root


RL_LAB_CHAPTERS = ("25", "26", "27", "28", "29", "30", "31")
_EPISODE_COUNT = 12
_SIM2REAL_RANDOMIZATION: dict[str, Any] = {
    "mass_scale": [0.90, 1.10],
    "friction_scale": [0.75, 1.20],
    "sensor_noise_std": [0.001, 0.004],
    "initial_state_std": [0.002, 0.012],
    "action_delay_steps": [0, 2],
    "push_force": [0.5, 1.5],
    "push_step": [35, 80],
    "push_duration_steps": [2, 5],
}
_CHAPTER_29_RUNTIME_RANDOMIZATION: dict[str, Any] = {
    "mass_scale": [0.90, 1.10],
    "inertia_scale": [0.90, 1.10],
    "com_offset_m": [-0.01, 0.01],
    "friction_scale": [0.75, 1.20],
    "joint_damping": [0.01, 0.10],
    "actuator_strength_scale": [0.85, 1.15],
    "sensor_noise_std": [0.001, 0.004],
    "action_delay_steps": [0, 2],
}


@dataclass(frozen=True)
class PolicyGradientEstimate:
    analytic_gradient: float
    raw_mean: float
    baseline_mean: float
    raw_variance: float
    baseline_variance: float
    raw_gradients: np.ndarray
    baseline_gradients: np.ndarray


def estimate_gaussian_policy_gradient(
    *,
    seed: int,
    batches: int,
    samples_per_batch: int,
    mean: float = 0.15,
    std: float = 0.45,
    target_action: float = 0.65,
) -> PolicyGradientEstimate:
    """在一维高斯策略上将 REINFORCE 样本梯度同解析梯度逐项比较。"""

    if batches <= 1 or samples_per_batch <= 1 or std <= 0.0:
        raise ValueError("批次数、每批样本数必须大于 1，且标准差必须为正")
    rng = np.random.default_rng(seed)
    actions = rng.normal(mean, std, size=(batches, samples_per_batch))
    reward = -np.square(actions - target_action)
    score = (actions - mean) / (std * std)
    value_baseline = -((mean - target_action) ** 2 + std * std)
    raw_gradients = np.mean(score * reward, axis=1)
    baseline_gradients = np.mean(score * (reward - value_baseline), axis=1)
    return PolicyGradientEstimate(
        analytic_gradient=float(-2.0 * (mean - target_action)),
        raw_mean=float(np.mean(raw_gradients)),
        baseline_mean=float(np.mean(baseline_gradients)),
        raw_variance=float(np.var(raw_gradients, ddof=1)),
        baseline_variance=float(np.var(baseline_gradients, ddof=1)),
        raw_gradients=raw_gradients,
        baseline_gradients=baseline_gradients,
    )


def _resolve_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    return root if root.is_absolute() else project_root() / root


def _save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _chapter_27(plot_path: Path, seed: int = 0) -> tuple[dict[str, float], dict[str, dict[str, float | str]], dict[str, Any]]:
    estimate = estimate_gaussian_policy_gradient(seed=seed, batches=320, samples_per_batch=128)
    raw_error = abs(estimate.raw_mean - estimate.analytic_gradient)
    baseline_error = abs(estimate.baseline_mean - estimate.analytic_gradient)
    reduction = estimate.raw_variance / estimate.baseline_variance
    metrics = {
        "analytic_gradient": estimate.analytic_gradient,
        "raw_gradient_absolute_error": float(raw_error),
        "baseline_gradient_absolute_error": float(baseline_error),
        "raw_gradient_variance": estimate.raw_variance,
        "baseline_gradient_variance": estimate.baseline_variance,
        "variance_reduction_ratio": float(reduction),
    }
    conditions = {
        "raw_gradient_absolute_error": {"operator": "<=", "value": 0.08},
        "baseline_gradient_absolute_error": {"operator": "<=", "value": 0.08},
        "variance_reduction_ratio": {"operator": ">=", "value": 1.5},
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.8, 4.2))
    axes[0].hist(estimate.raw_gradients, bins=28, alpha=0.62, color="#d36b27", label="REINFORCE")
    axes[0].hist(estimate.baseline_gradients, bins=28, alpha=0.62, color="#17745a", label="value baseline")
    axes[0].axvline(estimate.analytic_gradient, color="#17201d", linestyle="--", label="analytic gradient")
    axes[0].set(xlabel="gradient estimate", ylabel="batch count", title="Unbiasedness and variance")
    axes[0].legend()
    axes[1].bar(["raw", "baseline"], [estimate.raw_variance, estimate.baseline_variance], color=["#d36b27", "#17745a"])
    axes[1].set(ylabel="sample-gradient variance", title=f"Variance reduction: {reduction:.2f}x")
    for axis in axes:
        axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "model": {
            "policy": "a ~ Normal(mu=0.15, sigma=0.45)",
            "reward": "-(a - 0.65)^2",
            "action_unit": "normalized action",
        },
        "batches": 320,
        "samples_per_batch": 128,
        "metrics": metrics,
    }


def _rollout_classic_controller(
    randomization: dict[str, Any] | None,
    *,
    episodes: int,
    seed: int,
) -> list[dict[str, Any]]:
    env = StandingEnv(max_episode_steps=160, randomization=randomization)
    controller = WheelBalancerController()
    records: list[dict[str, Any]] = []
    try:
        for episode in range(episodes):
            _, reset_info = env.reset(seed=seed + episode)
            controller.reset()
            total_return = 0.0
            peak_pitch = 0.0
            terminated = False
            truncated = False
            steps = 0
            while not (terminated or truncated):
                physical_action = controller.compute_action(env.runner, env.runner.time)
                action = env.to_normalized_action(physical_action)
                _, reward, terminated, truncated, info = env.step(action)
                total_return += float(reward)
                peak_pitch = max(peak_pitch, abs(float(info["pitch_error"])))
                steps += 1
            records.append(
                {
                    "episode": episode,
                    "seed": seed + episode,
                    "return": total_return,
                    "steps": steps,
                    "success": bool(truncated and not terminated),
                    "terminated": bool(terminated),
                    "peak_pitch_rad": peak_pitch,
                    "randomization": reset_info["randomization"],
                }
            )
    finally:
        env.close()
    return records


def _bootstrap_interval(values: np.ndarray, *, seed: int, samples: int = 2_000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    indexes = rng.integers(0, values.size, size=(samples, values.size))
    means = np.mean(values[indexes], axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def _coverage_ratio(records: list[dict[str, Any]]) -> float:
    values = [record["randomization"] for record in records]
    covered = []
    for name, configured in _SIM2REAL_RANDOMIZATION.items():
        samples = [entry[name] for entry in values]
        if isinstance(configured, list):
            covered.append(len(set(samples)) > 1 and min(samples) >= configured[0] and max(samples) <= configured[1])
        else:
            covered.append(all(value == configured for value in samples))
    return float(np.mean(covered))


def _chapter_31(plot_path: Path, seed: int = 0) -> tuple[dict[str, float], dict[str, dict[str, float | str]], dict[str, Any]]:
    evaluation_seed = seed + 23
    bootstrap_seed = seed + 31
    baseline = _rollout_classic_controller(None, episodes=_EPISODE_COUNT, seed=evaluation_seed)
    randomized = _rollout_classic_controller(_SIM2REAL_RANDOMIZATION, episodes=_EPISODE_COUNT, seed=evaluation_seed)
    baseline_returns = np.asarray([record["return"] for record in baseline], dtype=float)
    randomized_returns = np.asarray([record["return"] for record in randomized], dtype=float)
    paired_gap = randomized_returns - baseline_returns
    ci_low, ci_high = _bootstrap_interval(paired_gap, seed=bootstrap_seed)
    baseline_success = float(np.mean([record["success"] for record in baseline]))
    randomized_success = float(np.mean([record["success"] for record in randomized]))
    metrics = {
        "baseline_return_mean": float(np.mean(baseline_returns)),
        "randomized_return_mean": float(np.mean(randomized_returns)),
        "sim2real_return_gap": float(np.mean(paired_gap)),
        "bootstrap_ci_low": ci_low,
        "bootstrap_ci_high": ci_high,
        "bootstrap_ci_width": float(ci_high - ci_low),
        "baseline_success_rate": baseline_success,
        "randomized_success_rate": randomized_success,
        "baseline_fall_rate": float(1.0 - baseline_success),
        "randomized_fall_rate": float(1.0 - randomized_success),
        "randomized_return_std": float(np.std(randomized_returns, ddof=1)),
        "configuration_coverage_ratio": _coverage_ratio(randomized),
        "evaluation_episode_count": float(_EPISODE_COUNT),
    }
    conditions = {
        "configuration_coverage_ratio": {"operator": "==", "value": 1.0},
        "evaluation_episode_count": {"operator": "==", "value": float(_EPISODE_COUNT)},
        "bootstrap_ci_width": {"operator": ">", "value": 1e-6},
        "randomized_return_std": {"operator": ">", "value": 1e-6},
    }
    figure, axes = plt.subplots(2, 2, figsize=(11.2, 7.0))
    episodes = np.arange(1, _EPISODE_COUNT + 1)
    axes[0, 0].plot(episodes, baseline_returns, marker="o", color="#2978b5", label="nominal simulation")
    axes[0, 0].plot(episodes, randomized_returns, marker="o", color="#d36b27", label="randomized simulation")
    axes[0, 0].set(xlabel="episode", ylabel="return", title="Matched-seed evaluation")
    axes[0, 0].legend()
    axes[0, 1].boxplot([baseline_returns, randomized_returns], tick_labels=["nominal", "randomized"])
    axes[0, 1].set(ylabel="return", title="Return distribution")
    masses = [record["randomization"]["mass_scale"] for record in randomized]
    frictions = [record["randomization"]["friction_scale"] for record in randomized]
    scatter = axes[1, 0].scatter(masses, frictions, c=randomized_returns, cmap="viridis", s=64)
    axes[1, 0].set(xlabel="mass scale", ylabel="friction scale", title="Sampled dynamics and return")
    figure.colorbar(scatter, ax=axes[1, 0], label="return")
    axes[1, 1].errorbar([0], [metrics["sim2real_return_gap"]], yerr=[[metrics["sim2real_return_gap"] - ci_low], [ci_high - metrics["sim2real_return_gap"]]], fmt="o", color="#17745a", capsize=8)
    axes[1, 1].axhline(0.0, color="#17201d", linestyle="--")
    axes[1, 1].set(xlim=(-1, 1), xticks=[], ylabel="randomized - nominal return", title="Fixed-seed bootstrap 95% CI")
    for axis in axes.flat:
        axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    failure_episodes = [record for record in randomized if record["terminated"]]
    return metrics, conditions, {
        "seed": seed,
        "policy": "WheelBalancerController (same controller in both distributions)",
        "nominal_randomization": None,
        "randomization_specification": _SIM2REAL_RANDOMIZATION,
        "baseline_episodes": baseline,
        "randomized_episodes": randomized,
        "randomized_failure_episodes": failure_episodes,
        "bootstrap": {"seed": bootstrap_seed, "resamples": 2000, "confidence": 0.95},
        "metrics": metrics,
    }


def _chapter_25(plot_path: Path, seed: int = 0) -> tuple[dict[str, float], dict[str, dict[str, float | str]], dict[str, Any]]:
    """25 关：Gymnasium 契约与形状 / 复现性 / step 时长测量。"""
    env = StandingEnv(max_episode_steps=32)
    try:
        obs_shape = env.observation_space.shape
        act_shape = env.action_space.shape
        obs_a, _ = env.reset(seed=seed)
        env.close()
        env2 = StandingEnv(max_episode_steps=32)
        obs_b, _ = env2.reset(seed=seed)
        reset_diff = float(np.max(np.abs(obs_a - obs_b)))
        step_times: list[float] = []
        import time as _time
        for _ in range(64):
            start = _time.perf_counter()
            env2.step(np.zeros(env2.action_space.shape))
            step_times.append((_time.perf_counter() - start) * 1_000.0)
    finally:
        try:
            env2.close()
        except Exception:
            pass
    step_mean = float(np.mean(step_times))
    step_max = float(np.max(step_times))
    metrics = {
        "observation_dim": float(obs_shape[0]),
        "action_dim": float(act_shape[0]),
        "reset_reproducibility_max_abs": reset_diff,
        "step_time_ms_mean": step_mean,
        "step_time_ms_max": step_max,
    }
    conditions = {
        "observation_dim": {"operator": ">=", "value": 10.0},
        "action_dim": {"operator": "==", "value": 6.0},
        "reset_reproducibility_max_abs": {"operator": "<=", "value": 1e-9},
        "step_time_ms_mean": {"operator": "<=", "value": 60.0},
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
    axes[0].bar(["obs", "act"], [obs_shape[0], act_shape[0]], color=["#2978b5", "#d36b27"])
    axes[0].set(ylabel="dim", title="Gymnasium contract shapes")
    axes[1].plot(step_times, color="#17745a")
    axes[1].set(xlabel="step", ylabel="time [ms]", title=f"step latency (mean={step_mean:.2f} ms)")
    for axis in axes:
        axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "observation_shape": list(obs_shape),
        "action_shape": list(act_shape),
        "step_times_ms": step_times,
        "metrics": metrics,
    }


def _chapter_26(plot_path: Path, seed: int = 0) -> tuple[dict[str, float], dict[str, dict[str, float | str]], dict[str, Any]]:
    """26 关：奖励分解 / 终止 / 截断统计。"""
    env = StandingEnv(max_episode_steps=200)
    rewards: list[float] = []
    term_breakdown: dict[str, list[float]] = {"upright": [], "height": [], "position": [], "effort": []}
    terminated_count = 0
    truncated_count = 0
    step_count = 0
    try:
        env.reset(seed=seed)
        for _ in range(200):
            _, reward, terminated, truncated, info = env.step(np.zeros(env.action_space.shape))
            rewards.append(float(reward))
            for key in term_breakdown:
                term_breakdown[key].append(float(info["reward_terms"].get(key, 0.0)))
            step_count += 1
            if terminated:
                terminated_count += 1
                env.reset(seed=seed + step_count)
            elif truncated:
                truncated_count += 1
                break
    finally:
        env.close()
    metrics = {
        "reward_mean": float(np.mean(rewards)),
        "reward_std": float(np.std(rewards)),
        "upright_mean": float(np.mean(term_breakdown["upright"])),
        "height_mean": float(np.mean(term_breakdown["height"])),
        "position_mean": float(np.mean(term_breakdown["position"])),
        "effort_mean": float(np.mean(term_breakdown["effort"])),
        "terminated_ratio": float(terminated_count / max(1, step_count)),
        "truncated_ratio": float(truncated_count / max(1, step_count)),
    }
    conditions = {
        "upright_mean": {"operator": ">=", "value": 0.0},
        "height_mean": {"operator": ">=", "value": 0.0},
        "reward_std": {"operator": ">=", "value": 1e-6},
    }
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))
    axes[0].plot(rewards, color="#17745a")
    axes[0].set(xlabel="step", ylabel="reward", title="Reward trajectory")
    names = list(term_breakdown.keys())
    values = [float(np.mean(term_breakdown[key])) for key in names]
    axes[1].bar(names, values, color=["#2978b5", "#8b5fbf", "#d36b27", "#17745a"])
    axes[1].set(ylabel="mean value", title="Reward decomposition")
    for axis in axes:
        axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "step_count": step_count,
        "terminated_count": terminated_count,
        "truncated_count": truncated_count,
        "metrics": metrics,
    }


def _chapter_28(plot_path: Path, seed: int = 0) -> tuple[dict[str, float], dict[str, dict[str, float | str]], dict[str, Any]]:
    """28 关：训练并重载真实 MuJoCo 轮矩 PPO。"""

    # 训练步数沿用提交基线的 50_000：该值在参考 profile 下能稳定收敛到
    # success_rate=1.0 / fall_rate=0.0；100_000 步会让 PPO 过训练发散成跌倒策略。
    training_timesteps = 50_000
    evaluation_episodes = 10
    training_seed = seed + 28
    evaluation_seed = seed + 280
    checkpoint_path = train_ppo_standing(
        total_timesteps=training_timesteps,
        seed=training_seed,
        profile="reference",
        output_dir=plot_path.parent.parent / "checkpoints",
        tensorboard_dir=plot_path.parent.parent / "tensorboard",
    )
    zero_records = evaluate_policy(
        episodes=evaluation_episodes,
        mode="zero",
        seed=evaluation_seed,
        return_records=True,
    )
    classic_records = evaluate_policy(
        episodes=evaluation_episodes,
        mode="classic",
        seed=evaluation_seed,
        return_records=True,
    )
    policy_records = evaluate_policy(
        checkpoint_path,
        episodes=evaluation_episodes,
        mode="rl",
        seed=evaluation_seed,
        return_records=True,
    )
    zero_returns = [float(record["return"]) for record in zero_records]
    classic_returns = [float(record["return"]) for record in classic_records]
    policy_returns = [float(record["return"]) for record in policy_records]
    policy_return_mean = float(np.mean(policy_returns))
    zero_return_mean = float(np.mean(zero_returns))
    metrics = {
        "training_timesteps": float(training_timesteps),
        "evaluation_episode_count": float(evaluation_episodes),
        "zero_return_mean": zero_return_mean,
        "classic_return_mean": float(np.mean(classic_returns)),
        "ppo_return_mean": policy_return_mean,
        "ppo_return_improvement_over_zero": policy_return_mean - zero_return_mean,
        "ppo_success_rate": float(np.mean([record["success"] for record in policy_records])),
        "ppo_fall_rate": float(np.mean([record["fell"] for record in policy_records])),
        "ppo_max_abs_pitch_rad": float(max(record["max_abs_pitch_rad"] for record in policy_records)),
        "checkpoint_reloaded": 1.0,
    }
    conditions = {
        "training_timesteps": {"operator": ">=", "value": 50_000.0},
        "evaluation_episode_count": {"operator": "==", "value": 10.0},
        "ppo_return_improvement_over_zero": {"operator": ">=", "value": 100.0},
        "ppo_success_rate": {"operator": "==", "value": 1.0},
        "ppo_fall_rate": {"operator": "==", "value": 0.0},
        "ppo_max_abs_pitch_rad": {"operator": "<=", "value": 0.35},
        "checkpoint_reloaded": {"operator": "==", "value": 1.0},
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    axes[0].plot(zero_returns, marker="o", label="zero", color="#aeb7b3")
    axes[0].plot(classic_returns, marker="o", label="classic", color="#2978b5")
    axes[0].plot(policy_returns, marker="o", label="PPO", color="#17745a")
    axes[0].set(xlabel="episode", ylabel="return", title="Reloaded policy evaluation")
    axes[0].legend()
    axes[1].bar(
        np.arange(evaluation_episodes),
        [float(record["max_abs_pitch_rad"]) for record in policy_records],
        color="#d36b27",
    )
    axes[1].axhline(0.35, color="#17201d", linestyle="--", label="acceptance limit")
    axes[1].set(xlabel="episode", ylabel="max |pitch error| [rad]", title="PPO safety envelope")
    axes[1].legend()
    for axis in axes:
        axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "backend": "mujoco",
        "training": {
            "algorithm": "PPO",
            "training_mode": "wheel_torque",
            "seed": training_seed,
            "total_timesteps": training_timesteps,
            "checkpoint_path": str(checkpoint_path),
        },
        "evaluation": {
            "seeds": list(range(evaluation_seed, evaluation_seed + evaluation_episodes)),
            "zero_records": zero_records,
            "classic_records": classic_records,
            "ppo_records": policy_records,
        },
        "metrics": metrics,
    }


def _chapter_29(plot_path: Path, seed: int = 0) -> tuple[dict[str, float], dict[str, dict[str, float | str]], dict[str, Any]]:
    """29 关：审计真实环境逐回合应用的随机化值。"""

    spec = dict(_CHAPTER_29_RUNTIME_RANDOMIZATION)

    def collect(seed: int) -> tuple[dict[str, list[dict[str, float | int]]], float]:
        env = StandingEnv(max_episode_steps=1, randomization=spec)
        reset_samples: list[dict[str, float | int]] = []
        step_samples: list[dict[str, float | int]] = []
        reset_step_error = 0.0
        try:
            for index in range(200):
                env.reset(seed=seed if index == 0 else None)
                reset_values = env._runtime_randomization()
                env.step(np.zeros(env.action_space.shape))
                step_values = env._runtime_randomization()
                reset_step_error = max(
                    reset_step_error,
                    max(abs(float(reset_values[name]) - float(step_values[name])) for name in spec),
                )
                reset_samples.append(dict(reset_values))
                step_samples.append(dict(step_values))
        finally:
            env.close()
        return {"reset": reset_samples, "step": step_samples}, reset_step_error

    runtime_samples, reset_step_error = collect(seed)
    replay_runtime_samples, repeated_reset_step_error = collect(seed)
    samples = runtime_samples["step"]
    repeated_samples = replay_runtime_samples["step"]
    seed_reproducibility_error = max(
        abs(float(first[name]) - float(second[name]))
        for first, second in zip(samples, repeated_samples)
        for name in spec
    )
    per_field: dict[str, dict[str, float]] = {}
    for field_name, bounds in spec.items():
        values = np.asarray([entry[field_name] for entry in samples], dtype=float)
        per_field[field_name] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "lower_bound": float(bounds[0]),
            "upper_bound": float(bounds[1]),
        }
    boundary_violation_count = sum(
        not (float(spec[name][0]) <= float(value) <= float(spec[name][1]))
        for phase_samples in runtime_samples.values()
        for sample in phase_samples
        for name, value in sample.items()
    )
    covered = sum(1 for stat in per_field.values() if stat["min"] >= stat["lower_bound"] - 1e-9 and stat["max"] <= stat["upper_bound"] + 1e-9)
    metrics = {
        "field_count": float(len(per_field)),
        "runtime_verified_field_count": float(len(per_field)),
        "runtime_sample_count": float(len(samples)),
        "boundary_violation_count": float(boundary_violation_count),
        "covered_field_count": float(covered),
        "coverage_ratio": float(covered / len(per_field)),
        "reset_step_consistency_max_abs": float(max(reset_step_error, repeated_reset_step_error)),
        "seed_reproducibility_max_abs": float(seed_reproducibility_error),
        "mean_range_utilization": float(np.mean([
            (stat["max"] - stat["min"]) / max(1e-12, stat["upper_bound"] - stat["lower_bound"]) for stat in per_field.values()
        ])),
    }
    conditions = {
        "runtime_verified_field_count": {"operator": "==", "value": 8.0},
        "runtime_sample_count": {"operator": "==", "value": 200.0},
        "boundary_violation_count": {"operator": "==", "value": 0.0},
        "coverage_ratio": {"operator": "==", "value": 1.0},
        "reset_step_consistency_max_abs": {"operator": "==", "value": 0.0},
        "seed_reproducibility_max_abs": {"operator": "==", "value": 0.0},
        "mean_range_utilization": {"operator": ">=", "value": 0.6},
    }
    field_names = list(per_field.keys())
    means = [per_field[name]["mean"] for name in field_names]
    stds = [per_field[name]["std"] for name in field_names]
    figure, axis = plt.subplots(figsize=(11.0, 4.2))
    axis.errorbar(range(len(field_names)), means, yerr=stds, fmt="o", color="#17745a", capsize=6)
    axis.set_xticks(range(len(field_names)))
    axis.set_xticklabels(field_names, rotation=25, ha="right")
    axis.set(ylabel="sampled value", title="Domain randomization field distribution")
    axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "audit_source": "mujoco_model_and_environment_state",
        "sample_count": len(samples),
        "randomization_specification": spec,
        "runtime_samples": runtime_samples,
        "seed_replay_runtime_samples": replay_runtime_samples,
        "per_field": per_field,
        "metrics": metrics,
    }


def _chapter_30(plot_path: Path, seed: int = 0) -> tuple[dict[str, float], dict[str, dict[str, float | str]], dict[str, Any]]:
    """30 关：短 PPO 残差训练与同随机种子的经典基线对照。"""
    training_seed = seed
    evaluation_seed = seed + 300
    evaluation_episodes = 10
    total_timesteps = 10_000
    residual_scale = 0.05
    evaluation_disturbance = {
        "push_force": [10.0, 10.0],
        "push_step": [50, 50],
        "push_duration_steps": [10, 10],
    }
    checkpoint_path = train_ppo_residual_standing(
        total_timesteps=total_timesteps,
        seed=training_seed,
        profile="smoke",
        residual_scale=residual_scale,
        output_dir=plot_path.parent.parent / "checkpoints",
        tensorboard_dir=plot_path.parent.parent / "tensorboard",
    )
    baseline_records = evaluate_policy(
        episodes=evaluation_episodes,
        mode="classic",
        seed=evaluation_seed,
        return_records=True,
        randomization=evaluation_disturbance,
    )
    residual_records = evaluate_policy(
        checkpoint_path,
        episodes=evaluation_episodes,
        mode="residual",
        residual_scale=residual_scale,
        seed=evaluation_seed,
        return_records=True,
        randomization=evaluation_disturbance,
    )
    baseline_returns = [float(record["return"]) for record in baseline_records]
    residual_returns = [float(record["return"]) for record in residual_records]
    paired_gap = np.asarray(residual_returns) - np.asarray(baseline_returns)
    baseline_success_rate = float(np.mean([record["success"] for record in baseline_records]))
    residual_success_rate = float(np.mean([record["success"] for record in residual_records]))
    baseline_fall_rate = float(np.mean([record["fell"] for record in baseline_records]))
    residual_fall_rate = float(np.mean([record["fell"] for record in residual_records]))
    residual_max_pitch = float(max(record["max_abs_pitch_rad"] for record in residual_records))
    residual_max_action = float(max(record["max_abs_residual_action"] for record in residual_records))
    metrics = {
        "baseline_return_mean": float(np.mean(baseline_returns)),
        "residual_return_mean": float(np.mean(residual_returns)),
        "residual_return_gap": float(np.mean(paired_gap)),
        "paired_improvement_rate": float(np.mean(paired_gap >= 0.0)),
        "training_timesteps": float(total_timesteps),
        "evaluation_episode_count": float(evaluation_episodes),
        "baseline_success_rate": baseline_success_rate,
        "residual_success_rate": residual_success_rate,
        "baseline_fall_rate": baseline_fall_rate,
        "residual_fall_rate": residual_fall_rate,
        "residual_max_abs_pitch_rad": residual_max_pitch,
        "residual_max_abs_action": residual_max_action,
    }
    conditions = {
        "training_timesteps": {"operator": ">=", "value": 10_000.0},
        "evaluation_episode_count": {"operator": "==", "value": float(evaluation_episodes)},
        "residual_return_gap": {"operator": ">=", "value": 0.0},
        "residual_success_rate": {"operator": ">=", "value": baseline_success_rate},
        "residual_fall_rate": {"operator": "<=", "value": baseline_fall_rate},
        "residual_max_abs_pitch_rad": {"operator": "<=", "value": 0.35},
        "residual_max_abs_action": {"operator": "<=", "value": 1.0},
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    axes[0].plot(baseline_returns, marker="o", label="WheelBalancer baseline", color="#2978b5")
    axes[0].plot(residual_returns, marker="o", label="Trained residual PPO", color="#d36b27")
    axes[0].set(xlabel="episode", ylabel="return", title="Residual vs baseline")
    axes[0].legend()
    axes[1].bar(
        np.arange(evaluation_episodes),
        paired_gap,
        color=np.where(paired_gap >= 0.0, "#17745a", "#d36b27"),
    )
    axes[1].axhline(0.0, color="#17201d", linestyle="--")
    axes[1].set(xlabel="paired episode", ylabel="residual - baseline", title="Matched-seed return gap")
    for axis in axes:
        axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": training_seed,
        "config": {
            "training_mode": "residual",
            "total_timesteps": total_timesteps,
            "residual_scale": residual_scale,
            "evaluation_seed": evaluation_seed,
            "evaluation_episodes": evaluation_episodes,
            "evaluation_disturbance": evaluation_disturbance,
        },
        "training": {
            "training_mode": "residual",
            "seed": training_seed,
            "total_timesteps": total_timesteps,
            "residual_scale": residual_scale,
            "checkpoint_path": str(checkpoint_path),
        },
        "evaluation": {
            "baseline_seeds": list(range(evaluation_seed, evaluation_seed + evaluation_episodes)),
            "paired_seeds": list(range(evaluation_seed, evaluation_seed + evaluation_episodes)),
            "baseline_returns": baseline_returns,
            "residual_returns": residual_returns,
            "paired_return_gaps": paired_gap.tolist(),
            "baseline_records": baseline_records,
            "residual_records": residual_records,
        },
        "metrics": metrics,
    }


_LABS = {
    "25": _chapter_25,
    "26": _chapter_26,
    "27": _chapter_27,
    "28": _chapter_28,
    "29": _chapter_29,
    "30": _chapter_30,
    "31": _chapter_31,
}


def run_rl_lab(
    chapter_id: str,
    *,
    output_root: str | Path = "outputs",
    source_root: str | Path | None = None,
    seed: int = 0,
) -> Path:
    """运行一项学习控制实验，写入结果契约、原始日志、图表与作品集证据。"""

    if chapter_id not in _LABS:
        raise ValueError(f"学习控制实验只支持 {RL_LAB_CHAPTERS}，收到 {chapter_id}")
    root = _resolve_output_root(output_root)
    plot_path = root / "plots" / f"rl_{chapter_id}.png"
    metrics, conditions, log = _LABS[chapter_id](plot_path, seed=seed)
    return finalize_lab_artifacts(
        output_root=output_root,
        prefix="rl",
        chapter_id=chapter_id,
        metrics=metrics,
        pass_conditions=conditions,
        log=log,
        plot_path=plot_path,
        config={
            "lab": f"rl_{chapter_id}",
            "experiment": log.get("model", log.get("randomization_specification", log.get("config", {}))),
        },
        source_root=source_root,
    )
