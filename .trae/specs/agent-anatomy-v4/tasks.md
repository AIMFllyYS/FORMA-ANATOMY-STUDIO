# Forma v4：Agent 教学能力升级与系统解剖 3D 资产/命名体系重建 — 实施计划

> 工作分支：`feat/agent-anatomy-v4`（基于 `dev`）。每个任务完成后按 Conventional Commits 提交（`feat:/fix:/chore:/docs:/test:` 前缀）。产物二进制（GLB/BLEND）、node_modules、dist 不入库。合成图形测试必须带 `SYNTHETIC_GRAPHICS_NOT_ANATOMY` 标记。

## Task 1: 工具定义单一事实源重构
- **Status**: completed
- **Completion Evidence**:
  - TR-1.1（rule）通过：新增 `agent-server/tools-sync.test.mjs`，`node --test` 8/8 通过，断言共享清单与 ALLOWED_NAMES 完全一致、schema 完整、读写分组正确、旧 tool-definitions.json 已删除。
  - TR-1.2（rule）通过：`python tools/build.py` 构建成功（552,911 字节），占位符 `/*AGENT_TOOLS*/` 零残留；12 项 test_build.py 全过。
  - 变更：新增 web/agent-tools.json 与 #agent-tools-data 插槽；agent.js 改为内嵌 JSON 加载；server.mjs 改读同一文件；删除 agent-server/tool-definitions.json；提交 8721847 之后的 refactor commit。
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 新建 `web/agent-tools.json`：包含全部现有 10 个工具的 name、description、parameters（JSON Schema）、mutatesCanvas、zh、icon；作为浏览器与服务端唯一事实源。
  - [tools/build.py](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/tools/build.py) 增加内嵌占位（如 `/*AGENT_TOOLS*/`）；[shell.html](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/shell.html) 增加 JSON script 插槽；[agent.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js) 从内嵌 JSON 读取定义（开发环境回退 fetch 同文件）。
  - [server.mjs](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/agent-server/server.mjs) 改读 `../web/agent-tools.json`，删除 agent-server 内重复定义文件（tool-definitions.json 由共享文件取代，README 同步）。
  - 新增 node 测试：断言两端工具集同名、同 schema、同读写标记，且所有 schema 满足 `additionalProperties:false` 等基本约束。
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `rule` TR-1.1：`node --test` 中存在并通过"共享工具清单结构有效、server 与浏览器读取同一文件、ALLOWED_NAMES 与清单一致"用例；证据：测试命令输出。
  - `rule` TR-1.2：`python tools/build.py` 成功，构建 HTML 中工具描述只出现一份来源文本（grep 计数）；证据：构建输出与断言脚本。
- **Notes**: 新工具在 Task 20 增量进入该清单；本任务只搬迁、不改行为。

