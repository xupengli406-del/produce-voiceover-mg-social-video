# 视觉导演与素材来源

本文件用于防止“口播有钩子，画面却只是文字卡”“产品已经被念到，画面仍是通用 Agent”“为了丰富而塞图”等退化。先完成视觉导演，再找素材和做动效；素材形式必须服从当前语义窗要证明或解释的内容。

## 1. 两套钩子必须同题

口播钩子负责给观看理由，视觉钩子负责让这个理由在前三秒被看见。视觉钩子由三项组成：

- `attentionTarget`：第一眼应该看哪里；
- `visualBeat`：前三秒发生什么可见变化；
- `payoff`：变化结束后，观众立刻明白什么。

只有标题、字幕、通用圆点、装饰几何、无意义缩放或随机漂浮不算视觉钩子。产品类视频静音观看前三秒时，观众仍应能认出产品，并能大致说出开头提出的问题、反差或后果。

## 2. 产品首次出现合同

为口播中需要识别的产品建立 `entities`。产品名第一次被说出时，必须绑定 `product-recognition` 视觉事件：

- 官方 Logo、官方产品界面、官网公开原图或当期真实产品截图，在首次发声前不超过 0.20 秒或发声后不超过 0.35 秒变得可识别；
- 识别状态保持至少 0.80 秒；
- 产品名、识别事件和身份素材使用同一实体 ID 关联；
- 通用 Agent 图形、字幕、生成 Logo、仿真 UI 或不带品牌识别的电脑轮廓不能代替产品身份；
- 官方 Logo 叠加在生成情境图上时，Logo 必须是独立的确定性图层，不交给生图模型重画。

推荐结构：

```json
{
  "entities": [{
    "id": "workbuddy",
    "type": "product",
    "spokenNames": ["WorkBuddy"],
    "firstMentionAnchorId": "S01-A01",
    "recognitionEventId": "S01-E01",
    "identityAssetId": "asset-workbuddy-ui"
  }]
}
```

## 3. 每个语义窗先写导演方案

保留声画合同，并为每窗新增：

```json
{
  "directorPlan": {
    "attentionTarget": "观众第一眼看到的对象",
    "visualBeat": "随发声锚点发生的主动作或揭示",
    "payoff": "动作完成后观众获得的信息",
    "treatment": "official-capture+mg",
    "treatmentReason": "为什么这种呈现最适合当前主张"
  },
  "assetRefs": ["asset-id"],
  "visualEvents": []
}
```

`directorPlan` 必须描述画面，不得把口播换一种说法再抄一遍。有效方案要回答：

1. 第一视觉主体是哪个对象，而不是哪句字；
2. 对象从什么状态开始；
3. 在哪个发声锚点发生拖入、点击、读取、变形、筛选、确认、失败、换路或结果揭示；
4. 窗口结束时留下哪个完整可读状态；
5. 为什么使用真实截图、MG、生成情境或混合呈现。

纯 MG 可以通过，但必须解释对象关系、动作或状态变化。只把完整口播放进卡片、按顺序出现文字或重复四格模板不通过。

## 4. 素材来源与用途

统一 `assets` 最少记录：`id`、`kind`、`role`、`sourceScope`、`path`、`sourceUri`、`capturedAt`、`sha256`、`claimIds`、`synthetic`、`disclosure`。

允许值：

- `kind`：`official-original`、`official-capture`、`live-capture`、`creator-owned`、`generated`、`licensed-third-party`；
- `role`：`identity`、`evidence`、`explanation`、`atmosphere`；
- `sourceScope`：`official-public`、`live-product`、`creator-owned`、`generated`、`third-party`；
- `treatment`：`official-original`、`official-capture`、`live-capture`、`mg`、`generated`、`mixed`，也可用加号说明混合形式。

硬边界：

- `identity` 只能来自 `official-original`、`official-capture`、`live-capture`；
- `evidence` 只能来自上述三种或可核验的 `creator-owned`；
- `generated` 只能承担 `explanation` 或 `atmosphere`；
- 生成图不得伪装成真实产品截图、官方 Logo、真实执行结果或真实数据；可能被误认时改成明显抽象 MG，或持续标注“示意”；
- 官方截图必须记录来源页、取得时间、本地文件和哈希；
- 证据素材至少绑定一个 `claimId`，并且只证明画面中实际可见的对象、动作或结果；
- 一张图不能因为“来自官网”就越界证明它没有展示的功能、接入步骤或最终结果。

## 5. 从语义窗倒推素材

每窗按以下顺序决策：

1. 先写 `attentionTarget → visualBeat → payoff`；
2. 若主张是产品身份、按钮、字段、执行状态或真实结果，优先取得官方资源或真实截图；
3. 若主张是对象关系、不可见机制、选择条件或跨步骤因果，用确定性 MG；
4. 若需要情绪、生活场景或空间代入，可生成非品牌情境图；
5. 若仍缺素材，标记缺口并阻止正式渲染，不能退化成无关图片或伪界面。

同一语义窗可按“情境钩子 → 品牌/产品定位 → 动作解释 → 真实证据 → 结果停留”组织；不要求每窗塞满五层，但至少有一个清楚对象、一个有意义动作和一个结果状态。

## 6. 截图与多图布局

- 截图按“全局定位 → 操作区域 → 动作发生 → 结果验证”推进；
- 只在口播要求核对按钮、字段或结果时局部放大；
- 两张文字型截图默认上下全宽或按发声锚点先后占据主画面，禁止左右塞进两个窄小窗；
- 三张以上按锚点逐张接力，不做四宫格联系表式陈列；
- 每个截图镜头都要能回答“这一步发生了什么”，不能只作为背景；
- 真实证据的可读内容必须在手机尺寸仍能辨认；看不清时应分镜、裁切或重绘关系，不是继续缩小。

## 7. 转场完整状态

语义窗切换不能把两个完整页面交叉叠化。交叉叠化会同时出现两套标题、两张截图和两个结果，形成错页闪帧或半透明脏帧。

- 新窗第一帧已经有可识别主对象时，使用干净切换并让窗内动作继续；
- 新对象尚未就绪时，保持上一完整状态，等新对象可识别后再移除旧状态；
- 可以做共享对象形变、遮罩推入、镜头跟随或形状匹配，但不能闪白、闪黑、淡到空白或露出半成品；
- 在每个语义窗的起点前后各抽查至少三帧，确认没有错页、旧标题残影和素材加载空帧。

## 8. 两阶段闸门

素材制作前：

```bash
python scripts/validate_visual_plan.py brief.md timeline.json --stage directing
```

检查 Brief 的视觉钩子、每窗导演方案、首次产品识别需求和前三秒信息型变化。

正式渲染前：

```bash
python scripts/validate_visual_plan.py brief.md timeline.json --stage assets
```

检查素材引用、来源、文件、哈希、生成素材用途边界和产品识别时间。

## 9. 开头样片闸门

整片渲染前先输出 0–8 秒样片和 0.0、0.8、1.6、2.4、3.0 秒五帧联系表，逐项回答：

1. 静音能否认出产品；
2. 静音能否说出开头提出的问题、反差或后果；
3. 闭眼只听，口播钩子是否成立；
4. 声画一起看，产品名、动作和回报是否落在对应发声锚点；
5. 官方界面、事实证据、MG 解释和生成情境是否能被清楚区分。

任何一项失败，先修开头，不进入长片批量渲染。
