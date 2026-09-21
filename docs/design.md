# UtsuroClip 設計書

## 1. 概要

UtsuroClip は、Markdown形式で記載された動画の概要から、短尺の解説動画を自動生成するCLIツールである。

ユーザーは、作りたい動画のテーマや伝えたい内容などをMarkdownファイルに記載する。

UtsuroClip本体からCodex CLIを呼び出し、Codexが以下の処理を行う。

* 動画テーマに必要な情報の調査
* Web検索などを利用した事実確認
* 調査結果をもとにした台本作成
* シーン分割
* 演出設計
* Manimコード生成

生成した映像とVOICEVOX音声をFFmpegで結合し、最終的にMP4動画を出力する。

UtsuroClipでは、開発時と動画生成時でCodexの役割が大きく異なるため、用途ごとに異なるAGENTSファイルを使用する。

---

## 2. 対象動画

* 最大約3分
* 縦型 9:16
* 解説系ショート動画
* ジャンルは限定しない
* テキスト、図形、数式、線、矢印などを中心としたモーショングラフィックス

動画は単純な字幕中心の構成ではなく、説明内容に合わせて文字・図・数式・図形などが滑らかに現れ、移動・変形しながら次の情報へつながっていく表現を基本とする。

画面全体を頻繁に切り替えるのではなく、既存の要素を活かしながら次の説明へ自然に移ろう、ミニマルで視覚的に理解しやすい映像を目指す。

---

## 3. 使用技術

* Codex CLI
* Python
* Manim Community Edition
* VOICEVOX Engine
* FFmpeg

Codex CLI、VOICEVOX Engine、Manim Community Edition、FFmpegはUtsuroClipに同梱せず、利用者があらかじめインストールする。導入方法、動作確認、OS別の注意点は `README.md` に記載する。UtsuroClipは各ツールの不在や実行失敗を明示し、存在しない成果物を成功として扱わない。

---

## 4. 基本フロー

```text
input/request.md
        ↓
UtsuroClip CLI
        ↓
codex exec
        ↓
Codex
├─ 動画概要の解析
├─ 必要な情報の特定
├─ Web検索・情報収集
├─ 事実確認
└─ 調査結果の整理
        ↓
work/research/
├─ research.md
└─ sources.md
        ↓
Codex
└─ 調査結果をもとに台本作成
        ↓
work/script/script.md
        ↓
Codex
├─ シーン分割
├─ 演出設計
└─ Manimコード生成
        ↓
VOICEVOX
→ ナレーション音声生成
        ↓
Manim
→ シーン映像生成
        ↓
FFmpeg
├─ 映像と音声を結合
└─ 複数シーンを結合
        ↓
output/video.mp4
```

---

## 5. 入力

動画生成時の入力ファイルは以下とする。

```text
input/request.md
```

ユーザーは完成した台本を書く必要はなく、作りたい動画の概要を記載する。

例：

```markdown
# 動画概要

## テーマ

なぜ空は青いのか

## 伝えたいこと

レイリー散乱の仕組みを、難しい数式を使わずに説明したい。

## 想定視聴者

一般向け

## 動画時間

約90秒
```

記載項目は必須項目を増やしすぎず、テーマや概要だけでも動画生成を開始できる構成を目指す。

---

## 6. ディレクトリ構成

```text
utsuroclip/
├── AGENTS.dev.md
├── AGENTS.user.md
├── README.md
├── setup.sh
├── pyproject.toml
├── .gitignore
│
├── docs/
│   └── design.md
│
├── .codex.dev/
│   ├── config.toml
│   └── rules/
│       └── default.rules
│
├── .codex.user/
│   └── config.toml
│
├── .agents.user/
│   └── skills/
│       └── video-generation/
│           └── SKILL.md
│
├── prompts/
│   ├── research.md
│   ├── write-script.md
│   └── generate-video.md
│
├── src/
│   └── utsuroclip/
│       ├── __init__.py
│       ├── cli.py
│       └── codex.py
│
├── tools/
│   ├── voicevox.py
│   ├── manim_renderer.py
│   └── ffmpeg.py
│
├── input/
│   └── request.md
│
├── work/
│   ├── research/
│   │   ├── research.md
│   │   └── sources.md
│   │
│   ├── script/
│   │   └── script.md
│   │
│   ├── audio/
│   ├── scenes/
│   ├── rendered/
│   └── logs/
│
├── output/
│   └── .gitkeep
│
└── examples/
    └── sample-request.md
```

### 各ディレクトリ・ファイルの役割

#### `AGENTS.dev.md`

UtsuroClip自体をCodexで開発するときのルールを定義する。

#### `AGENTS.user.md`

UtsuroClipを利用して動画を生成するときのルールを定義する。

調査、台本作成、動画生成に関するCodexの基本的な作業ルールを記載する。


#### `setup.sh`

ツールの開発/利用のセットアップを実行するスクリプト。

開発/利用時のAGENTSファイルやCodexの設定ファイルを適切に配置する。