## Task 2: Agent 行为限额配置模型与循环强制
- **Status**: completed
- **Completion Evidence**:
  - TR-2.1（rule）通过：新增纯模块 web/agent-config.js（无 DOM 依赖，可注入 storage）与 agent-server/agent-config.test.mjs（6 用例：默认值/钳制/权限归一/v3 迁移/v4 优先/save+forget/consent），`node --test` 14/14。
  - TR-2.2（rule）通过：tests/browser_test.py 新增并通过 agent_max_turns_enforced（2 轮硬停＋"2 轮工具调用上限"提示）、agent_max_tool_calls_per_turn_enforced（超单轮上限整轮拒绝、无审批弹窗）、agent_config_migrates_v3；_verify_agent.py ALL PASSED；server_http_test.py 9/9。
  - 限额：maxTurns 1–20 默认 8、maxToolCallsPerTurn 1–12 默认 6、maxHoldSeconds 0–60 默认 12（工具 schema 硬边界放宽至 60，行为受用户值钳制）、requestTimeoutSeconds 30–300 默认 120、animationBudgetSeconds 0–180 默认 60；存储键升级 forma-agent-config-v4 并自动迁移 v3。
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 在 [agent.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js) 定义 v4 配置：`maxTurns`（1–20，默认 8）、`maxToolCallsPerTurn`（1–12，默认 6）、`maxHoldSeconds`（0–60，默认 12）、`requestTimeoutMs`（30–300s，默认 120）、`animationBudgetSeconds`（0–180，默认 60）、`permissionMode`（沿用 smart/allow/ask）。
  - localStorage 键升级 `forma-agent-config-v4`，读取时迁移 v3（url/key/model/consent/permissionMode），缺省补默认；越界值钳制并记录。
  - 用配置值替换硬编码：8 轮循环、单轮 6 调用、12s hold clamp、120s 超时；超限提示文案动态显示实际配置。
  - 纯函数导出（clamp/normalize/migrate）便于 node 或夹具测试。
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `rule` TR-2.1：迁移/钳制纯函数对"缺字段、越界、v3 旧数据"三组输入输出正确；证据：node 测试或浏览器夹具断言。
  - `rule` TR-2.2：循环在配置为 2 轮时第 2 轮后必然停止并出现上限提示；单轮工具数超配置时整轮拒绝且不执行写工具；证据：浏览器夹具测试（模拟兼容服务）。

## Task 3: 设置中心与"助教设计"快捷条
- **Status**: completed
- **Completion Evidence**:
  - TR-3.1（rule）通过：_verify_agent.py 新增 settings_tabs（5 分页）/limits_panel/5 limit rows/即改即存/输出同步/恢复默认/design 弹层三项/权限双端共享；browser_test 全套 exit 0（about:blank 存储拒绝时自动跳过持久化断言，file:// 由 _verify_agent_persist.py ALL PASSED 覆盖 v4 持久化）。
  - TR-3.2（rubric）自评 4/5：settings_center.png、design_popover.png 走查——玻璃分页条、限额卡片滑块、权限分段与现有设计系统一致，窄屏有媒体查询；锚定阈值 ≥4。
  - 入口：Agent 齿轮/Agent 面板"设置"/顶栏"更多→设置中心"均打开分页弹窗；作曲家栏新增 sliders 按钮打开"助教行为设计"弹层；暴露 app.popover 供 Agent 调用。
- **Priority**: high
- **Depends On**: Task 2
- **Description**:
  - 新增"设置中心"弹窗（顶栏"更多"菜单与 Agent 面板齿轮均可进入），分页：助教连接（沿用 URL/Key/Model/同意）、行为限额（Task 2 全部字段，滑块+数值+恢复默认）、模型源（Task 11 接线前先占位）、显示（主题/权限默认）、关于与许可（链接来源弹窗）。
  - Agent 输入区工具条旁新增"助教设计"按钮 → popover 显示轮次/单轮工具/停留/权限四项高频控件，即改即存，与设置中心双向同步。
  - 沿用现有水墨/玻璃设计语言与 modal 组件；移动端可用；所有插入文本经 esc。
  - 移除原独立齿轮弹窗的重复表单（齿轮改开设置中心）。
- **Acceptance Criteria Addressed**: AC-1, AC-11
- **Test Requirements**:
  - `rule` TR-3.1：两处入口修改同一配置并持久化；刷新后值保留；证据：浏览器夹具测试 + 截图（桌面/移动）。
  - `rubric` TR-3.2：视觉一致性；1–5；1＝风格割裂不可用，3＝功能可用但粗糙，5＝与现有设计系统完全统一；阈值 ≥4；证据：浅/深/窄屏走查截图。

