#!/usr/bin/env python3
"""在飞书文档中插入 Mermaid 图表的脚本。

使用方法：
python scripts/add_charts_to_feishu.py
"""

import subprocess

# 文档 token 和对应的图表
DOCS_WITH_CHARTS = {
    "CHjtdvjMZozPG1xBSlac8LY1nMb": {
        "name": "00_getting_started",
        "chart_name": "学习路线图",
        "mermaid": """graph TD
    subgraph 基础层["🔧 基础层（Lesson 00-02）"]
        A1[环境搭建 & 工具链]
        A2[MuJoCo 仿真引擎]
        A3[机器人模型理解]
    end

    subgraph 控制层["🎮 控制层（Lesson 03-04）"]
        B1[PD 控制<br/>经典反馈控制]
        B2[LQR 控制<br/>最优控制]
        B3[控制接口设计]
    end

    subgraph 学习层["🧠 学习层（Lesson 05-06）"]
        C1[Gymnasium 环境封装]
        C2[PPO 强化学习]
        C3[奖励函数设计]
    end

    subgraph 工程层["⚙️ 工程层（Lesson 07-10）"]
        D1[鲁棒性与域随机化]
        D2[残差 RL<br/>经典+学习融合]
        D3[模型替换]
        D4[高层指令接口]
    end

    基础层 --> 控制层 --> 学习层 --> 工程层

    style 基础层 fill:#e3f2fd,stroke:#1976d2
    style 控制层 fill:#e8f5e9,stroke:#388e3c
    style 学习层 fill:#fff3e0,stroke:#f57c00
    style 工程层 fill:#fce4ec,stroke:#c62828"""
    },
    "Jbd1dWzbDosYQWxPHp1cC6rInog": {
        "name": "01_robot_model_audit",
        "chart_name": "模型结构示意",
        "mermaid": """graph TD
    world["🌍 world<br/>(固定基座)"]
    base["📦 base<br/>(自由浮动基座)"]

    subgraph 左腿["左腿"]
        left_hip["🦴 left_hip<br/>(铰链关节)"]
        left_knee["🦴 left_knee<br/>(铰链关节)"]
        left_wheel["🎡 left_wheel<br/>(铰链关节)"]
    end

    subgraph 右腿["右腿"]
        right_hip["🦴 right_hip<br/>(铰链关节)"]
        right_knee["🦴 right_knee<br/>(铰链关节)"]
        right_wheel["🎡 right_wheel<br/>(铰链关节)"]
    end

    world --> base
    base --> left_hip --> left_knee --> left_wheel
    base --> right_hip --> right_knee --> right_wheel

    style world fill:#e3f2fd,stroke:#1976d2
    style base fill:#e8f5e9,stroke:#388e3c
    style 左腿 fill:#fff3e0,stroke:#f57c00
    style 右腿 fill:#fce4ec,stroke:#c62828"""
    },
    "TeTfdLC9RoGia0xjavPcGxuYnyf": {
        "name": "03_classical_control",
        "chart_name": "轮式倒立摆模型",
        "mermaid": """graph TD
    subgraph 轮式倒立摆模型
        A["📦 躯干<br/>质量 m，长度 l"]
        B["⚙️ 车轮<br/>半径 r"]
        A -->|"θ (偏角)"| B
    end

    style A fill:#e3f2fd,stroke:#1976d2
    style B fill:#e8f5e9,stroke:#388e3c"""
    },
    "QtNPd6hcroswDTxFtfTcziRLnXb": {
        "name": "05_gymnasium_env",
        "chart_name": "Gymnasium 交互流程",
        "mermaid": """sequenceDiagram
    participant Agent as 🤖 Agent
    participant Env as 🌍 Environment

    Agent->>Env: reset()
    Env-->>Agent: observation, info

    loop 交互循环
        Agent->>Env: step(action)
        Env-->>Agent: observation, reward, terminated, truncated, info

        alt terminated or truncated
            Agent->>Env: reset()
            Env-->>Agent: observation, info
        end
    end

    Agent->>Env: close()"""
    },
    "Cf1GdAjtuoWayKxDLuOcJ8Mpn0g": {
        "name": "06_reinforcement_learning",
        "chart_name": "PPO 算法流程",
        "mermaid": """graph TD
    A["初始化策略 π_θ 和价值函数 V_φ"]
    B["用当前策略采集轨迹<br/>{(s_t, a_t, r_t, s_{t+1})}"]
    C["计算优势估计 A_t<br/>（使用 GAE）"]
    D{"epoch = 1, ..., K"}
    E["计算裁剪目标 L^CLIP(θ)"]
    F["更新策略<br/>θ ← θ + α ∇_θ L^CLIP(θ)"]
    G["更新价值函数<br/>φ ← φ - α ∇_φ (V_φ - V_target)²"]
    H{"收敛？"}

    A --> B --> C --> D
    D --> E --> F --> D
    D --> G --> H
    H -->|否| B
    H -->|是| I["输出最优策略 π*"]

    style A fill:#e3f2fd,stroke:#1976d2
    style B fill:#e8f5e9,stroke:#388e3c
    style C fill:#e8f5e9,stroke:#388e3c
    style D fill:#fff3e0,stroke:#f57c00
    style E fill:#fff3e0,stroke:#f57c00
    style F fill:#fff3e0,stroke:#f57c00
    style G fill:#fce4ec,stroke:#c62828
    style H fill:#f3e5f5,stroke:#7b1fa2
    style I fill:#e8f5e9,stroke:#388e3c"""
    },
    "HFPyd0wj0ouWs6xY1hccRXtynbL": {
        "name": "09_model_swap",
        "chart_name": "模型替换流程",
        "mermaid": """graph LR
    A["📁 准备模型文件<br/>MJCF/URDF"] --> B["📝 创建配置文件<br/>JSON"]
    B --> C["🔍 运行模型审计<br/>验证正确性"]
    C --> D["✅ 验证模型加载<br/>运行测试"]

    style A fill:#e3f2fd,stroke:#1976d2
    style B fill:#e8f5e9,stroke:#388e3c
    style C fill:#fff3e0,stroke:#f57c00
    style D fill:#e8f5e9,stroke:#388e3c"""
    },
    "SsZNdBiYiojA7JxtjxZceLsJn6b": {
        "name": "10_high_level_commands",
        "chart_name": "三层控制架构",
        "mermaid": """graph TD
    A["🎤 高层指令（High-Level）<br/>\\"go forward\\" / \\"turn left\\" / \\"stop\\""]
    B["📋 中层规划（Mid-Level）<br/>mode, velocity, yaw_rate, height"]
    C["⚡ 底层控制（Low-Level）<br/>PD / LQR / RL / Residual"]
    D["🤖 MuJoCo 仿真"]

    A -->|"解析意图"| B
    B -->|"控制参数"| C
    C -->|"关节力矩"| D

    style A fill:#e3f2fd,stroke:#1976d2
    style B fill:#e8f5e9,stroke:#388e3c
    style C fill:#fff3e0,stroke:#f57c00
    style D fill:#fce4ec,stroke:#c62828"""
    }
}