通常モードでは `AGENTS.user.md` を `AGENTS.md` へ、`.codex.user/` を `.codex/` へ、`.agents.user/` を `.agents/` へコピーする。開発モードでは `AGENTS.dev.md` と `.codex.dev/` を配置する。同名ファイルは上書きされるため、利用者は必要に応じて独自設定を退避する。

```bash
# Development Mode
bash setup.sh --dev

# User Mode
bash setup.sh
```

#### `docs/`

UtsuroClipの設計書など、プロジェクトのドキュメントを格納する。

本設計書は以下に格納する。

```text
docs/design.md
```

#### `.codex.dev/`

開発者向けのCodex設定ファイルを格納する

#### `.agents.user/skills/`

Codexが動画構成や演出を考える際に参照するSkillを格納する。

UtsuroClip固有の動画制作ノウハウは以下に定義する。

```text
.agents.user/skills/video-generation/SKILL.md
```

通常モードのセットアップ時に `.agents/skills/video-generation/SKILL.md` として配置する。

#### `prompts/`

UtsuroClipからCodexへ渡す、各工程の具体的な作業指示を格納する。

```text
research.md
→ 情報収集・事実確認

write-script.md
→ 調査結果をもとに台本作成

generate-video.md
→ 台本から動画生成
```

#### `src/utsuroclip/`

UtsuroClip本体のCLI処理とCodex CLI呼び出し処理を格納する。

#### `tools/`

VOICEVOX、Manim、FFmpegを操作する処理を格納する。

#### `input/`

ユーザーが作りたい動画の概要を記載したMarkdownファイルを格納する。

#### `work/research/`

Codexによる調査結果と、その情報源を格納する。

#### `work/script/`

調査結果をもとにCodexが生成した動画台本を格納する。

#### `work/audio/`

VOICEVOXで生成したナレーション音声を格納する。

#### `work/scenes/`

Codexが生成したManimコードを格納する。

#### `work/rendered/`

Manimでレンダリングしたシーン動画を格納する。

#### `work/logs/`

動画生成中のログを格納する。

#### `output/`

完成した動画を格納する。

#### `examples/`

動画概要のサンプルを格納する。

---

## 7. AGENTSファイルの使い分け

UtsuroClipでは、Codexを以下の2つのモードで利用する。

### Development Mode

UtsuroClip自体を開発・変更するときに使用する。

```text
AGENTS.dev.md
        ↓
AGENTS.md
        ↓
Codex
        ↓
UtsuroClipの実装・修正
```

### User Mode

UtsuroClipを利用して動画を生成するときに使用する。

```text
AGENTS.user.md
        ↓
AGENTS.md
        ↓
Codex
        ↓
調査
        ↓
台本作成
        ↓
動画生成
```

### AGENTS.mdの切り替え

`AGENTS.md` 自体に両方のルールを持たせず、現在使用するモードのAGENTSファイルをコピーして使用する。

`setup.sh` スクリプトの処理でAGENTSファイルをコピーして配置する。

```bash
# Development Mode
bash setup.sh --dev

# User Mode
bash setup.sh
```

---

## 8. Codex向け構成

UtsuroClipでは、Codexへの指示を以下の3種類に分離する。

```text
AGENTS.md
→ Codexが現在のモードで守る基本ルール

.agents.user/skills/
→ 動画制作に関する再利用可能な知識・ノウハウ

prompts/
→ UtsuroClipがCodexに実行させる具体的なタスク
```

これにより、動画制作の細かなノウハウをAGENTSファイルへ大量に記載せず、役割ごとに管理する。

---

## 9. 各コンポーネント

### UtsuroClip CLI

`src/utsuroclip/cli.py`

ユーザーからのCLI操作を受け付ける。

想定コマンド：

```bash
utsuroclip generate input/request.md
```

主な役割：

* 動画概要ファイルを受け取る
* User ModeのAGENTS設定を使用する
* Codex CLIを起動する
* 調査・台本作成・動画生成処理を開始する
* 実行結果をユーザーへ表示する
* 各工程の標準出力・標準エラー・最終メッセージを `work/logs/` に保存する
* 正常終了前に `output/video.mp4` が生成されていることを確認する

---

### Codex Runner

`src/utsuroclip/codex.py`

Codex CLIを非対話モードで起動する。

```text
UtsuroClip
↓
codex exec
↓
Codex
↓
Research
↓
Script
↓
Video
```

CodexはAGENTS、Prompt、Skill、動画概要、中間生成物を参照し、動画生成に必要な処理を進める。

CLIは `codex exec --sandbox workspace-write` を使い、Research、Script、Video Generationをそれぞれ独立して順番に起動する。各工程は前工程がファイルへ保存した成果物を読み込む。いずれかの工程が失敗した場合、後続工程は実行しない。

