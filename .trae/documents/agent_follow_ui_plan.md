# Agent 板块前端深度优化规划：跟随式教学体验

## 一、需求拆解（第一性原理）

本项目中用户的主要姿态是**跟随 Agent 输出、注视中央 3D 画布**，Agent 面板承担"导航 + 字幕"角色，而非传统聊天App的阅读主角。据此推导出四条设计原则：

1. **视线引导**：画布即将变化前先预告；变化中明确"正在动什么、该看哪里、马上做什么"。
2. **节奏可控**：动画/停留期间可暂停、快进、跳过，用户不等 Agent、Agent 也不刷屏。
3. **低认知负荷**：推理链流式化、单行化、自动折叠；同类工具调用聚合为数字，而不是大方框堆叠。
4. **回答可读**：AI 的 Markdown 回答用一套成熟、统一、适配窄面板的富文本排版呈现。

## 二、现状勘察结论

### 现有结构
- 面板 DOM：[shell.html](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/shell.html#L26) 中 `#agent-panel` 包含 `#chat-messages`、`#tool-approval`、`#chat-form`。
- 轮次渲染：[agent.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js#L465-L520) 的 `beginTurn / paintThink / addToolCard / finishTool / finishTurn`；历史恢复走 `renderViewEntry`（[agent.js#L257-L274](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js#L257-L274)）。
- 工具执行：`runTurn` 中顺序执行工具（[agent.js#L654-L683](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js#L654-L683)）；动画工具返回 `wait_seconds`，agent 用 `sleep()` **阻塞等待**（[agent.js#L674-L677](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js#L674-L677)）；视角停留用 `viewHoldUntil` 时间戳 + `respectHold()`（[agent.js#L424-L429](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js#L424-L429)）。
- 时间轴：[timeline.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/timeline.js) 已有 `pause()/resume()/stop()`、公开 `elapsed/total/playing`；实例经 `app.timeline` 暴露（[app.js#L453-L454](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/app.js#L453-L454)）。**无速率（快进）能力，无进度回调**。
- 工具元数据：中文名/图标已在 [agent-tools.json](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent-tools.json) 单一事实源；`approval()` 已有"id→中文名"摘要逻辑（[agent.js#L525](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js#L525)）。
- Markdown：[markdown.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/markdown.js) 为自研安全渲染器（无 HTML 直通），已支持表格、GitHub 风格提示块、代码块、任务列表、数学符号；样式作用域 `.md-body`（[style.css 第23行](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/style.css#L23)）。
- 构建：[build.py#L66-L67](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/tools/build.py#L66-L67) 按 marker 内嵌 web/*.js；新增模块须同时在 `shell.html` 加 `<script>` 标签、build.py marker 列表加一行，占位符替换由 test_build 回归校验。
- 画布上已有空壳元素 `#motion-badge`（[shell.html#L18](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/shell.html#L18)），仅手动关节模式使用，Agent 动画期间不显示。

### 现有问题（与需求逐条对应）
1. **无跟随组件**：Agent 动画布时只有工具卡 flag 文字（"动画播放 5s"）和 9px 的 `#chat-state`；用户不知道该看画布，也无法暂停/快进/跳过。sleep 阻塞期间唯一干预手段是"停止整轮"。
2. **推理链重**：每张工具卡是带边框/图标的大卡片，执行中强制 `open=true` 展开参数与输出；思考流执行时整块展开（最高 240px 滚动区）；N 次同类调用 = N 张大卡。
3. **信息不自动折叠**：思考过程、工具参数、工具输出默认全部可见。
4. **富文本有基础但不成体系**：标题/列表/表格/提示块样式零散，窄面板（300–366px）节奏未精修。

### 约束
- 原生 JS、无框架、无 CDN/npm 运行时依赖、单文件离线可用（NFR-2）。
- 不并引第二个 Markdown 解析器（自研解析器是单一事实源，遵守"同类能力只引一个库"原则）；组件以自建轻量 DOM 模块实现，不引入框架。
- `view` 历史存档 schema 尽量不变；现有队列测试依赖选择器 `.agent-turn.user.queued / .queued-cancel / #chat-stop[data-queue] / .agent-turn.error`（[agent_queue_test.py](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/tests/agent_queue_test.py#L74-L110)），保持兼容。
- 动画总时长/停留上限、停止即中断、配对消毒等既有安全语义不回归。

## 三、设计方案

### 模块 1：跟随状态条 FollowStrip（新增核心）

**位置与形态**
- 主组件：`#agent-panel` 内、消息区底部/输入区上方的 **sticky 玻璃质感细条**（沿用项目 iOS glassmorphism 语言：`backdrop-filter` + `--panel` 半透明 + `--shadow`，与 `.floating-widget`/`.bottom-dock` 一致）。
- 画布镜像：升级现有 `#motion-badge` 为极简一行提示（图标+动作名，如"相机移动中 · 请看模型"），Agent 动作期间显示；不含按钮，避免遮挡画布。
- 无动作时整条 `hidden`，不占空间、不产生视觉噪音。

**状态机（phase）**
| phase | 时机 | 展示 |
|---|---|---|
| `announce` | 写工具批准后、执行前 | "即将：高亮 舟骨、月骨 · 请看画布中央"（动作预告） |
| `running` | focus/isolate/highlight/set_view/set_explode/set_layer 执行中 | 图标+动作名+对象摘要+流动指示 |
| `playing` | play_assembly / play_joint_motion / camera_tour | 动作名 + 线性进度条 + 已用/总秒数 |
| `holding` | hold_seconds 停留中 | "观察中" + 倒计时进度 |
| `asking` | 等待工具授权 | 动作摘要 +「允许一次 / 拒绝」按钮（复用同一 `pendingApproval` Promise，不新增绕过路径） |
| `done/error/denied` | 工具收尾 | 1.2s 轻提示后自动消失（错误/拒绝用 --red/--gold 色） |

**交互控件**（playing/holding 时出现）
- ⏸ **暂停/继续**：动画期调用已有 `timeline.pause()/resume()`；停留期暂停倒计时。
- ⏩ **快进**：动画 1×→2×→4× 循环（timeline 新增 `setRate`）；停留快进 = 立即结束本次等待。
- ⏭ **跳过**：`app.stopAnimation()` + 结束等待，Agent 直接进入下一步讲解（不中断整轮对话）。
- 控件在 `prefers-reduced-motion` 下只保留"跳过"（动画本身已降级为终态）。

**数据来源（rAF 轮询，无需改引擎回调）**
- 进度直接读 `app.timeline.{playing,elapsed,total}`（字段已公开）。
- 动作中文名/图标取 `TOOL[name].zh/ico`；参数摘要新增 `summarizeArgs(name,args)`（ids→`FormaKnowledge.title(app.object(id))`，抽自 approval 现有逻辑共用）。

### 模块 2：等待句柄化（agent.js + timeline.js）

当前 `sleep(ms, signal)` 只支持 abort。升级为**可等待句柄**：

- agent 维护当前等待 `this._wait = {kind:'anim'|'hold', total, start, pausedAt, rate}`，方法 `pauseWait()/resumeWait()/skipWait()`。
- 停留机制：`respectHold()` 改为注册/消费句柄（内部仍由 `viewHoldUntil/animUntil` 计算剩余时间，暂停时平移截止时间戳）。
- 动画：`runTurn` 中 `await this.sleep(w*1000, signal)` 换为 `await this.waitForAnimation(w)`，句柄与 `app.timeline` 的 pause/resume/setRate/stop 联动；timeline `oncancel`（用户跳过）正常 resolve，不报错。
- 既有 `_aborted`（手动停止/排队撤销）路径行为保持不变。

**timeline.js 新增（小改动，确定性语义不变）**
- `setRate(rate)`：内部累计时钟按速率推进（`this._rate`，tick 中 `elapsed` 按速率增量计算）；终态仍严格走 `renderAt(total)`，回放结果与 1× 完全一致。
- 其余 pause/resume/stop/renderAt 不动。

### 模块 3：推理链轻量流式化（agent.js + style.css）

**单轮新结构**（替换现有 `reason-shell` 大方框内容，类名尽量沿用以保护归档/测试）：
1. **活动流一行**（常驻）：spinner + 实时短状态（"请求中… / 思考中… / 高亮结构"）；轮次结束折叠为"已推理 · N 步 · x 秒"，点击展开归档（沿用 `<details>` 外壳）。
2. **思考 chip**：执行中只渲染**最新两行**（CSS line-clamp 两行，展示尾部新内容，不出现大滚动框）；点击展开全文；轮次结束自动整体折叠。
3. **工具单行 chip**：小图标(14px) + 工具中文名 + 状态点/短 flag（执行中/完成/未授权）；参数与输出收入点击展开的详情行，**默认折叠**；正在执行的那一次其 flag 状态实时变化。
4. **同类工具聚合**：同一轮内同名工具合并为一个 chip，右侧 `×N` 计数；N 增加时数字做 odometer 滚动动画（CSS keyframe + `transform: translateY`，reduced-motion 时禁用）。聚合 chip 展开后按次序列出每一次的参数与结果。
   - 存档 `view.tools` 仍逐条保存（信息不丢），**聚合只在渲染层**：`addToolCard/finishTool` 改为操作聚合组，`renderViewEntry` 历史恢复同样分组聚合。
5. 竖向时间线 rail 保留但弱化为细线；每个工具单元高度从约 60–90px 压缩到约 24px。

### 模块 4：成熟 Markdown 富文本排版（style.css 为主）

以 `.md-body` 为唯一作用域，定义一套排版（浅/深主题双适配，300–366px 窄面板优先）：
- 标题层级节奏（h2/h3 轻量竖条修饰，复用项目水墨设计语言但更克制）、段落间距、正文行高。
- 列表：标记着色、任务列表对齐；引用块与提示块（NOTE/TIP/WARNING/IMPORTANT/CAUTION）五态配色 + 左侧语义色条。
- 表格：圆角外框（已有）+ 表头粘性/斑马纹/横向滚动优化；代码块头部栏与复制按钮保留精修；行内 code、mark 高亮、数学块、hr 统一间距。
- 流式态（`.is-stream`）与终态共用同一套样式，避免生成中/完成后跳动。
- markdown.js 仅做**最小**安全增强（如表格对齐符号 `:--:` 支持），不重写、不引库。

### 模块 5：动作联动接线（agent.js 内聚）

- 在 `runTurn` 工具循环中抽出生命周期钩子：`onAnnounce / onStart / onProgress / onEnd / onAsking`，统一调用 `app.follow.*`（新模块挂到 app 上）。
- 覆盖用户列举的全部场景：模型翻转（set_view/camera_tour）、模型变化（play_assembly/set_explode/set_layer/isolate/focus）、选中/高亮（focus/highlight/set_highlight）均进入 announce→running/playing→holding→done 时序。
- 纯只读工具（search/get_scene/list_taxonomy/get_lesson/get_structure_info）**不弹 FollowStrip**（画布不动，用户无需转移视线），仅在活动流一行中体现。
- 授权等待态：strip 上的「允许一次 / 拒绝」与现有 `#tool-approval` 卡片共用同一个 `pendingApproval` resolve，两处操作等价、状态同步，不产生新的授权绕过。

## 四、文件改动清单

| 文件 | 改动 |
|---|---|
| `web/follow.js`（新增） | `FormaFollow` 模块：FollowStrip 与画布镜像 badge 的 DOM、状态机、rAF 倒计时/进度、暂停/快进/跳过/授权按钮事件、odometer 数字动画工具 |
| `web/timeline.js`（编辑） | 新增 `setRate(rate)`；约 10 行，时钟累计逻辑 |
| `web/agent.js`（编辑，主战场） | 等待句柄化；工具生命周期事件接入 FollowStrip；`summarizeArgs` 抽取；beginTurn/paintThink/addToolCard/finishTool/finishTurn/renderViewEntry 改为活动流+两行思考+聚合 chip；view 存档 schema 不变 |
| `web/style.css`（编辑） | 追加独立分段：FollowStrip、画布 badge 镜像、tool-chip/计数动画、think 两行折叠；升级 `.md-body` 富文本体系；覆盖旧大卡样式（不改写历史压缩行，新增段落覆盖） |
| `web/shell.html`（编辑） | agent-panel 内增加空容器节点 `#follow-strip`；注册 `<script>/*FOLLOW*/</script>`（位于 AGENT_CONFIG 之后、TIMELINE 之前） |
| `tools/build.py`（编辑） | marker 列表增加 `('/*FOLLOW*/','follow.js')` 一行 |
| `tests/` | 现有 agent_queue_test 选择器保持兼容；新增跟随条夹具用例（见验收） |
| `dist/forma_anatomy_studio.html` | 构建重建，不手改 |

## 五、可访问性与兼容

- FollowStrip：`role="status"` `aria-live="polite"`；动画进度数字 `aria-hidden`，状态文案给屏幕阅读器；所有控件带 `aria-label`。
- `prefers-reduced-motion`：不做数字滚动/进度动效，动画直接终态，strip 只短暂提示"已呈现结果"。
- 移动端（≤700px breakpoint）：strip 收紧为单行、按钮图标化；富文本表格横向滚动已有处理。
- 历史对话恢复、队列/停止行为、限额钳制、单文件导出全部不回归。

## 六、风险与处理

1. **setRate 破坏时间轴确定性** —— 只改交互播放的时钟速率，终态仍 `renderAt(total)`；夹具断言快进/跳过后画布终态与正常播放在 sticky 段上一致。若实现中发现速率改动复杂，退路为只提供"跳到结尾"（renderAt(total)+finish），不提供 2×。
2. **等待句柄化影响 runTurn 控制流** —— 保持 `_aborted/signal` 原路径，仅新增 pause/skip 分支；agent_queue_test 18 断言全绿才算完。
3. **聚合后看不到单次参数** —— 聚合组可展开，每次调用的参数/输出完整保留；当前正在执行的一次状态外显。
4. **授权安全性被削弱** —— strip 按钮与审批卡片共用同一个 Promise resolve，无任何自动放行路径；smart/allow/ask 三模式判定逻辑不动。
5. **构建占位符遗漏** —— follow.js 的注册必须 shell.html 与 build.py 同时改，test_build 会立即暴露未替换 marker。

## 七、实施顺序

1. `timeline.js`：setRate + 自检。
2. 新增 `follow.js`；shell.html/build.py 注册；最小挂接验证 strip 能显示/隐藏。
3. `agent.js`：等待句柄化 + 工具生命周期事件 + 授权联动。
4. `agent.js + style.css`：推理链活动流 / 两行思考 / 工具 chip 聚合（含历史恢复）。
5. `style.css (+markdown.js 微调)`：富文本排版体系。
6. 测试与构建：更新/新增夹具、`python tools/build.py` 重建 dist。

## 八、验收标准

**功能（浏览器夹具，合成几何，不含解剖素材）**
- 模拟一次含"搜索→高亮→相机编排→组装动画→停留"的轮次：strip 依次出现 announce/running/playing/holding；playing 显示进度且与 `timeline.elapsed/total` 同步。
- 播放中点暂停：时间轴与倒计时都停；继续后走完；点快进：速率切到 2×/4×；点跳过：动画与等待立即结束，Agent 继续输出下一段，对话不中断、不报错。
- 等待授权态：strip 与审批卡片同步出现；任一处允许/拒绝结果一致；拒绝后不重复请求。
- 连续 3 次 `search_structures`：仅 1 个聚合 chip，计数 1→2→3 且有数字滚动；展开可见 3 次参数/结果；切换历史对话再切回，聚合表现一致。
- 思考流式期间仅占两行高度；轮次结束后思考与工具详情默认全部折叠，可逐条展开。

**回归**
- `python tests/test_build.py`（含新 marker 替换、14 项既有断言）通过。
- `python tests/agent_queue_test.py`（18 断言：排队、撤销、停止清队列）通过。
- `python tests/server_http_test.py`、`node --test agent-server/protocol.test.mjs` 不回归。
- dist 单文件离线打开：无外部资源、浅/深主题与 ≤700px 窄屏下 FollowStrip、聚合 chip、富文本排版均可用。

## 九、待确认的默认决策（审批时可否决）

1. FollowStrip 放在 Agent 面板内（sticky），同时在画布左下保留极简镜像提示 —— 默认两处都做。
2. 快进提供 2×/4×/跳过三档 —— 若担心复杂度可砍掉速率只留跳过。
3. 思考预览流式时显示**最新两行**（尾部），而非最前两行。
4. 新建独立 `web/follow.js`（agent.js 已 700 行，遵循单文件职责/≤500 行约定），需在 shell.html 与 build.py 各注册一处。