## Task 4: 浏览器侧统一工具参数校验器
- **Status**: completed
- **Completion Evidence**:
  - TR-4.1（rule）通过：browser_test schema_validation_all_tools 对 10 个工具各 1 非法 1 合法用例（未知字段/错类型/缺必填/越界/枚举非法/数组空）全部识别；schema_invalid_blocks_execution 全链路断言：非法 focus_structures 不弹审批、卡片 is-error、错误回送后模型自纠一轮即止。
  - TR-4.2（rule）通过：_verify_agent ALL PASSED、browser_test exit 0（含既有多步工具 agent_multistep_tools），合法参数行为不回归；hold_seconds 在执行前即钳制为用户上限。
  - 实现：agent.js validateSchema/validateArgs（type/enum/range/length/items/required/additionalProperties），位于审批与 executeTool 之前；导出供测试。
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - 在 [agent.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/agent.js) 实现按 JSON Schema 的最小校验器（type/integer/number/boolean/string/array、enum、minimum/maximum、minItems/maxItems、minLength/maxLength、required、additionalProperties:false、items），覆盖共享清单中全部约束。
  - 工具执行路径改为：先 schema 校验，再进审批/执行；校验失败输出结构化错误（不改变画布）并回送模型；移除/收编执行器内分散校验。
  - hold_seconds 上限改读配置；动画类工具预留的时长参数同样被钳制（Task 20 启用）。
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `rule` TR-4.1：对每个现有工具至少一条非法参数用例（越界/错类型/未知字段/缺必填），断言不触达 executeTool 且返回错误 JSON；证据：浏览器夹具测试。
  - `rule` TR-4.2：合法参数用例全部通过且行为与重构前一致（回归）；证据：tests/_verify_agent.py 系列通过。

## Task 5: agent-server 协议加固与依赖锁定
- **Status**: in_progress
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - [protocol.mjs](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/agent-server/protocol.mjs)：`toModelMessages` 丢弃入站 `system` 角色消息（系统指令只信 server instructions），并在转换时用共享 JSON Schema 校验每条入站 tool_call 的 arguments（引入 Ajv，编译缓存）；非法即抛错。
  - 单轮 tool_calls 数量上限改由清单/常量集中管理；保持 tool_call_id 配对与 MAX_MESSAGES。
  - `package.json` 依赖改为 ai 6.x / @ai-sdk/openai-compatible 2.x 当前精确版本（安装时取 ai-v6 通道最新），新增 `ajv`；执行 `npm install` 生成并提交 package-lock.json。
  - 更新 protocol.test.mjs：system 剥离、非法参数拒绝、白名单拒绝；跑通 `npm test` 与 `npm run check`。
  - server.mjs 的 ALLOWED_NAMES 从共享清单派生；README 更新"新增工具只改一处"。
- **Acceptance Criteria Addressed**: AC-3, AC-2
- **Test Requirements**:
  - `rule` TR-5.1：新增三条拒绝用例（system 被剥离、非法 tool 参数 400/抛错、未知工具名拒绝）全部通过；证据：node --test 输出。
  - `rule` TR-5.2：`package-lock.json` 入库且 `npm ci` 可离线复现安装；`npm run check` 通过；证据：命令输出与 git diff。
  - `rule` TR-5.3：鉴权失败/错误 Origin/2MB 体限/健康检查既有行为不回归；证据：server_http_test.py 通过。

## Task 6: 七系统 GLB 节点语料提取与覆盖率基线
- **Status**: pending
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 新增 `tools/extract_node_corpus.py`（仅标准库解析 GLB chunk）：输入七套 GLB 路径或自动下载（BASE/MIRROR），输出 `tools/data/node_corpus.json`（系统、节点名、mesh/primitive 数）与可读统计；按 Z-Anatomy 约定标记 `.j/.g/撇号` 特殊对象与 `.l/.r` 侧别。
  - 产物（不含 GLB 二进制）入库，作为命名覆盖率统计基线。
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `rule` TR-6.1：脚本对七套 GLB 成功运行，节点总数与各系统计数输出且非空；证据：命令输出与 node_corpus.json。
  - `rule` TR-6.2：语料中可见肌肉完整 TA 名样例（如 `External abdominal oblique muscle.l`）与内脏名；侧别解析正确率抽样 100%；证据：报告中的样例与断言。

