"""命令行演示入口（阶段1起逐步扩展子命令）。"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 保证从 VoiceAssistant 目录运行时能 import ai
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ai import audio_io, pipeline, speech_to_text, text_process, text_to_speech
from ai.text_process import ProcessMode


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def cmd_record(args: argparse.Namespace) -> int:
    try:
        if args.seconds is not None:
            path = audio_io.record_for_seconds(args.seconds)
        else:
            print("按 Enter 结束录音…")
            audio_io.start_recording()
            input()
            path = audio_io.stop_recording()
        print(f"已保存: {path}")
        if audio_io.is_silent_wav(path):
            print(f"提示: {audio_io.NO_SPEECH_HINT}")
            if args.play:
                print("录音为静音，已跳过播放。")
            return 0
        if args.play:
            print("正在播放…")
            audio_io.play_wav(path)
        return 0
    except audio_io.AudioIOError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def cmd_transcribe(args: argparse.Namespace) -> int:
    try:
        if args.preload:
            speech_to_text.preload_whisper(args.model)
            print(f"模型 '{args.model}' 已预加载")
            if not args.path:
                return 0
        if not args.path:
            print("请提供 --path 指定 wav 文件", file=sys.stderr)
            return 1
        text = speech_to_text.transcribe(args.path, language=args.lang, model_name=args.model)
        print("识别结果:")
        print(text)
        return 0
    except speech_to_text.SpeechToTextError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def cmd_ask(args: argparse.Namespace) -> int:
    try:
        if args.preload:
            text_process.preload_nlp()
        reply = text_process.process_text(args.text, mode=args.mode)
        print("AI 回复:")
        print(reply)
        if args.speak:
            text_to_speech.speak(reply)
        return 0
    except text_process.TextProcessError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def cmd_speak(args: argparse.Namespace) -> int:
    try:
        text_to_speech.speak(args.text)
        return 0
    except text_to_speech.TextToSpeechError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def cmd_session(args: argparse.Namespace) -> int:
    try:
        if args.preload:
            pipeline.preload_all(args.whisper_model)
        if args.text:
            reply = text_process.process_text(args.text, mode=args.mode)
            print("识别文本(手动):")
            print(args.text)
            print("AI 回复:")
            print(reply)
            if not args.no_speak:
                text_to_speech.speak(reply)
            return 0

        seconds = args.seconds if args.seconds > 0 else 5.0
        print(f"开始录音 {seconds} 秒，请对着麦克风说话…")
        out = pipeline.run_full_voice_session(
            mode=args.mode,
            record_seconds=seconds,
            speak_reply=not args.no_speak,
        )
        if out.success:
            print("识别文本:")
            print(out.recognized_text)
            print("AI 回复:")
            print(out.reply_text)
            print(f"录音文件: {out.recording_path}")
            return 0
        print(f"错误: {out.error_message}", file=sys.stderr)
        if out.recognized_text:
            print("识别文本:", out.recognized_text)
        if out.reply_text:
            print("AI 回复:", out.reply_text)
        return 1
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def cmd_play(args: argparse.Namespace) -> int:
    try:
        audio_io.play_wav(args.path)
        return 0
    except audio_io.AudioIOError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VoiceAssistant AI 模块 CLI")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_rec = sub.add_parser("record", help="录音并保存 wav")
    p_rec.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="固定录音秒数；省略则按 Enter 结束",
    )
    p_rec.add_argument("--play", action="store_true", help="录完后立即播放")
    p_rec.set_defaults(func=cmd_record)

    p_play = sub.add_parser("play", help="播放 wav")
    p_play.add_argument("--path", required=True, help="wav 文件路径")
    p_play.set_defaults(func=cmd_play)

    p_tr = sub.add_parser("transcribe", help="Whisper 语音转文字")
    p_tr.add_argument("--path", default=None, help="wav 文件路径")
    p_tr.add_argument("--model", default="base", help="Whisper 模型名 tiny/base/small…")
    p_tr.add_argument("--lang", default="zh", help="语言代码")
    p_tr.add_argument("--preload", action="store_true", help="仅预加载模型")
    p_tr.set_defaults(func=cmd_transcribe)

    p_ask = sub.add_parser("ask", help="文本智能处理")
    p_ask.add_argument("--text", required=True)
    p_ask.add_argument(
        "--mode",
        default=ProcessMode.QA,
        choices=[ProcessMode.QA, ProcessMode.SUMMARY, ProcessMode.KEYWORDS, ProcessMode.STUDY_TIP],
    )
    p_ask.add_argument("--speak", action="store_true", help="播报回复")
    p_ask.add_argument("--preload", action="store_true")
    p_ask.set_defaults(func=cmd_ask)

    p_sp = sub.add_parser("speak", help="TTS 播报")
    p_sp.add_argument("--text", required=True)
    p_sp.set_defaults(func=cmd_speak)

    p_sess = sub.add_parser("session", help="录音→识别→处理→播报")
    p_sess.add_argument("--seconds", type=float, default=5.0)
    p_sess.add_argument("--mode", default=ProcessMode.QA, choices=[
        ProcessMode.QA, ProcessMode.SUMMARY, ProcessMode.KEYWORDS, ProcessMode.STUDY_TIP,
    ])
    p_sess.add_argument("--text", default=None, help="跳过录音识别，直接处理该文本")
    p_sess.add_argument("--no-speak", action="store_true")
    p_sess.add_argument("--preload", action="store_true")
    p_sess.add_argument("--whisper-model", default=None)
    p_sess.set_defaults(func=cmd_session)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
