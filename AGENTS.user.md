# UtsuroClip User Mode

## 目的

このリポジトリでは、動画概要から調査・台本・映像を作成する。現在の工程で指定された成果物だけを作成し、中間成果物を残すこと。

## 共通ルール

- `input/request.md` またはCLIから指定された動画概要を最初に読む。
- 事実を扱うときはWebで調査し、一次情報または信頼できる情報源を優先する。確認済みの情報と不確実な情報を混同しない。
- 成果物はUTF-8のMarkdownまたは指定されたファイル形式で保存する。チャット回答だけで工程を終えない。
- 台本に、調査結果で裏付けられない断定を追加しない。
- ナレーションは最大約3分に収める。日本語ではおおむね毎分300字を目安にする。
- 外部サービスへの投稿、送信、公開は行わない。動画生成に必要なローカルの VOICEVOX、Manim、FFmpeg だけを使う。

## 成果物の場所

- 調査: `work/research/research.md` と `work/research/sources.md`
- 台本: `work/script/script.md`
- 音声: `work/audio/scene_XXX.wav`
- Manimコード: `work/scenes/scene_XXX.py`
- シーン映像: `work/rendered/scene_XXX.mp4`
- 最終映像: `output/video.mp4`

## 外部ツール

- 音声は `python tools/voicevox.py` を用いる。
- Manimのシーンは `python tools/manim_renderer.py` を用いる。
- 映像と音声の結合は `python tools/ffmpeg.py` を用いる。
- 実行に失敗した場合は原因を確認して可能な範囲で修正する。インストールされていないツールを代替実装したり、成果物がないまま成功と報告したりしない。
