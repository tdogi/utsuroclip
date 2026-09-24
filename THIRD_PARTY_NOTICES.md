# Third-Party Notices

UtsuroClip invokes the following tools, which users install separately. This
repository does not include their executables, libraries, or voice assets. When
obtaining, configuring, modifying, or distributing those tools (or generated
content), comply with their respective current terms and licenses.

| Tool | How UtsuroClip uses it | License / terms |
| --- | --- | --- |
| [Codex CLI](https://github.com/openai/codex) | Runs the separately installed `codex` executable. | [Apache-2.0](https://github.com/openai/codex/blob/main/docs/license.md) |
| [VOICEVOX Engine](https://github.com/VOICEVOX/voicevox_engine) | Sends requests to a separately running local HTTP API. | [LGPL-3.0 or separately obtained alternative license](https://github.com/VOICEVOX/voicevox_engine/blob/master/LICENSE) |
| [Manim Community Edition](https://github.com/ManimCommunity/manim) | Runs the separately installed `manim` executable. | [MIT License](https://github.com/ManimCommunity/manim/blob/main/LICENSE.community) |
| [FFmpeg](https://ffmpeg.org/) | Runs the separately installed `ffmpeg` executable. | [LGPL-2.1-or-later by default; GPL-2.0-or-later if GPL components are enabled](https://ffmpeg.org/legal.html) |

## VOICEVOX generated audio

The selected VOICEVOX voice library has its own usage terms. For the speakers
currently available in UtsuroClip, include the applicable credit in the
published video or its description:

- `VOICEVOX:ずんだもん`
- `VOICEVOX:四国めたん`
- `VOICEVOX:春日部つむぎ`

See the [VOICEVOX voice-library terms](https://github.com/VOICEVOX/voicevox_resource/blob/main/core/README.md) and each speaker's linked terms for the complete, current conditions.

## Video fonts

Commercial mode uses separately installed fonts. It restricts Manim text to
`Noto Sans CJK JP`, `Noto Sans Mono CJK JP`, `Noto Serif CJK JP`, and
`Noto Sans Math`. The Noto CJK fonts are licensed under the
[SIL Open Font License 1.1 (Sans and Mono)](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE)
or the [SIL Open Font License 1.1 (Serif)](https://github.com/notofonts/noto-cjk/blob/main/Serif/LICENSE).
Noto Sans Math is licensed under the
[SIL Open Font License 1.1](https://github.com/notofonts/math/blob/main/OFL.txt).
The font authors permit commercial use, including video titling, without
requiring a credit in the video. Redistribution of font files has separate
conditions; consult the [OFL FAQ](https://openfontlicense.org/ofl-faq/).

**Commercial mode does not check the rights or terms for images, video, audio,
BGM, or other material supplied by the user. The user must check and comply
with the conditions for commercial use, editing, publication, and credits.**

## UtsuroClip

UtsuroClip's own source code and documentation are available under the
[MIT License](LICENSE). This license does not replace the terms for any
separately installed third-party tool or generated voice content.