映像生成工程でローカルのVOICEVOX Engineを呼び出せるよう、CLIはVideo GenerationのCodex実行時だけ `workspace-write` のネットワークアクセスを有効にし、Codexのネットワークプロキシで `127.0.0.1` だけを許可する。公開インターネットおよび他のローカル宛先は許可しない。既定のVOICEVOX URLは `http://127.0.0.1:50021` とする。

---

### Research Prompt

`prompts/research.md`

動画概要をもとに、台本作成に必要な情報を調査するためのプロンプト。

主な処理：

* 動画テーマを解析する
* 動画内で説明するために必要な事実を特定する
* Web検索などから情報を収集する
* 可能な限り一次情報や信頼性の高い情報源を優先する
* 重要な情報を必要に応じて複数の情報源で確認する
* 確認できた情報と不確実な情報を区別する
* 調査結果を `research.md` に保存する
* 使用した情報源を `sources.md` に保存する

---

### Script Prompt

`prompts/write-script.md`

調査結果をもとに動画台本を作成する。

```text
request.md
+
research.md
+
sources.md
        ↓
Codex
        ↓
work/script/script.md
```

台本では、調査によって確認された情報を基本として使用する。

動画尺を考慮し、最大約3分に収まる内容へ整理する。

---

### Video Generation Prompt

`prompts/generate-video.md`

完成した台本から動画を生成する処理を定義する。

主な内容：

* `work/script/script.md` を読み込む
* `.agents/skills/video-generation/SKILL.md` を参照する
* 台本をシーンに分割する
* 各シーンの視覚表現を設計する
* Manimコードを生成する
* VOICEVOX、Manim、FFmpeg用ツールを利用する
* 最終動画を生成する

---

### Video Generation Skill

`.agents/skills/video-generation/SKILL.md`

Codexが動画を制作する際の演出方針やノウハウを定義する。

特に以下を重視する。

* ナレーション全文をそのまま字幕として表示するだけにしない
* 説明内容を可能な限り図や動きに置き換える
* テキスト、図形、線、矢印、数式などを組み合わせる
* 情報を一度に大量表示せず、説明に合わせて段階的に見せる
* 既存の要素を移動・変形させながら次の説明へつなげる
* 不必要な画面切り替えを避ける
* 滑らかで連続性のあるアニメーションを優先する
* 視聴者の視線を自然に次の情報へ誘導する
* 派手さよりも、内容の理解につながる演出を優先する

---

### VOICEVOX Tool

`tools/voicevox.py`

VOICEVOX Engine APIを呼び出し、各シーンのナレーション音声を生成する。

`/audio_query` と `/synthesis` を使用し、既定では `http://127.0.0.1:50021` のローカルEngineへ接続する。話者IDとEngine URLはCLI引数で変更できる。

```text
ナレーション文章
↓
VOICEVOX Engine
↓
work/audio/scene_001.wav
```

---

### Manim Renderer

`tools/manim_renderer.py`

Codexが生成したManimコードを実行し、各シーンの映像を生成する。

レンダリング後、Manimの一時メディアディレクトリから生成したMP4を指定された出力パスへ配置する。

```text
work/scenes/scene_001.py
↓
Manim
↓
work/rendered/scene_001.mp4
```

---

### FFmpeg Tool

`tools/ffmpeg.py`

Manimで生成した映像とVOICEVOX音声を結合し、複数のシーンを1本の動画としてまとめる。

`mux` サブコマンドでシーン映像と音声を結合し、`concat` サブコマンドで結合済みシーンを順番に連結する。

```text
scene_001.mp4 + scene_001.wav
scene_002.mp4 + scene_002.wav
scene_003.mp4 + scene_003.wav
              ↓
            FFmpeg
              ↓
       output/video.mp4
```

---

## 10. 調査結果・台本・中間生成物

動画生成では、各工程の成果物を保存する。

```text
work/
├── research/
│   ├── research.md
│   └── sources.md
│
├── script/
│   └── script.md
│
├── audio/
│   ├── scene_001.wav
│   └── scene_002.wav
│
├── scenes/
│   ├── scene_001.py
│   └── scene_002.py
│
├── rendered/
│   ├── scene_001.mp4
│   └── scene_002.mp4
│
└── logs/
```

### research.md

動画で使用するために調査した内容を保存する。

以下のような情報を含める。

* 確認できた事実
* 動画内で説明すべきポイント
* 注意が必要な情報
* 不確実または議論のある情報

### sources.md

調査時に使用した情報源を保存する。

可能な範囲で以下を残す。

* 情報源名
* URL
* 参照した内容

### script.md

`research.md` と `sources.md` をもとにCodexが作成した動画台本を保存する。

原則として、調査によって確認できていない事実を台本へ追加しない。

---

UtsuroClipでは、完成したMP4だけを生成するのではなく、

```text
動画概要
↓
調査
↓
台本
↓
音声
↓
Manimコード
↓
シーン映像
↓
完成動画
```

という制作過程そのものを中間成果物として保持する。

これにより、Codexから調査内容、台本、特定シーンなどを確認・修正しながら動画を制作できる環境を目指す。