## Task 7: 规范命名数据生成管线
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 6
- **Description**:
  - 新增 `tools/build_nomenclature.py`：输入 node_corpus、Z-Anatomy TA2.csv（脚本可下载，缓存入 `tools/data/cache/`）、Wikidata SPARQL 缓存（按英文名/FMA/TA id 取拉丁名、中文标签、TA98/TA2、FMA id；CC0）、UBERON 可选层级、以及人工覆表层。
  - 输出 `web/nomenclature.json`：records（稳定 id、zh、en、la、side、system、region、group、subgroup、method、status、source refs）；输出覆盖率报告 `tools/data/nomenclature_coverage.md/json`（按系统 × 映射方法 × 审校状态）。
  - 匹配规则：多词 TA 全名归一（去 side/`muscle` 后缀变体、亚部、序号椎骨/肋骨/指骨规则）、词干同义词表；方法标注 exact-ta2 / wd-match / rule / manual / none；所有自动结果默认 pending，人工覆表为 reviewed。
  - 可重复运行（网络数据走缓存），不抓取名词委批量数据。
- **Acceptance Criteria Addressed**: AC-4, FR-8, FR-13
- **Test Requirements**:
  - `rule` TR-7.1：管线无网络可复跑（缓存命中），输出 JSON 结构有效且 id 唯一；证据：命令输出。
  - `rule` TR-7.2：肌肉 + 内脏节点 auto 及以上中文名覆盖率统计可产出；证据：覆盖率报告文件（本任务只建能力，不要求达到 90%）。

## Task 8: 中文规范名人工覆表与亚群归类（≥90% 覆盖）
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 7
- **Description**:
  - 建立 `tools/data/nomenclature_review_zh.csv`（或等价结构化文件）：对语料中实际肌肉/内脏/脉管/神经节点逐条给中文规范名（教材常用名，人卫《系统解剖学》体系）、拉丁名、功能群/亚群归类；有把握标 reviewed，存疑标 pending 并备注。
  - 肌肉分类至少覆盖 FR-11 所列全部肌群；内脏按九大系统归组；上肢细分（上肢带肌/臂前后群/前臂前后群/手肌内外在）为必达样板。
  - 重跑管线使肌肉+内脏覆盖率 ≥90%，未命中保留源名。
- **Acceptance Criteria Addressed**: AC-4, AC-5, AC-10
- **Test Requirements**:
  - `rule` TR-8.1：覆盖率报告显示肌肉、内脏两系统中文命名 ≥90%，每条带来源/方法；证据：nomenclature_coverage 报告。
  - `rubric` TR-8.2：抽样 30 肌 + 20 脏器中文名与亚群归属，对照教材；1–5；1＝多处错名，3＝常用名对但亚群有含糊，5＝名称与归类均准确；阈值 ≥4；证据：抽样核对表（含核对人/日期/依据）。

## Task 9: 命名层运行时接线与结构树分层
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 8
- **Description**:
  - [knowledge.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/knowledge.js)：names() 优先走 nomenclature 记录（zh/en/la/side/status），知识卡改以稳定 id 关联（保留现有 cardFor 回退路径，不误挂、不丢 465 张卡）；region/family/group/subgroup 由命名层提供。
  - [app.js](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/web/app.js) 结构树/目录渲染改为"系统→区域→功能群→亚群→结构"；悬浮、标签、讲解头部、Agent 输出统一显示中文名 + 拉丁/英文 + 可信度徽标（已审校/待审/未映射）；搜索索引纳入拉丁名与拼音。
  - shell.html 占位、build.py 内嵌 nomenclature.json；pinyin 运行时兼容新中文名。