def run_lark_cli(args):
    """运行 lark-cli 命令。"""
    cmd = ["C:\\Users\\YHX\\AppData\\Roaming\\npm\\lark-cli.cmd"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def insert_mermaid_chart(doc_token, mermaid_code, chart_name):
    """在文档中插入 Mermaid 图表。"""
    # 构建 XML 内容
    content = f'<whiteboard type="mermaid">\n{mermaid_code}\n</whiteboard>'

    stdout, stderr, code = run_lark_cli([
        "docs", "+update", "--api-version", "v2",
        "--doc", doc_token,
        "--command", "append",
        "--content", content,
        "--as", "user"
    ])

    if code != 0:
        print(f"插入图表失败: {stderr}")
        return False

    print(f"插入图表成功: {chart_name}")
    return True

def main():
    """主函数。"""
    print("开始在飞书文档中插入 Mermaid 图表...")

    success_count = 0
    total_count = len(DOCS_WITH_CHARTS)

    for doc_token, info in DOCS_WITH_CHARTS.items():
        print(f"\n处理文档: {info['name']}")
        print(f"图表: {info['chart_name']}")

        if insert_mermaid_chart(doc_token, info["mermaid"], info["chart_name"]):
            success_count += 1

    print(f"\n完成！成功插入 {success_count}/{total_count} 个图表")

if __name__ == "__main__":
    main()
