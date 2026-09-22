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
python -m pip install "manim==0.21.0"
manim --version  # Manim Community v0.21.0 と表示されること
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

このコマンドは `AGENTS.user.md` を `AGENTS.md` へ、`.codex.user/` を `.codex/` へ、`.agents.user/` を `.agents/` へコピーします。既存の `AGENTS.md` 、 `.codex/` 、 `.agents/` は削除されるため、独自の変更がある場合は事前に退避してください。

動画生成時、UtsuroClip は VOICEVOX Engine の既定URLである `http://127.0.0.1:50021` だけへ接続できる Codex ネットワーク設定を明示的に適用します。公開インターネットや他のローカル宛先は許可しません。VOICEVOX Engine を別のホストまたは `localhost` 名で起動する場合は、この許可先の変更が必要です。

UtsuroClip本体を開発する場合は、代わりに次を実行します。

```bash
bash setup.sh --dev
```

## 使い方

`input/request.sample.md` を参考に、動画概要ファイル `input/request.md` を作成します。

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

通常はCodexが一時ファイル `output/video.mp4` を生成し、CLIが最終ファイル名へ変更します。Codexが誤って一時ファイルを別名へ変更した場合でも、その実行で新規作成されたMP4が1本だけなら、`generate` と `revise` のどちらでもCLIが安全に回収して記録します。複数の新規MP4がある場合は対象を推測せずに停止します。

各工程の JSONL 標準出力・標準エラー・最終メッセージは `work/logs/` に保存されます。Codex、VOICEVOX、Manim、FFmpegのどれかが利用できない場合は、必要な工程で停止し、ログに原因を残します。

`work/` に前回の中間成果物が残っている場合、生成前に削除確認を表示します。確認しない場合は生成を中断します。自動実行では、`-y` または `--yes` を指定して確認なしで削除・生成できます。

```bash
utsuroclip generate input/request.md --yes
```

Codex CLIの実行ファイルやプロジェクトルートを明示したい場合は、次のオプションを使えます。

```bash
utsuroclip generate /absolute/path/request.md --project-root /path/to/utsuroclip --codex-bin codex
```

## 完成動画の修正

最後に `generate` した動画は、対応する制作素材と完成MP4のパスを `work/` に記録します。完成後に台本、文字サイズ・位置、図、特定時間帯の演出などを修正したいときは、自然言語の指示を指定します。

```bash
utsuroclip revise -p "20秒あたりの波形の図を少し下に移動させて"
```

`revise` は記録済みの完成動画と `work/` の台本、音声、Manimコード、シーン映像を確認して、修正対象をCodexに特定させます。必要な素材だけを更新・再レンダリングし、元動画を残したまま `元動画名_revised_YYYYMMDDhhmmss.mp4` の形式で `output/` に修正版を保存します。続けて修正する場合は、直前の修正版が対象になります。

`revise` は開始前に制作セットと修正対象MP4を一時バックアップします。Codex工程、成果物検証、保存のいずれかが失敗した場合は、台本・音声・Manimコード・シーン映像・対象記録・対象MP4を修正前の状態へ戻します。失敗した修正で新規作成されたMP4は削除し、`work/logs/revise-video.*` のログは原因調査のため保持します。

新しい `generate` を開始すると `work/` の中間成果物と記録は削除されるため、過去動画を選択して修正することはできません。`work/` の制作素材、記録済みの対象MP4、または必要な依存ツールがない場合、`revise` は失敗して直接MP4を編集しません。

前回失敗した処理の一時ファイル `output/video.mp4` が残っている場合も、誤って修正版として保存しないように停止します。内容を確認したうえで、この一時ファイルを削除してから再実行してください。

Codex CLIまたはプロジェクトルートを明示する場合は、次のように指定できます。

```bash
utsuroclip revise -p "冒頭の説明をもっと短くして" --project-root /path/to/utsuroclip --codex-bin codex
```

## ライセンスと外部ツール

UtsuroClip本体は [MIT License](LICENSE) で提供します。Codex CLI、VOICEVOX Engine、Manim Community Edition、FFmpegは利用者が別途導入する外部ツールであり、詳細なライセンスと利用上の注意は[第三者通知](THIRD_PARTY_NOTICES.md)を確認してください。

VOICEVOXで生成した音声を公開する際は、選択した話者に対応するクレジット表記が必要です。動画内または説明欄などに、たとえば `VOICEVOX:春日部つむぎ` と記載してください。話者ごとの詳しい条件は[第三者通知](THIRD_PARTY_NOTICES.md#voicevox-generated-audio)から公式規約を確認してください。