- **Acceptance Criteria Addressed**: AC-5, AC-10, FR-10, FR-12
- **Test Requirements**:
  - `rule` TR-9.1：加载合成夹具时树中出现"前臂肌/前群"等关键分组标签且组内对象非空；未映射对象显示源名与未映射徽标；证据：浏览器夹具断言与截图。
  - `rule` TR-9.2：拉丁名搜索、中文搜索、拼音搜索均可命中标称对象；证据：夹具用例。
  - `rubric` TR-9.3：命名可信度区分清晰度；1–5；阈值 ≥4；证据：UI 走查截图。

## Task 10: 命名与构建回归测试
- **Status**: pending
- **Priority**: medium
- **Depends On**: Task 9
- **Description**:
  - 将 90% 覆盖率门槛写入测试脚本（低于门槛失败）；test_build.py 增加 nomenclature/agent-tools 内嵌断言；浏览器 fixture 增加分类分组与徽标断言；更新 _verify_names.py。
- **Acceptance Criteria Addressed**: AC-5, AC-13
- **Test Requirements**:
  - `rule` TR-10.1：覆盖率门槛、内嵌断言、分组夹具三项测试通过；证据：python 与浏览器测试输出。

## Task 11: 模型来源注册表与 gzip/档位加载
- **Status**: pending
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 新增 `web/model-sources.json`：来源（上游 standard、本地/自托管 balanced/HD 模板）×系统文件 URL、质量说明、三角面预算、许可/署名 id；core.js `AssetManager.load(category,{source,tier})` 据此解析 URL；已缓存资产按 SHA 天然隔离，缓存记录 category/source/tier。
  - fetch 层支持 gzip：HTTP `Content-Encoding` 透传（浏览器默认）+ 本地/Object URL `.glb.gz` 用 DecompressionStream 解压；导入器识别 .gz 扩展。
  - 模型资源弹窗：来源与档位选择（standard/balanced/HD），显示各档面数/许可/是否可用（未生成的档位给出"查看自托管说明"）；与设置中心模型源分页接线。
- **Acceptance Criteria Addressed**: AC-7, FR-14, FR-17
- **Test Requirements**:
  - `rule` TR-11.1：注册表驱动加载，切换档位请求不同 URL；缓存不串档；证据：本地静态服务器手测 + 夹具（mock fetch）断言。
  - `rule` TR-11.2：`.glb.gz` 本地导入经解压后被现有 GLB 读取器成功解析；证据：合成 GLB gzip 往返夹具。

## Task 12: Blender 七系统多档高模导出
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 11
- **Description**:
  - 安装 Blender（Windows 官方包，版本记录）；下载 Z-Anatomy 模板（Z-Anatomy.zip/Startup.blend）与 TA2.csv 留存 `models/source/`（gitignore 覆盖二进制）。
  - 升级 [tools/export_blender.py](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/tools/export_blender.py)：补齐 muscles 之外的 organs/vessels/lymph（含曲线转网格）、按档位三角面预算（HD 肌/血管/神经 ≥ 现用 2×，见 AC-6）、过滤 `.j/.g/撇号` 特殊对象、节点 extras 写 anatomyId（TA/FMA/稳定 slug）、输出每档 manifest（对象、节点名、面数、字节数、SHA-256、许可链）。
  - 经 [tools/build.py](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/tools/build.py) 现有 `--blender/--blend/--systems` 串起；文档给出一键命令；产物写 `models/hd/`、`models/balanced/`（不入库），manifest 入 `models/manifests/`。
- **Acceptance Criteria Addressed**: AC-6, FR-15, FR-18
- **Test Requirements**:
  - `rule` TR-12.1：单一命令完成七系统两档导出；manifest 中肌肉/心血管/神经 HD 面数 ≥ 现用档 2×（现用值取 node_corpus/上游 manifest 对照）；证据：manifest diff 与统计。
  - `rule` TR-12.2：所有导出 GLB 被自研 MeshReader 成功解析，节点名与 anatomyId 可读，无 Draco/蒙皮/变形目标扩展；证据：解析校验脚本输出。

