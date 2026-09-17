# 架构与扩展说明

## 分层，而不是在一个 HTML 里堆功能

```text
源数据 / 旧版离线 HTML / IndexedDB
            ↓
core.js · AssetManager（实际字节、哈希、元数据）
            ↓
mesh-engine.js（严格解析 → 对象/面 → WebGL2 GPU）
            ↕
app.js（显式场景状态、树、讲解、全景、练习、可逆视图）
        ↙            ↘
knowledge.js/json     agent.js
学习卡/语义候选       白名单工具＋批准＋兼容消息循环
                         ↕ 可选
                    agent-server/
                    Vercel AI SDK 6
```

前端采用原生 JavaScript 独立模块＋事件总线，不依赖 React、Three.js、远程 CDN 或 npm 运行时才能打开。源网格引擎沿用原版，不将材质调整或对象显示位移写回源顶点。构建器只把这些模块打包到单 HTML；开发时以分开的源文件为准。

## 结构身份

运行时对象数字 ID 只在当前场景有效。可持久身份由资产 SHA-256、sourceName、nodeIndex 组合。对象可以有多个 primitive，每个面域再绑定 primitive 索引、面数与面编号集合。

原版 v2 面域字段 `assetSHA/key/name`、整对象 `sourceTriangles` 与新版不完全一致。新导入器先验证源 SHA 和对象，再检查整对象面数，最后转换 primitive 面数。不能用同名但不同 SHA 的模型恢复旧 face indices。

知识卡匹配与几何身份分离：exact/alias/numeric match 优先；相关名称仅提供父结构学习材料，显示“相关结构提纲”，不取代源名称。未映射的细部词条保留 term 状态；手工圈出的 face-region 保留 unreviewed 状态。

## 状态管理

`app.js` 管理选择、可见性、图层透明度、相机、分离场景栈、可撤销视图、面域、关节轴、练习、布局和笔记。源字节留在 AssetManager。Agent 的 URL、Model 与密钥保存在本机 `localStorage`（`forma-agent-config-v4`，读取时自动迁移 v3），不进入学习记录或导出 HTML；对话线程（消息＋渲染视图，不含密钥）保存在本机 `localStorage`（`forma-agent-threads-v1`，上限 20 个对话、每对话 100 条消息／60 轮视图），加载后默认恢复上次对话，同样不进入学习记录或导出 HTML。

可逆显示操作通过 scene snapshot 恢复；拆分位移与手动轴旋转属于显示变换，源几何保持不变。临时面域展开会创建使用源顶点子集的显示对象，返回场景时释放 GPU 缓冲，不污染资产原对象统计。

## 工具不是任意执行接口

Agent 提供 17 个限定工具（唯一事实源 `web/agent-tools.json`，浏览器与
agent-server 共用，node 测试强制两端白名单一致）：

- 只读：get_scene、search_structures、get_structure_info、list_taxonomy、
  get_lesson、start_practice（后者切面板但不改几何）。
- 画布：focus_structures、isolate_structures、highlight_structures、set_layer、
  set_explode、set_view。
- 教学动画（v4 新增）：set_highlight、play_assembly、play_joint_motion、
  camera_tour、stop_animation。

工具执行器校验已加载 ID（或命名层稳定 id）、类别、枚举与数值范围。所有写
工具需用户批准并通过 Ajv/内置 Schema 校验；只读工具可自动运行。显式停止、
回合上限、单轮工具数、停留与动画总时长预算避免无限循环或长时间占画。标签、
用户输入、源模型名与模型返回均转义显示，不交给 innerHTML 执行任意脚本。
动画工具回传 `wait_seconds`，Agent 在可中断的等待期间讲解；锚点缺失时
play_joint_motion 直接中文报错，绝不静默换轴。

当前工具不读取私人笔记、不上传模型文件、不增加服务端文件／网络／系统权限。
用户在问题中主动输入的内容属于明确发送范围。

## 命名层与课程层（v4）

- 数据：`tools/build_nomenclature.py` 离线（缓存）融合七系统 GLB 语料、TA2
  拉丁名、Wikidata(CC0) 中/拉标签与人工审校覆表，输出 `web/nomenclature.json`
  （records + 按 system/nodeIndex 的 assignments）。未命中保留源名，不张冠李戴。
