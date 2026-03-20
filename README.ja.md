# StarResonanceMidi（日本語ドキュメント）


MIDI をキーボード入力に変換する Flet GUI ツールです。プレイリスト連続再生、曲間バッファ、UI 多言語、微調整に対応しています。

主な用途: MIDI ファイルをキーボード入力へ変換し、「星痕共鳴 / Blue Protocol: Star Resonance / ブループロトコル：スターレゾナンス」での演奏に利用すること。

言語ページ：
- 英語（デフォルト）：[README.md](README.md)
- 中国語：[README.zh-CN.md](README.zh-CN.md)
- 日本語：このページ

## ライセンス

本プロジェクトは **GNU Affero General Public License v3.0 or later（AGPL-3.0-or-later）** です。

## 楽曲/MIDI の著作権および商標・権利表記

- 本ソフトウェアは非公式の独立ツールであり、ゲーム運営・権利者との提携や公認はありません。
- 利用する楽曲および MIDI データの適法性は利用者の責任で確認してください。
- 権利許諾のない楽曲/MIDI の配布・公開・演奏は行わないでください。
- 商標/名称「Blue Protocol」は **BANDAI NAMCO** に帰属します。
- 「星痕共鳴 / Blue Protocol: Star Resonance / ブループロトコル：スターレゾナンス」の著作権は **BOKURA** に帰属します。

## ヘッダの「Constraints」について

統一ヘッダは次の 4 項目です。
- `Author`：作成者/保守者情報
- `Purpose`：ファイルの責務
- `Constraints`：実装上のルール（例: 文言は locale key 管理、コールバック署名を壊さない）
- `License`：ライセンス識別子

`Constraints` はライセンスではなく、開発運用ルールです。

## 必要環境

- Python 3.10+
- 依存パッケージ：`flet`、`mido`、`pynput`

インストール例：

```bash
python -m pip install flet mido pynput
```

## 実行

プロジェクトルートで実行：

```bash
python main.py
```

## locale キー規約

ユーザー向け文言は `locales.json` の key を通して使用してください。

推奨グループ：
- `nav_*`：ナビゲーション
- `play_*`：再生ビュー
- `lib_*`：ライブラリビュー
- `set_*`：設定ビュー
- `msg_*`：実行時メッセージ

新しい key を追加する場合：
1. `en`、`ja`、`zh` の全ロケールに追加
2. キー順とグループをロケール間で統一
3. コード側で key を参照し、文言を直書きしない

## 翻訳コントリビューション

他言語への翻訳コントリビューションを歓迎します。

運用ルールは英語のメイン文書を基準にしてください：
- 詳細は [README.md](README.md) の Translation Contributions セクション
- 新言語を追加する場合は [locales.json](locales.json) と README の言語リンクを更新
- 提出前にキー整合性チェックを実行

## locales 一貫性チェック

スクリプト：[scripts/check_locales.py](scripts/check_locales.py)

実行：

```bash
python scripts/check_locales.py
```

終了コード：
- `0`：全ロケールでキー集合が一致
- `1`：差分あり（不足/余剰キーを出力）