## Task 13: 高模真机验证与性能定档
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 12, Task 9
- **Description**:
  - 用本地静态服务器承载 models/ 目录，浏览器真实加载 balanced 全套与 HD 各系统：记录加载时长、JS 堆/显存、交互帧率（旋转/拾取）、拾取正确性、命名显示。
  - 不达标档位回调 Blender 预算重导出；最终在资源界面只把实测达档位标为可用；产出性能报告（硬件/浏览器版本留档）。
- **Acceptance Criteria Addressed**: AC-12, AC-7, FR-16
- **Test Requirements**:
  - `rubric` TR-13.1：balanced 全套交互帧率；1–5；锚点 1/3/5 按 spec AC-12；阈值 ≥4（否则降档并在 UI/文档标注）；证据：性能采样报告。
  - `rule` TR-13.2：HD 每系统可加载、可拾取、名称为规范名；SHA 与 manifest 一致；证据：手测记录 + 自动断言。

## Task 14: 许可署名与来源文档合规
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 12
- **Description**:
  - 更新 [licenses/SOURCE_NOTICES.md](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/licenses/SOURCE_NOTICES.md)、core.js ATTRIBUTION、应用内来源弹窗：BodyParts3D（现渠道 CC BY 4.0 说明 + 旧 BY-SA 2.1 JP 历史链）、Z-Anatomy CC BY-SA 4.0、改编版本义务、AnatomyTOOL/SPL 等未使用源不混入；记录"教育用途/未完整审校/仅成年男性/内耳肾第三方 NC 限制"提示。
  - models/README.md 写清两档产物来源、自托管（GitHub release/静态服务器）做法与 CORS。
- **Acceptance Criteria Addressed**: AC-14, NFR-5
- **Test Requirements**:
  - `rule` TR-14.1：来源弹窗对每个已启用来源显示名称、许可、改动说明、链接；文档与注册表一致；证据：UI 截图 + 文档 diff 评审。

## Task 15: 时间轴播放器内核
- **Status**: pending
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 在 app 层新增 timeline 模块（可置于新 `web/timeline.js`，build 与 shell 加挂）：基于 rAF 的时钟、片段（delay/duration/easing/loop）、可插值通道：相机（target/yaw/pitch/span）、explode、per-object 组装偏移、单刚体运动矩阵（与现有 r.motion 兼容）、高亮态集合；提供 play/pause/stop/onfinish、中断（新写操作/停止按钮/场景切换即取消）、prefers-reduced-motion 直接到终态。
  - 总时长受 `animationBudgetSeconds` 钳制；时间轴状态进入 snapshot/undo 与场景返回清理。
- **Acceptance Criteria Addressed**: AC-8, FR-19, FR-20
- **Test Requirements**:
  - `rule` TR-15.1：合成几何夹具验证：串行/重叠片段时序、停止后状态、预算钳制、reduced-motion 终态；证据：浏览器自动化测试。
  - `rule` TR-15.2：动画期间执行其他写工具会先取消时间轴且不留残差；证据：夹具断言。

## Task 16: 组装、多态高亮与相机编排原语
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 15
- **Description**:
  - 组装：结构组序列从 explode 偏移按每步时长/缓动归位（可反向），伴随相机推近与组焦点高亮；偏移纯显示变换，源顶点不动。
  - 多态高亮：渲染器支持 normal/accent/series/contraction 至少四态（颜色/描边策略，沿用教学材质），可在时间轴中切换；拾取不受影响。
  - 相机编排：iso/六面视图切换可定时化、绕选中结构环转（角度/时长）、多视点停留；解剖方位名仅在用户做过朝向校准后可用（未校准时维持"源坐标"措辞，朝向校准数据见 Task 18）。
  - 关节学习面板升级：播放条（播放/暂停/停止/循环）、每步时长与角度区间控件；保留手动两点设轴为"高级模式"。
