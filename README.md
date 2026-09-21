# UtsuroClip

Codex、Manim、VOICEVOX、FFmpegを使って、Markdownの動画概要から縦型の短尺解説動画を生成するCLIツールです。調査結果、台本、音声、Manimコード、シーン映像も `work/` に残ります。

## 必要環境

外部ツールは利用者がインストールして起動します。UtsuroClip はそれらを自動ダウンロードしません。

- Python 3.10以上
- [Codex CLI](https://developers.openai.com/codex/cli/)（ログイン済みであること）
- [VOICEVOX Engine](https://github.com/VOICEVOX/voicevox_engine)（ローカルで起動すること）
- [Manim Community Edition](https://docs.manim.community/en/stable/installation.html)
- [FFmpeg](https://ffmpeg.org/download.html)

### 1. Codex CLI

公式の [Codex CLI インストール手順](https://developers.openai.com/codex/cli/) に従って導入し、ログインしてください。導入後に次を確認します。

```bash
codex --version
codex login
```

### 2. VOICEVOX Engine

[VOICEVOX Engine のリリース](https://github.com/VOICEVOX/voicevox_engine/releases)または公式のDockerイメージを使用し、Engine をローカルのポート `50021` で起動します。Dockerを使う例は次のとおりです（CPU版のタグは公式リリースで利用可能なものを確認してください）。

```bash
docker run --rm -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest
```

別ターミナルで API が応答することを確認します。

```bash
curl http://127.0.0.1:50021/version
```

### 3. Manim Community Edition

Manim 公式のOS別依存パッケージ手順を先に満たしたうえで、Python仮想環境へ導入します。

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install manim
manim --version
```

ManimはFFmpegやCairo/Pangoなどのシステム依存を必要とする場合があります。OSごとの追加手順は[公式インストールガイド](https://docs.manim.community/en/stable/installation.html)を参照してください。

### 日本語フォント

映像内に日本語のテキストを表示する場合、Manimが利用できる日本語フォントが必要です。Ubuntu / Debianでは、Noto CJKフォントを導入してフォントキャッシュを更新します。

```bash
sudo apt update
sudo apt install fonts-noto-cjk
fc-cache -f
```

導入後、次のコマンドで日本語対応フォント（例: `Noto Sans CJK JP`）が表示されることを確認してください。

```bash
fc-list :lang=ja family | sort -u
```

### 4. FFmpeg

代表的な導入例です。Windowsは[公式配布ページ](https://ffmpeg.org/download.html)または利用中のパッケージマネージャーを使用してください。

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu / Debian
sudo apt update
sudo apt install ffmpeg

ffmpeg -version
```

## セットアップ

プロジェクトを取得したら、Pythonパッケージを開発モードで導入します。

```bash
python3 -m pip install -e .
```

動画生成用のCodex設定とSkillを配置します。

```bash
bash setup.sh
```

このコマンドは `AGENTS.user.md` を `AGENTS.md` へ、`.codex.user/` を `.codex/` へ、`.agents.user/` を `.agents/` へコピーします。同名の設定ファイルは上書きされるため、独自の変更がある場合は事前に退避してください。

動画生成時、UtsuroClip は VOICEVOX Engine の既定URLである `http://127.0.0.1:50021` だけへ接続できる Codex ネットワーク設定を明示的に適用します。公開インターネットや他のローカル宛先は許可しません。VOICEVOX Engine を別のホストまたは `localhost` 名で起動する場合は、この許可先の変更が必要です。

UtsuroClip本体を開発する場合は、代わりに次を実行します。

```bash
bash setup.sh --dev
```

## 使い方

`input/request.md` を編集するか、`examples/sample-request.md` を参考に動画概要を作成します。

```bash
utsuroclip generate input/request.md
```

ナレーション話者は `ずんだもん`、`四国めたん`、`春日部つむぎ` から選べます。既定値は `春日部つむぎ` です。

```bash
utsuroclip generate input/request.md --speaker ずんだもん
```

実行すると以下の順に Codex が起動します。

1. 調査を行い、`work/research/research.md` と `work/research/sources.md` を生成する。
2. 調査結果から `work/script/script.md` を作成する。
3. VOICEVOX、Manim、FFmpegを使い、`output/YYYYMMDDhhmmss_タイトル.mp4` を生成する。タイトルはCodexが動画内容に合わせて決定する。

実行中は、工程の開始・完了、Codex が実行するコマンド、Web 検索、Codex からの進捗メッセージが端末に表示されます。各工程の終了時とパイプライン全体の終了時には、経過時間と Codex が報告した input / cached input / output / reasoning output トークン数が表示されます。Codex CLI が使用量を返さない場合は `取得不可` と表示されます。

各工程の JSONL 標準出力・標準エラー・最終メッセージは `work/logs/` に保存されます。Codex、VOICEVOX、Manim、FFmpegのどれかが利用できない場合は、必要な工程で停止し、ログに原因を残します。

`work/` に前回の中間成果物が残っている場合、生成前に削除確認を表示します。確認しない場合は生成を中断します。自動実行では、`-y` または `--yes` を指定して確認なしで削除・生成できます。

```bash
utsuroclip generate input/request.md --yes
```

Codex CLIの実行ファイルやプロジェクトルートを明示したい場合は、次のオプションを使えます。

```bash
utsuroclip generate /absolute/path/request.md --project-root /path/to/utsuroclip --codex-bin codex
```

## ライセンスと外部ツール

UtsuroClip本体は [MIT License](LICENSE) で提供します。Codex CLI、VOICEVOX Engine、Manim Community Edition、FFmpegは利用者が別途導入する外部ツールであり、詳細なライセンスと利用上の注意は[第三者通知](THIRD_PARTY_NOTICES.md)を確認してください。

VOICEVOXで生成した音声を公開する際は、選択した話者に対応するクレジット表記が必要です。動画内または説明欄などに、たとえば `VOICEVOX:春日部つむぎ` と記載してください。話者ごとの詳しい条件は[第三者通知](THIRD_PARTY_NOTICES.md#voicevox-generated-audio)から公式規約を確認してください。
