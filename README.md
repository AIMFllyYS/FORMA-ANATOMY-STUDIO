# Forma · 解剖学习工作台

Forma is a browser-based 3D workbench for learning systematic anatomy. Structure names are shown in standard Chinese; English and Latin stay in the side panel as a glossary. It is a study aid, not a clinical device.

给医学生用的三维系统解剖学学习与复习工具。原生 JavaScript + WebGL2，不依赖前端框架。打开单文件页面就能转模型、点结构、对照中文标准名复习。作者自己备考时把散落的英文网格名整理成能直接背的中文，开源是为了让同样在学解剖的同学少走弯路，也欢迎一起改错别字和名词。

## 这是做什么的

- **看结构**：载入骨骼、关节、肌、内脏、脉管、淋巴和神经的源网格，旋转、剖切、爆炸图和隔离。
- **认名字**：悬停、选中标签、结构树、搜索和画布标签用中文。右侧讲解面板同时给出拉丁文和英文，方便对教材。
- **左右侧**：成对结构按教材习惯写成「右肺尖段动脉」「左足籽骨」，而不是只留一个英文 Left/Right。
- **复习**：465 张本地学习卡、关节学习场景、离线练习。可选的 Agent 只能调用页面里写死的教学工具。
- **名词从哪来**：运行时读 `web/nomenclature.json`。人工校对结果在 `tools/data/zh_proofread.json`，`tools/build_nomenclature.py` 重建时会盖过 Wikidata 自动译文，避免下次生成把改过的中文冲掉。仍不确定的条目标成「待审」，清单在 `tools/data/zh_review_pending.md`。

模型是减面后的教学网格，不是影像，也不是标本。没载入的韧带或腔隙不会被程序补出来。

## 为什么开源

这个工作台是备考过程里长出来的：英文网格名对不上人卫教材，Wikidata 上还有「壳」被写成娱乐团体、「橄榄」被写成油橄榄这种错。中文名词是给自己背的，也会错。仓库公开，是希望一起学解剖的人能直接改 `tools/data/zh_proofread.json` 里的一条译名，而不是各自维护一份对不上的表。

改名词时请对照人民卫生出版社《系统解剖学》《局部解剖学》，以及全国科学技术名词审定委员会的《人体解剖学名词》。拿不准就保留中文草稿，把 `status` 写成 `pending`，并在 `note` 里写原因。足大趾用「踇」、拇指用「拇」，这样「踇长屈肌」和「拇长屈肌」不会在同一个界面里变成同一个词。

## 怎么打开

构建后的页面是 `dist/forma_anatomy_studio.html`（`dist/` 不入库，需本地生成）。双击或用浏览器打开。首次载入骨骼会向公开模型地址请求 GLB，失败时页面报错，不会换成假骨架。

常用操作：左键旋转，`G` 平移，滚轮缩放，单击选中并显示名称，双击进入结构分析，右键打开结构菜单。搜索框接受中文、英文、拉丁文和拼音。

## 开源素材与许可证

下面每条都按来源页核对过。模型二进制不在本仓库里；标准档是运行时从上游地址加载的衍生网格。