- **Acceptance Criteria Addressed**: AC-8, AC-11, FR-21, FR-23, FR-24, FR-25
- **Test Requirements**:
  - `rule` TR-16.1：组装播放结束后对象变换回到装配位（explode=0、无残差矩阵），逆向播放可复现；证据：夹具。
  - `rule` TR-16.2：四态高亮在浅深主题下均可见且不改变拾取 id；证据：夹具 + 截图。
  - `rubric` TR-16.3：课程播放观感；1–5；阈值 ≥4；证据：腕关节手工播放录像走查。

## Task 17: 教学近似轴求解器与关节运动时间轴
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 15, Task 18
- **Description**:
  - 依据课程锚点规则（如腕屈伸：过头状骨/月骨区的内外侧方向近似轴；桡尺偏：前后方向近似轴）从真实已加载对象的包围盒中心/极值点求两点轴；锚点对象缺失或几何异常时失败并给中文提示，不静默换轴。
  - 运动时间轴：移动骨组 + 跨关节肌群按刚性成组在角度区间内随时间往复（支持起止角、时长、循环、保持）；肌群"收缩态"用 contraction 高亮表达；UI/工具结果常驻"教学近似、非生理活动度/生物力学认证"标注。
- **Acceptance Criteria Addressed**: AC-8, FR-22, FR-25
- **Test Requirements**:
  - `rule` TR-17.1：合成几何下锚点规则求出的轴方向与预期容差一致；缺锚点对象必然失败返回；证据：夹具断言。
  - `rule` TR-17.2：播放中被勾选移动对象共享同一时间轴矩阵，未勾选对象不动；结束可复位；证据：夹具。

## Task 18: 动画教学数据（课程 schema 与腕关节样板）
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 9
- **Description**:
  - 以版本化数据（扩展 knowledge.js JOINTS 或新建 `web/curriculum.json`，构建内嵌）定义：组装顺序（稳定 id 组序列）、组成（沿用现有 parts 机制并接命名层 id）、运动列表（运动术语、锚点规则、教学角度区间、移动组、主动/拮抗肌群 id）、六面观察建议。
  - 腕关节为完整样板（桡尺远端 → 舟月三角豆 → 大小头状钩 → 掌骨 → 关节盘/韧带 → 跨腕屈/伸/尺桡偏肌群；屈伸、桡偏/尺偏两条运动）；其余七关节迁移到新 schema，缺字段显式标记未提供。
  - 朝向校准：提供一次源轴→解剖方位的声明式校准（按模型来源默认值 + 用户可翻转），校准前 set_view 类描述禁用解剖方位词。
- **Acceptance Criteria Addressed**: AC-9, AC-10, FR-29
- **Test Requirements**:
  - `rule` TR-18.1：腕课程所有引用 id 在命名层存在且分属骨/关节/肌；schema 校验脚本通过；证据：数据校验脚本输出。
  - `rubric` TR-18.2：腕课程文字（组成/运动/肌群）与教材一致性；1–5；阈值 ≥4；证据：人工核对表。

## Task 19: Agent 新增教学工具与提示词
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 1, Task 4, Task 16, Task 17, Task 18
- **Description**:
  - 在共享清单新增并实现执行器：只读 `list_taxonomy`（系统/区域/群/亚群、对象数、加载状态）、`get_lesson`（课程组装顺序、组成、运动、肌群、轴规则、缺失项）；写工具 `set_highlight`（ids+state）、`play_assembly`（组序列/每步时长/缓动/方向）、`play_joint_motion`（关节枚举或 id、运动枚举、起止角、时长、循环、移动对象可选覆盖）、`camera_tour`（视点序列/环转/停留）、`stop_animation`。
  - 全部写工具走审批与 schema 校验；Agent 循环支持"等待动画播完"（类似 viewHold 的可中断等待，时长受 animationBudget 钳制）；错误回传可自纠。
  - 更新 SYSTEM 提示词：发现（只读工具）→确认 id→申请播放→边停边讲→主动回忆的教学法；方位术语规则；近似轴/刚性肌/未加载不编造/未审校边界；节奏规则。