- 运行时：`web/nomenclature.js` 提供按 nodeIndex（名称一致时才信任，防跨 GLB
  碰撞）与按名称的双索引解析；`knowledge.js` 的 names/region/family 优先命名层、
  回退旧知识卡，搜索索引加入拉丁名与拼音。结构树按 系统→区域→功能群→亚群→结构
  渲染，详情/标签/悬浮显示中文名·拉丁名·英文名与可信度徽标
  （reviewed/pending/unmapped）。
- 课程：`web/curriculum.json` + `web/curriculum.js`。课程引用全部是命名层稳定
  id；`tools/validate_curriculum.py` 校验引用可解析、轴向量合法。方位未校准时
  anchorRule 只能用源坐标方向，UI/Agent 不得称解剖学前/后/内/外。

## 时间轴（v4）

`web/timeline.js` 是独立于 mesh-engine 的确定性播放器：片段（assembly/
rigidMotion/rigidSweep/cameraMove/highlight）写渲染器的显示通道
（`timelineOffsets` / `timelineMatrixFor` / `highlightState`），不修改源顶点。
rAF 时钟支持播放/暂停/停止/循环、缓动与预算钳制；reduced-motion 或 instant
直接落终态；任何新写操作（remember/restore）都取消时间轴，结束/打断清通道，
保证不留残差矩阵。多态高亮（accent/series/contraction）只改颜色，拾取 id 不变。
教学轴由锚点对象包围盒中心与声明源坐标方向推导，几何退化或缺锚点即失败。

## 模型档位（v4）

`web/model-sources.json` 描述 standard/balanced/HD 三档 URL、gzip、面数预算、
许可与可用标记。AssetManager 按当前档位解析 URL，`.glb.gz` 在无
Content-Encoding 时用 DecompressionStream 本地解压；资产来源标记为
`compact:<tier>`，配合 IndexedDB 的 SHA-256 键天然按档/版本隔离。balanced/HD
需由 `tools/export_blender.py`（七系统、特殊对象过滤、anatomyId extras、
manifest）自托管，未生成时注册表 available:false，UI 明示而非伪装可下载。

## 记录和导出

单文件导出基于页面启动时保存的原始 HTML 模板，而不是当前 DOM。只插入允许字段的实际资产和记录 JSON，避免把聊天、输入框 Key 或动态 UI 注入导出文件。`<` 转义防止 JSON 提前闭合 script。旧 HTML 只通过惰性的 DOMParser 读取 payload，不运行其脚本。

浏览器内导出包含笔记；分享前需要处理隐私。源码构建同样采用 payload 字段白名单；所有模型 SHA 重新计算并核对。

## 扩展入口

增加学习卡：编辑 `web/knowledge.json` 的 `cards`，添加稳定 id、中文/英文、类别、区域、summary、sections、landmarks、sources、review。新增术语不会自动生成模型；新增来源须录入 sources。

增加关节课程：编辑 `web/curriculum.json`（v4 schema：组装顺序、组成、运动、锚点规则、移动组、主动/拮抗肌群 id），运行时由 `web/curriculum.js` 加载，并用 `python tools/validate_curriculum.py` 校验所有引用 id 在命名层可解析。自动轴和动作要经过独立数据和生物力学验证，不能默默代替当前人工轴。

增加 Agent 工具：只改唯一事实源 `web/agent-tools.json`，再在 `web/agent.js`（前端执行器/schema 校验/审批）与 `agent-server/server.mjs`、`agent-server/protocol.mjs`（白名单与 Ajv 校验派生）接线，并补 `agent-server/tools-sync.test.mjs` 两端一致性测试。新工具默认按写操作请求确认，不能增加通用 eval。

增加几何格式：在 mesh-engine.js 的 reader 层实现，并加入畸形输入、索引越界、world transform、法线、拾取和离线 roundtrip 测试。不支持的压缩格式明确报错。

## 必须分开的四种验证

1. 网格解析和字节打包验证。
2. UI 和真实三角面交互验证。
3. 语义命名、边界和领域内容审校。
4. 真实全模型性能、真实接口与部署验证。

本交付完成前两层的工程回归，并提供第三、四层的工作入口；没有用图形夹具通过的测试冒充全身医学图谱认证。
