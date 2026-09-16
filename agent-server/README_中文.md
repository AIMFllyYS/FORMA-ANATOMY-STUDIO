# 可选服务端：Vercel AI SDK 6 × Forma 画布

这个目录是真正独立的 Node.js 服务端，不嵌在 HTML 中。前端单文件即使没有本服务仍可查看模型、做本地练习和通过兼容协议直连个人接口。

## 当前验证状态

已通过 `protocol.test.mjs` 的消息／工具结果转换测试和 `tests/server_http_test.py` 的 HTTP、鉴权、Origin、模型白名单与单文件静态路由测试。服务采用 SDK 动态导入，因此这些测试不需要联系模型提供方。

制作环境的 npm 网络不可用；没有安装 `ai` 与 `@ai-sdk/openai-compatible`，没有真实 Key，**SDK 工具回合与真实提供方端到端尚未验证**。依赖使用 SDK 6 主版本，不声称已测试新主版本或所有兼容提供方；首次成功安装后应保存 npm 锁文件并回归测试。

## 配置

需要 Node.js 22+。在工程根目录：

```bash
python tools/build.py
cd agent-server
npm install
cp .env.example .env
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

Windows PowerShell 的复制命令使用 `Copy-Item .env.example .env`。把刚生成的随机令牌填进 `.env` 的 `PROXY_TOKEN`，其余字段按本人的提供方填写：

```dotenv
HOST=127.0.0.1
PORT=8787
MODEL_BASE_URL=https://你的兼容服务/v1
MODEL_API_KEY=你的提供方密钥
MODEL_ID=实际获准使用的模型ID
PROXY_TOKEN=独立随机代理访问令牌
ALLOWED_ORIGINS=http://127.0.0.1:8787,http://localhost:8787
ALLOW_FILE_ORIGIN=false
```

`MODEL_BASE_URL` 是基址，不附 `/chat/completions`。不要把 .env 上传到仓库；代码默认拒绝没有足够长度代理令牌的启动。代理令牌必须与提供方密钥不同。

```bash
npm start
```

浏览器打开 `http://127.0.0.1:8787/`，同一个服务会提供构建好的完整 HTML。右侧 Agent 设置填写：

```text
URL       http://127.0.0.1:8787/agent
API Key   PROXY_TOKEN（代理令牌，不是 MODEL_API_KEY）
Model ID  与 .env MODEL_ID 一致
```

默认只允许指定的本地网页来源。直接双击 file:// HTML 调用代理需要显式开启 `ALLOW_FILE_ORIGIN=true`，且只能绑定回环地址并仍需令牌；更推荐由服务提供页面，不放宽到所有 Origin。没有任何功能要求禁用浏览器安全检查。

## 数据流

```text
HTML 内的 Agent 会话
   → POST /agent，Bearer 代理令牌
   → 服务校验来源、令牌、模型白名单和消息格式
   → Vercel ToolLoopAgent / OpenAI-compatible provider
   → 返回文本或白名单工具调用意图
   → HTML 显示写操作批准窗口
   → HTML 在真实 WebGL 场景执行已批准的工具
   → 返回实际工具结果到下一回合
```

工具不在服务器直接执行：真实模型存在浏览器中。工具定义只有一份事实源 `../web/agent-tools.json`（浏览器经构建器内嵌为 `#agent-tools-data`，服务端直接读取，`tools-sync.test.mjs` 断言两端一致）。服务用 `stopWhen: stepCountIs(1)` 完成一次模型回合；前端管理外层有界循环和工具批准。不能在后台“假执行”画布工具然后告诉用户已经聚焦。

## 安全和运行边界

- 提供方 Key 只从环境变量读取；HTML 只持有本次会话的代理令牌。
- 固定工具白名单，没有 eval、shell、文件读取、任意 URL 抓取工具。
- 来源白名单、模型白名单、Bearer 认证、2MB 请求限制、每 IP 限流、并发与超时限制。
- 不输出 prompt、Key 或私人笔记日志；异常文本尝试擦除密钥。
- 不提供任意文件静态服务器；仅 `/` 返回固定构建 HTML。
- 不默认具备多人账户、用户隔离、持久配额和企业认证。公开部署前需补这些能力，并配置 HTTPS、反向代理、请求审计与依赖更新。
- Chat Completions 兼容不保证每个模型都支持 tools；不支持的服务会返回错误，不假装完成。

参考一手文档：
- [Vercel ToolLoopAgent](https://ai-sdk.dev/docs/reference/ai-sdk-core/tool-loop-agent)
- [OpenAI-compatible provider](https://ai-sdk.dev/providers/openai-compatible-providers)
- [Model messages](https://ai-sdk.dev/docs/reference/ai-sdk-core/model-message)
- [OpenAI API Key Safety](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)
