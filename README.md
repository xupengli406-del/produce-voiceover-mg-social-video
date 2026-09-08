# produce-voiceover-mg-social-video

一个面向 Codex 的可复用 Skill：把信息、概念、观点或产品流程制作成带用户授权原声、信息型 MG 动效、同步字幕、双平台封面和发布文案的小红书/抖音完整交付包。

## 能力范围

- 信息解释、概念说明和流程演示三种叙事模式；
- 用户原声或已授权音色 API；
- Remotion 帧驱动的 MG 画面、真实测字、目标自适应标注和避障箭头；
- 前三秒视觉钩子、产品首次识别与逐语义窗视觉导演；
- 官方素材、事实证据、解释型 MG 与生成情境的来源分层；
- 口播—画面双向覆盖审计；
- 字幕、音效、三种封面和双平台发布包；
- 技术、内容、视觉、音频与事实边界验收。

## 运行架构

整个项目由一个主智能体连续负责。脚本、渲染、ASR、抽帧和检测程序只做确定性执行，不把案例、语义窗或终审分派给其他智能体。长片会被拆成连续检查区间，但仍由同一负责人按顺序完成，并在最后做整片 `1×` 终审。

每个项目使用 `project-state.json` 保存阶段产物、哈希、批准状态和失效传播。修改口播会使旧音频及其下游失效；修改音频会使旧时码和旧渲染失效；修改成片会使旧终审结论失效。详细规则见 [references/orchestration-and-state.md](references/orchestration-and-state.md)。

纯录屏剪辑不属于这个 Skill 的主要范围，应使用录屏视频专项流程。

## 从视频来到这里，先拿齐三套

