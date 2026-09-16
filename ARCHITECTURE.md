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

`app.js` 管理选择、可见性、图层透明度、相机、分离场景栈、可撤销视图、面域、关节轴、练习、布局和笔记。源字节留在 AssetManager。Agent 的 URL、Model 与密钥保存在本机 `localStorage`（`forma-agent-config-v3`），不进入学习记录或导出 HTML；对话仍只留在本次会话。

可逆显示操作通过 scene snapshot 恢复；拆分位移与手动轴旋转属于显示变换，源几何保持不变。临时面域展开会创建使用源顶点子集的显示对象，返回场景时释放 GPU 缓冲，不污染资产原对象统计。

## 工具不是任意执行接口

Agent 提供 10 个限定工具：get_scene、search_structures、get_structure_info、focus_structures、isolate_structures、highlight_structures、set_layer、set_explode、set_view、start_practice。

工具执行器校验已加载 ID、类别、视图枚举和数值范围。改变画布需用户批准；只读工具可自动运行。显式停止、回合上限与请求超时避免无限循环。标签、用户输入、源模型名与模型返回均转义显示，不交给 innerHTML 执行任意脚本。

当前工具不读取私人笔记、不上传模型文件、不增加服务端文件／网络／系统权限。用户在问题中主动输入的内容属于明确发送范围。

## 记录和导出

单文件导出基于页面启动时保存的原始 HTML 模板，而不是当前 DOM。只插入允许字段的实际资产和记录 JSON，避免把聊天、输入框 Key 或动态 UI 注入导出文件。`<` 转义防止 JSON 提前闭合 script。旧 HTML 只通过惰性的 DOMParser 读取 payload，不运行其脚本。

浏览器内导出包含笔记；分享前需要处理隐私。源码构建同样采用 payload 字段白名单；所有模型 SHA 重新计算并核对。

## 扩展入口

增加学习卡：编辑 `web/knowledge.json` 的 `cards`，添加稳定 id、中文/英文、类别、区域、summary、sections、landmarks、sources、review。新增术语不会自动生成模型；新增来源须录入 sources。

增加关节课程：编辑 `web/knowledge.js` 的 JOINTS，定义真实对象匹配、可缺失软组织、学习段落与引用。自动轴和动作要经过独立数据和生物力学验证，不能默默代替当前人工轴。

增加 Agent 工具：同时修改前端定义、执行器、服务端 tool-definitions、消息白名单和权限测试。新工具默认按写操作请求确认，不能增加通用 eval。

增加几何格式：在 mesh-engine.js 的 reader 层实现，并加入畸形输入、索引越界、world transform、法线、拾取和离线 roundtrip 测试。不支持的压缩格式明确报错。

## 必须分开的四种验证

1. 网格解析和字节打包验证。
2. UI 和真实三角面交互验证。
3. 语义命名、边界和领域内容审校。
4. 真实全模型性能、真实接口与部署验证。

本交付完成前两层的工程回归，并提供第三、四层的工作入口；没有用图形夹具通过的测试冒充全身医学图谱认证。