- **Acceptance Criteria Addressed**: AC-2, AC-9, FR-26, FR-27, FR-28
- **Test Requirements**:
  - `rule` TR-19.1：每个新工具一条合法 + 两条非法夹具用例；写工具未授权时不执行且不重复请求；证据：浏览器夹具。
  - `rule` TR-19.2：schema/白名单自动同步测试在新增工具后仍通过；证据：node --test。

## Task 20: 腕课程 Agent 端到端验证
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 19, Task 13
- **Description**:
  - 扩展模拟兼容服务/浏览器 e2e：用户发出腕部学习请求 → Agent 调用 list_taxonomy/get_lesson/search → 申请组装并播放 → 六面相机编排 → 屈伸、桡尺偏运动（肌群高亮）→ 文字讲解边界声明 → start_practice；断言工具序列、时间轴实际产生画面变化（状态/截图对比）、缺料场景提示加载对应系统、拒绝授权路径安全。
  - 更新 tests/_verify_agent*.py 与 RESULTS/VALIDATION 记录。
- **Acceptance Criteria Addressed**: AC-9, FR-30
- **Test Requirements**:
  - `rule` TR-20.1：e2e 脚本在无真实密钥下通过并留存序列日志与 _runtime 截图；证据：测试输出与截图。
  - `rule` TR-20.2：拒绝授权一次后 Agent 不再申请同一动作且最终消息照常完成讲解；证据：e2e 断言。

## Task 21: 全量回归与发布构建
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 20, Task 10, Task 14
- **Description**:
  - 跑全部测试：`python tools/build.py`、test_build.py、server_http_test.py、`node --test agent-server/protocol.test.mjs`、`npm run check`、浏览器夹具套件；更新 tests/RESULTS、SERVER_HTTP_RESULTS、VALIDATION_SUMMARY；重建 dist（不入库）做冒烟。
  - 单文件导出/旧版 HTML 导入/SHA 校验/记录白名单/密钥不导出回归。
- **Acceptance Criteria Addressed**: AC-13
- **Test Requirements**:
  - `rule` TR-21.1：所有命令退出码 0，结果文件更新且数字一致；证据：命令日志归档。

## Task 22: 文档与版本说明
- **Status**: pending
- **Priority**: medium
- **Depends On**: Task 21
- **Description**:
  - 更新 [README_中文.md](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/README_中文.md)（设置中心、命名可信度、模型档位、动画课程、Agent 工具新清单与限额）、[ARCHITECTURE.md](file:///d:/projects/Dev-Web/Forma-Anatomy-Studio/ARCHITECTURE.md)（命名层、来源注册表、时间轴、单一工具事实源扩展入口）、RELEASE_NOTES、agent-server README（v6 锁定/ajv/lockfile/v7 迁移备注）。
  - Open Questions 中 DBCLS 许可确认事项写入 docs 待办。
- **Acceptance Criteria Addressed**: AC-14
- **Test Requirements**:
  - `rule` TR-22.1：文档中工具清单/限额默认值/文件名与实现逐一对应（评审表）；证据：文档评审记录。

## Task 23: 设计走查与独立评审准备
- **Status**: pending
- **Priority**: medium
- **Depends On**: Task 22
- **Description**:
  - 浅/深主题、桌面/窄屏对设置中心、助教设计条、动画播放条、命名徽标、模型资源档位做统一走查与打磨；完成后进入 Spec Mode Review（全新上下文独立评审，生成 review.md）。
- **Acceptance Criteria Addressed**: AC-11
- **Test Requirements**:
  - `rubric` TR-23.1：整体体验；1–5；阈值 ≥4；证据：走查截图集与评审记录。