| Skill | 负责什么 |
| --- | --- |
| **本仓库：主 MG Skill** | 整理需求、口播、声音、字幕、语义动作、检查及发布包 |
| [封面 Skill](https://github.com/xupengli406-del/produce-social-media-cover) | 同片视觉或美漫高冲击两种方向，按画幅独立构图 |
| [节奏增强 Skill](https://github.com/xupengli406-del/enhance-voiceover-video-rhythm) | 哪个词值得强调、选什么动作、何时停稳以及动效密度 |

这是一套给 AI 智能体使用的制作要求、模板和脚本。AI 按内容编写、调用和调整工程；不是双击就能工作的独立剪辑软件，也不保证每次一次生成即可发布。

视频里说的“自动剪辑”主要包含口播停顿与节奏处理、字幕及动作对齐、场景编排和合成。纯录屏素材的智能选段剪辑、自动数字人对口型不在本 Skill 的主要范围。

## 安装与第一次使用

分别下载或克隆这三个仓库，保留各自完整文件夹，不要只复制 `SKILL.md`。把它们放入所用 AI 工具配置的 Skills 目录；本仓库文件夹名保持为 `produce-voiceover-mg-social-video`。入口文件是 [SKILL.md](SKILL.md)。[官方 Skills 说明](https://learn.chatgpt.com/docs/build-skills)介绍 Skill 的组织与使用方式；其他工具按各自安装说明配置。

在 Codex 中，也可以让内置 `$skill-installer` 从上表的 GitHub 仓库安装完整 Skill。安装后检查三套名称是否可见；没有出现时重新启动工具。具体目录以当前工具配置为准。

第一次可以直接对 AI 说：

> 使用 produce-voiceover-mg-social-video、produce-social-media-cover 和 enhance-voiceover-video-rhythm。我要给【观众】讲【主题】，希望他们记住【核心观点】。资料在【资料位置】，使用【我提供的声音／已授权音色】。封面选【同片视觉／美漫高冲击】。先让我审完整口播，再做一段包含声画同步和重点标注的 45–60 秒样片，确认后扩展全片，保留字幕、封面、发布文案和可编辑工程。

请使用自己的主题、资料、声音与人物照片；仓库不包含原作者的人像、声音或个人音色配置。固定口头禅可以换成自己的，也可以省略。

### 运行需要什么

| 项目 | 用途与边界 |
| --- | --- |
| 能读写文件和运行命令的 AI 工具 | 读取 Skill、组织内容、编写和调整工程 |
| Python 3.10+、Node.js、pnpm、FFmpeg/ffprobe、兼容 Chromium | 项目与检查脚本、画面渲染、音视频合成；仓库持续检查使用 Python 3.12 和 Node.js 24 |
| 可用且获授权的中文字体 | 渲染前明确选择并重新测字；模板不分发系统字体 |
| 自己的录音，或授权 TTS 服务 | 现有 MossAPI 辅助脚本可选；使用自己的录音不需要 TTS 配置 |
| 语音识别或 forced alignment 工具 | 从真实声音取得时间锚点；本仓库不附识别模型与服务 |
| 图片生成／处理能力 | 生成情境插图和封面主视觉；使用者须准备必要参考与服务权限 |

生成声音、图片及使用 AI 工具可能产生费用，取决于你的配置。渲染依赖遵循各自许可，尤其请核对 [Remotion 的当前许可](https://www.remotion.dev/license)。本仓库的许可不替代这些工具或你输入素材的授权。

实际生成后还需创作者审稿、核对事实并完整看听；下面的技术检查不能证明画面吸引力、声音自然程度或所有题材的一次成功率。

## 视频能力对应到哪里

| 你在视频里看到的能力 | 可检查的实现与要求 |
| --- | --- |
| 从主题、受众与资料形成口播 | [叙事规范](references/story-and-motion.md)、[口播验收](references/voiceover-script-acceptance.md)、Brief 模板 |
| 自录声音／授权合成 | [音频处理](references/audio-and-timing.md)、[MossAPI](references/moss-api.md)与 `scripts/moss_tts.py` |
| 说到哪个词，字幕和动作跟到哪里 | [语义时间轴](references/semantic-timeline-and-sync.md)、`scripts/prepare_remotion.py` 与全局帧时钟 |
| 素材进入、字段组合、节点连线和结果 | [场景示例](assets/remotion-template/src/scenes.jsx)；按本期语义继续扩展，不机械套页 |
| 圈选随文字大小改变、箭头避让 | [几何实现](assets/remotion-template/src/contracts.mjs)、[组件](assets/remotion-template/src/components.jsx)；先提供真实目标边界，再检查实际帧 |
| 配音改了，旧时码不能接着用 | `scripts/project_state.py` 使下游失效；重新对齐后再准备、渲染和验收，不是替换音频就自动修好 |
| 两种封面风格、三比例重构 | 由上面的封面 Skill 实现；每个比例独立验收 |
| 重点强调与稳定停留 | 用户调用节奏增强 Skill 时，由同一制作流程接入处理图 |
| 字幕、稿子、发布材料和工程 | [交付规范](references/delivery-and-qa.md)、`scripts/validate_delivery.py` |

## 工程与检查命令

项目初始化：

```bash
python scripts/init_project.py <project-dir> --title "主题" --mode information
```

新建工程默认使用 Remotion；已有 Canvas 工程保留兼容，不自动迁移。安装锁定依赖、添加场景动作数据、实际渲染和负例测试，见 [Remotion 制作层](references/remotion-production.md)。新增组件测试不替代原有口播、事实、音频、导演、封面及完整听审标准。

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

## 一起改进

觉得有用可以 Star 收藏支持。有使用问题或想法请提 Issue；已做出具体修改可以提交 PR，审核后再合并。

提交问题时写清运行环境、输入类型、实际结果与期待结果；示例使用合成数据或有权公开的材料。不要附密钥、私人声音、人像或未授权客户素材。修改代码后运行上面的检查，并说明实际验证范围。

## 开源许可

本仓库原创的说明、脚本和模板使用 [MIT License](LICENSE)。允许修改、再分发和商用，保留版权与许可声明。第三方工具、字体、图片、声音及运行服务遵循各自的许可与授权条件。