| 素材 | 用在哪里 | 许可证 | 链接 |
| --- | --- | --- | --- |
| Z-Anatomy（Gauthier Kervyn、Marcin Zielinski） | 网格与 TA2 英文/拉丁对照的上游；`tools/build_nomenclature.py` 读取其 `TA2.csv` | 仓库声明为 **CC BY-SA 4.0**。署名要求写明 “Z-Anatomy - The libre 3D atlas of anatomy - CC-BY-SA 4.0” | https://github.com/Z-Anatomy/Models-of-human-anatomy/blob/master/License.txt |
| BodyParts3D（DBCLS / Kousaku Okubo） | Z-Anatomy 的原始轮廓数据 | 官网写明轮廓与渲染图为 **CC BY-SA 2.1 Japan** | https://lifesciencedb.jp/bp3d/info_en/ |
| Z-Anatomy 内的分件 | 可能进入神经、内耳、肾等相关网格。本仓库不能把它们从系统 GLB 里拆开 | 颅神经与孔道：Dundee CAHID，**CC BY 4.0**。内耳：Dundee School of Medicine，**CC BY-NC-SA 4.0**。肾：Lissie Cowley，**CC BY-NC 4.0**。华盛顿大学 “Brainder” / 白质：**许可证未在上游 License.txt 写明，待确认** | 同上 License.txt 的 Attributions |
| DrMuratAltun/anatomi-simulatoru | 标准档 `systems/*.glb` 的公开减面衍生文件。本项目不用它的 three.js 包，也不用它的标志 | 上游 ATTRIBUTION 写明这些 GLB 是 Z-Anatomy 的衍生作品，按 **CC BY-SA 4.0** 分发 | https://github.com/DrMuratAltun/anatomi-simulatoru/blob/main/ATTRIBUTION.md |
| Wikidata 结构化数据 | 早期自动中文/拉丁标签（现已被校对表覆盖的条目不再单独依赖在线结果） | 结构化数据为 **CC0** | https://www.wikidata.org/wiki/Wikidata:Licensing |
| `ai` 6.0.283、`@ai-sdk/openai-compatible` 2.0.75 | 可选 `agent-server/` | **Apache-2.0**（以 `agent-server/package-lock.json` 的 `license` 字段为准） | https://github.com/vercel/ai |
| `ajv` 8.20.0 | 同上，校验工具参数 | **MIT** | https://github.com/ajv-validator/ajv |
| `opencc-python-reimplemented` | `tools/requirements.txt`；构建时把维基繁体标签转成简体 | PyPI 分类为 **Apache License** | https://pypi.org/project/opencc-python-reimplemented/ |
| `pypinyin` | `tools/gen_pinyin.py` 生成 `web/pinyin-data.js` | PyPI 分类为 **MIT** | https://pypi.org/project/pypinyin/ |

工作台自己的界面代码见根目录 `LICENSE`（与 `licenses/LICENSE_CODE_MIT.txt` 相同）：**仅代码是 MIT**。MIT 不能把上面的模型、名词数据或非商业分件改成可以随意商用。更细的署名边界在 `licenses/SOURCE_NOTICES.md`。

再分发带网格的离线 HTML 时，请保留 Z-Anatomy 与 BodyParts3D 的署名，并按 CC BY-SA 以相同方式共享该衍生网格。不要把上游标志当成自己的商标。

## 使用声明

**仅供学习交流。** 不能用于临床诊断或治疗，不能代替教材、标本和执业判断。网格经过减面，方向用的是源坐标，运动演示是教学近似，不是生物力学认证。

**不得商用。** 上游图集里含有 CC BY-NC、CC BY-NC-SA 分件，系统级 GLB 又没有把这些分件拆干净，因此整个模型链路按非商业使用。模型衍生部分还需要署名，并按 CC BY-SA 相同方式共享。

若认为仓库内容侵犯了你的权利，请通过代码托管平台联系，核实后删除。

## 仓库用哪一份许可证

根目录 `LICENSE` 采用已有的代码 MIT，而不是把整个仓库改成 CC BY-SA。理由：

- 代码许可证与模型许可证可以并列。MIT 允许代码与 BY-SA 素材放在一起，只要素材继续按它自己的许可证分发。
- 把代码改成 CC BY-SA 会比现在的 MIT 更严，也不能取消上游 CC BY-NC 分件的非商业限制。
- 因此：代码 MIT；模型及其减面衍生文件保持 CC BY-SA 4.0，并带上 BodyParts3D（CC BY-SA 2.1 Japan）署名；含 NC 分件的内容不得商用。

## 从源码构建

需要 Python 3.10+。

```bash
python tools/build.py
```

生成 `dist/forma_anatomy_studio.html`。浏览器标签图标是墨绿 `#36755b` 圆角方块、白色衬线 F 和骨色 `#c7ba98` 圆点，写在 `web/shell.html` 的 `<title>` 后面。

名词有改动时：

```bash
python tools/build_nomenclature.py --no-wikidata   # 会合并 tools/data/zh_proofread.json
python tools/gen_pinyin.py                         # 需要 pypinyin
python tools/build.py
```

`tools/build_nomenclature.py` 在没有本地缓存时会下载 Z-Anatomy 的 `TA2.csv`。`--no-wikidata` 跳过在线 SPARQL。校对表仍然会写上中文。

```bash
python -m unittest tests.test_nomenclature tests.test_build
```

可选 Agent 代理在 `agent-server/`，依赖见其 `package.json`。不要把 API key 或 `.env` 提交进仓库。
