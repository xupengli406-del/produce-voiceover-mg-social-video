# MossAPI 个人音色生成

只在用户已授权 Mossland/MossAPI 音色并需要直接生成旁白时读取。

## 默认链路

1. 从环境变量 `MOSS_API_KEY` 读取密钥；不得把密钥写入命令参数、Skill、项目、日志或聊天。在 Windows 上若当前 Codex 进程尚未继承新写入的用户级环境变量，配套脚本会只读查询当前用户的环境配置作为兼容路径。
2. 音色优先取 `MOSS_VOICE_ID`。没有 ID 时，用 `MOSS_VOICE_NAME` 或 `--voice-name` 调用 `GET /v1/audio/voices`，只在名称唯一匹配时继续。
3. 使用 `POST https://api.mosi.cn/v1/audio/speech`，请求体至少包含：
   - `model: moss-tts`
   - `input: 口播定稿`
   - `voice_id: 已确认的音色 ID`
   - `response_format: mp3` 或 `wav`
   - `delivery_method: audio`
4. 先生成一句短样本验证音色、计费和格式；同一已验证配置后续可直接生成完整稿。
5. 原始响应写到项目的原声输入区，不能覆盖用户素材。检查可解码、时长与内容后，才进入时码、字幕、响度和成片流程。

官方参考：

- 单人语音生成：https://platform.mosi.cn/docs/reference/speech/
- 查询音色列表：https://platform.mosi.cn/docs/reference/voices-list/
- 认证：https://platform.mosi.cn/docs/getting-started/auth/

## 口播输入

- 文本从 UTF-8 文件读取，避免长稿出现在命令历史。
- 可保留 Moss TTS 支持的 `[pause X.Ys]` 停顿标记；公开文档给出的范围为 0.1–10.0 秒。
- 网站界面还支持带声调数字的纯拼音与斜杠包裹的 IPA。只有确有发音问题时使用，不为普通句子堆控制标记。
- 接口没有公开承诺自动改写、分段或截断；长稿应先按语义整理，不能假设服务端会替创作者修稿。

## 安全与失败边界

- API Key 只在创建时完整展示，应由用户或受控凭证流程保存到环境/密钥管理器；不要截图、回显或记录长度以外的内容。
- 创建、轮换或删除 API Key 是独立的账号变更，遵循当前环境对凭证操作的确认要求；已授权音色使用不等于可以绕过凭证安全边界。
- 不从已登录网页抓取 Cookie、Local Storage、Authorization 请求头或隐藏令牌来替代 API Key。
- `401`、`403`、额度不足、音色不唯一、音色未就绪、返回 JSON 错误或音频不可解码时停止；保留口播和视觉工程，不把失败请求标为完成。
- 失败时可在用户已登录且网页仍可用的前提下使用浏览器界面降级，但下载后仍执行相同的原声母本、哈希、试听和技术验收。

## 可移植性

- `MOSS_API_BASE_URL` 可覆盖 API 根地址，默认 `https://api.mosi.cn`。
- 不写死用户名、盘符、操作系统、Python 路径、音色名称或 Voice ID。
- `scripts/moss_tts.py` 只使用 Python 标准库；缺少 Python 时使用当前环境等价的 HTTPS 客户端实现同一契约。
