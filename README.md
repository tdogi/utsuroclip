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

実行すると以下の順に Codex が起動します。

1. 調査を行い、`work/research/research.md` と `work/research/sources.md` を生成する。
2. 調査結果から `work/script/script.md` を作成する。
3. VOICEVOX、Manim、FFmpegを使い、`output/video.mp4` を生成する。

各工程の標準出力・標準エラー・最終メッセージは `work/logs/` に保存されます。Codex、VOICEVOX、Manim、FFmpegのどれかが利用できない場合は、必要な工程で停止し、ログに原因を残します。

Codex CLIの実行ファイルやプロジェクトルートを明示したい場合は、次のオプションを使えます。

```bash
utsuroclip generate /absolute/path/request.md --project-root /path/to/utsuroclip --codex-bin codex
```
