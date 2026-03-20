# StarResonanceMidi（中文说明）


这是一个将 MIDI 映射为键盘输入的 Flet 图形工具，支持播放列表顺序播放、曲间过渡缓冲、多语言文案与参数调节。

主要用途：将 MIDI 文件映射到键盘，用于「星痕共鸣 / Blue Protocol: Star Resonance / ブループロトコル：スターレゾナンス」内演奏。

语言版本：
- 英文（默认首页）：[README.md](README.md)
- 中文：当前页面
- 日文：[README.ja.md](README.ja.md)

## 许可证

本项目采用 **GNU Affero General Public License v3.0 or later（AGPL-3.0-or-later）**。

## 歌曲/MIDI 版权与商标版权声明

- 本软件为独立的非官方工具，与游戏发行方或权利方无隶属、无背书关系。
- 你需要自行确保所使用歌曲与 MIDI 文件的合法性。
- 未经授权，请勿上传、传播或公开演奏受版权保护的歌曲/MIDI。
- 游戏商标/名称「蓝色协议 / Blue Protocol」归属于 **BANDAI NAMCO**。
- 游戏「星痕共鸣 / Blue Protocol: Star Resonance / ブループロトコル：スターレゾナンス」版权归属于 **BOKURA**。

## 文件头“约束模板”说明

统一文件头包含四项：
- `Author`：作者/维护者信息。
- `Purpose`：文件职责。
- `Constraints`：协作约束（例如必须使用 locale key、不要破坏回调签名）。
- `License`：许可证标识。

其中 `Constraints` 不是许可证，而是团队工程规范。

## 环境要求

- Python 3.10+
- 依赖包：`flet`、`mido`、`pynput`

安装示例：

```bash
python -m pip install flet mido pynput
```

## 运行方式

在项目根目录执行：

```bash
python main.py
```

## 多语言键命名规范

所有用户可见文案应通过 `locales.json` 管理，并在代码中以 key 调用。

建议分组：
- `nav_*`：导航
- `play_*`：演奏页
- `lib_*`：曲库页
- `set_*`：设置页
- `msg_*`：运行状态与通知

新增 key 时请同时：
1. 在 `en`、`ja`、`zh` 三个语言段都补齐。
2. 保持各语言段的 key 顺序一致。
3. 代码中使用 key，不直接写死文案。

## 翻译贡献说明

欢迎提交其他语言版本的翻译。

请以英文主文档的规范为准：
- 规则入口见 [README.md](README.md) 的 Translation Contributions 章节。
- 新语言需要同时更新 [locales.json](locales.json) 与 README 语言链接。
- 提交前请运行校验脚本，确保 key 一致。

## locales 一致性校验

脚本路径：[scripts/check_locales.py](scripts/check_locales.py)

执行：

```bash
python scripts/check_locales.py
```

返回值：
- `0`：三种语言 key 完全一致。
- `1`：存在缺失或多余 key，终端会打印差异明细。
