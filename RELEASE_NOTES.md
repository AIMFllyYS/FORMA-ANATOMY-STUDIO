# Forma 4.0 · Agent 教学能力 + 规范命名/功能分类 + 时间轴课程

这轮在 Forma 3.0 的 Agent 行为限额与协议加固之上，交付一条完整的"系统解剖
认知路径"：规范命名层、功能群分类、确定性时间轴动画、腕关节贯通课程，以及
可扩展的模型档位注册表。

## 新增

### 规范命名层（zh / en / la + 可信度）
- `tools/build_nomenclature.py` 从七系统 GLB 语料 + TA2 + Wikidata(CC0) +
  人工覆表生成 `web/nomenclature.json`；网络响应全部走缓存，可完全离线复跑。
- 肌肉/内脏中文名覆盖率 **100%**（门槛 ≥90%）；肌肉 395 / 内脏 60 条人工审校，
  其余为待审自动映射，未命中保留源名并显示"未规范命名"。
- 新增规则化功能分类（头颈肌/躯干肌/上肢带肌/臂肌/前臂肌/手肌/髋肌/大腿肌/
  小腿肌/足肌，内脏按消化/呼吸/泌尿/生殖/内分泌归组），肌肉/内脏有名称节点
  功能群归类 100%，结构树按"系统→区域→功能群→亚群→结构"分层。
- 详情页/悬浮/标签/树统一显示中文名 · 拉丁名 · 英文名 + 拼音；搜索支持中文、
  拉丁名、英文与拼音（拼音表从 698 短语扩充到 1575）。
- 徽标三态：已审校（绿）/ 待审（橙）/ 未规范命名（空心），UI 与 Agent 输出
  都沿用该可信度，不冒充审校结论。

### 确定性时间轴与教学动画
- 新模块 `web/timeline.js`：rAF 时钟、串行/重叠片段、缓动、循环、播放/暂停/停止；
  通道含每对象组装偏移、刚体运动矩阵、相机、多态高亮；显示变换不修改源顶点。
- `prefers-reduced-motion` 直接呈现终态；总时长受 `animationBudgetSeconds`
  钳制；任何新的画布写操作、停止、场景切换即中断并清除残差。
- 多态高亮四态：普通/accent 强调（绿）/series 序列焦点（橙）/contraction
  收缩态（红），拾取 id 不受颜色影响。
- 教学近似轴求解器：从锚点对象真实包围盒中心 + 声明的源坐标方向取两点；
  锚点缺失或几何退化直接中文报错，不静默换轴。

### 腕关节贯通课程（curriculum）
- `web/curriculum.json`：腕关节完整样板——7 步组装（桡尺骨→近排腕骨→远排→
  掌骨→关节盘韧带→屈肌群→伸肌群）、屈伸与桡尺偏两个教学运动（含移动骨组、
  主动/拮抗肌、近似轴规则）、五视点观察。
- 其余七关节迁移到新 schema 并显式标注缺失字段。
- 全界面常驻边界声明："教学近似轴 / 肌肉刚性成组演示，非生理活动度与生物力学
  认证"；源模型朝向未校准前只允许源坐标措辞。
- `tools/validate_curriculum.py` 校验课程全部稳定 id 均能在命名层解析、轴向量
  合法（82 个腕课程引用全部通过）。

### Agent 教学工具（单一事实源同步到服务端）
- 新增只读 `list_taxonomy`、`get_lesson`，写工具 `set_highlight`、
  `play_assembly`、`play_joint_motion`、`camera_tour`、`stop_animation`
  （共 17 个工具，两端共用 `web/agent-tools.json`）。
- 全部写工具走审批 + Schema 校验；动画工具回传 `wait_seconds`，Agent 边播边讲，
  等待受动画预算钳制且可被停止打断。
- SYSTEM 提示词内置教学节奏（发现→申请组装→六面观察→运动→主动回忆）、
  方位术语规则、命名可信度规则与拒绝不重试规则。

### 模型来源注册表与 gzip/档位
- `web/model-sources.json`：standard（上游减面版，立即可用）/ balanced / HD
  （Z-Anatomy 重导出自托管，默认 `available:false`），按 SHA-256 隔离缓存。
- fetch 层与本地导入支持 `.glb.gz`（`DecompressionStream` 本地解压）；
  模型资源弹窗新增档位选择，未生成档位明确提示自托管说明。
- `tools/export_blender.py` 升级：七系统、`.j/.g/'` 特殊对象过滤、曲线转网格、
  节点 `extras.anatomyId/side/tier`、每档 manifest（对象/面数/SHA/许可链）。

## 测试
- Python：`test_build.py` 14 项、新增 `test_nomenclature.py` 5 项（覆盖率门槛、
  id 唯一/可解析、功能群完整、课程引用）。
- Node：agent-server 17 项（含新工具元数据/读写分组/白名单同步，Ajv 校验）。
- 浏览器夹具：新增 `test_timeline_naming.py`（26 项）、`test_wrist_e2e.py`
  （8 项，模拟服务的完整教学序列 + 拒绝不重试）；原 browser_test/verify 全套回归。
- HTTP：`server_http_test.py` 15 项鉴权/来源/校验不回归。
- 全部合成几何夹具带 `SYNTHETIC_GRAPHICS_NOT_ANATOMY` 标记，不作为解剖交付。

## 明确未完成 / 需外部条件
- balanced/HD GLB 实体产物与真机性能（AC-6/12/13）：构建机未安装 Blender，
  脚本已就绪但未对 Z-Anatomy 模板实跑；注册表如实标记不可用，不伪装。
- 命名自动分类为教材常用名的规则映射（待审），逐条专家审校仍以人工覆表为准。
- 方位校准、生理活动度、生物力学认证、CT/MRI 体数据均不在本轮范围。
- agent-server 仍锁定 AI SDK 6（v7 迁移留待独立迭代）。
