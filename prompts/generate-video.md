# 映像生成工程

`work/script/script.md` と `.agents/skills/video-generation/SKILL.md` を読み、台本に対応した完成動画を作成してください。

1. 台本をシーンに分け、各シーンの視覚表現を簡潔に設計する。
2. 各シーンのナレーションを `python tools/voicevox.py --speaker <実行コンテキストで指定された話者>` で `work/audio/scene_XXX.wav` に生成する。話者は実行コンテキストで指定されたものを必ず使用する。
3. 各シーンの縦型9:16 Manimコードを `work/scenes/scene_XXX.py` に作成する。対応する `Scene` クラスを `python tools/manim_renderer.py` で `work/rendered/scene_XXX.mp4` にレンダリングする。
4. `python tools/ffmpeg.py mux` で各シーンの映像と音声を結合し、`python tools/ffmpeg.py concat` でシーン順に連結して `output/video.mp4` を生成する。
5. 出力ファイルが存在することを確認し、シーン数と最終ファイルの場所を報告する。

生成前に、VOICEVOX Engine、Manim、FFmpegが利用できるか確認してください。未導入または実行不能なら、どの依存ツールが不足しているかを明確に報告し、存在しない動画を完成としないでください。
