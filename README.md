# produce-voiceover-mg-social-video

一个面向 Codex 的可复用 Skill：把信息、概念、观点或产品流程制作成带用户授权原声、信息型 MG 动效、同步字幕、双平台封面和发布文案的小红书/抖音完整交付包。

## 能力范围

- 信息解释、概念说明和流程演示三种叙事模式；
- 用户原声或已授权音色 API；
- 确定性时间驱动的 MG 画面；
- 前三秒视觉钩子、产品首次识别与逐语义窗视觉导演；
- 官方素材、事实证据、解释型 MG 与生成情境的来源分层；
- 口播—画面双向覆盖审计；
- 字幕、音效、三种封面和双平台发布包；
- 技术、内容、视觉、音频与事实边界验收。

## 运行架构

整个项目由一个主智能体连续负责。脚本、渲染、ASR、抽帧和检测程序只做确定性执行，不把案例、语义窗或终审分派给其他智能体。长片会被拆成连续检查区间，但仍由同一负责人按顺序完成，并在最后做整片 `1×` 终审。

每个项目使用 `project-state.json` 保存阶段产物、哈希、批准状态和失效传播。修改口播会使旧音频及其下游失效；修改音频会使旧时码和旧渲染失效；修改成片会使旧终审结论失效。详细规则见 [references/orchestration-and-state.md](references/orchestration-and-state.md)。

纯录屏剪辑不属于这个 Skill 的主要范围，应使用录屏视频专项流程。

## 安装

把本仓库克隆到 Codex 的 Skills 目录，并确保文件夹名保持为 `produce-voiceover-mg-social-video`。入口文件是 [SKILL.md](SKILL.md)。

项目初始化：

```bash
python scripts/init_project.py <project-dir> --title "主题" --mode information
```

已有项目建立状态账本：

```bash
python scripts/project_state.py init <project-dir>
python scripts/project_state.py status <project-dir>
```

正式制作前先完成视觉导演与素材闸门：

```bash
python scripts/validate_visual_plan.py brief.md timeline.json --stage directing
python scripts/validate_visual_plan.py brief.md timeline.json --stage assets
```

产品类长片还必须先检查 0–8 秒样片和 0.0、0.8、1.6、2.4、3.0 秒五帧联系表，再进入整片渲染。

交付校验：

```bash
python scripts/validate_delivery.py <output-dir> --topic "主题" --full-decode
```

生成同一主智能体依次执行的逐锚点审查清单：

```bash
python scripts/build_anchor_audit_manifest.py timeline.json audit-manifest.json
```

## 可选 MossAPI 配置

密钥与音色配置优先从环境变量或系统密钥管理器读取，不写入仓库；用户在当前任务中明确直发并授权时也可作为一次性运行配置直接使用：

- `MOSS_API_KEY`
- `MOSS_VOICE_ID` 或 `MOSS_VOICE_NAME`

具体用法见 [references/moss-api.md](references/moss-api.md)。不要提交 `.env`、用户原始音频、成片或包含真实账号信息的项目文件。

## 维护与同步

更新后先运行：

```bash
python scripts/repo_check.py
python scripts/sync_github.py --message "说明本次修改"
```

同步脚本会检查仓库、提交修改、推送当前分支，并确认远端提交 SHA 与本地一致。它不会执行强制推送。
