"""Main CLI for RH56 Rock-Paper-Scissors demo."""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# Ensure demo package is importable when run as module.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from rosclaw_rps.game_engine import GameEngine, RPS_CHOICES
from rosclaw_rps.gesture_schema import GestureConfig, GesturePrediction
from rosclaw_rps.hand.gesture_executor import GestureExecutor, GestureVerifier
from rosclaw_rps.hand.rh56_controller import build_hand_controller, MockHandController
from rosclaw_rps.vision.camera_source import build_camera_source
from rosclaw_rps.vision.hand_gesture_recognizer import build_recognizer, KeyboardRecognizer
from rosclaw_rps.vision.majority_vote import MajorityVoteBuffer
from rosclaw_rps.vision.recognition_worker import RecognitionWorker
from rosclaw_rps.logging.round_logger import RoundLogger
from rosclaw_rps.ui.simple_opencv_ui import SimpleOpenCVUI


def load_configs(config_dir: Path) -> tuple:
    gestures_path = config_dir / "rh56_gestures.yaml"
    demo_path = config_dir / "rps_demo.yaml"
    with open(gestures_path, "r", encoding="utf-8") as f:
        gestures_raw = yaml.safe_load(f)
    with open(demo_path, "r", encoding="utf-8") as f:
        demo_raw = yaml.safe_load(f)

    gestures = {
        name: GestureConfig.from_dict(name, data)
        for name, data in gestures_raw["gestures"].items()
    }
    return gestures, demo_raw


def _wait_for_start(auto: bool) -> bool:
    if auto:
        return True
    try:
        input("Press Enter to start next round (Ctrl-C to quit)...")
        return True
    except EOFError:
        return False
    except KeyboardInterrupt:
        return False


def run_mock(gestures: Dict[str, GestureConfig], demo_config: dict) -> None:
    hand = MockHandController()
    executor = GestureExecutor(hand, gestures, GestureVerifier())
    engine = GameEngine()
    logger = RoundLogger(
        Path(demo_config["logging"]["root_dir"]) / f"mock_{uuid.uuid4().hex[:8]}",
        save_frames=False,
        save_telemetry=True,
    )
    recognizer = KeyboardRecognizer()
    rounds_total = int(demo_config["demo"]["rounds"])
    auto = bool(demo_config["demo"].get("auto", False))

    print("=== RH56 RPS Mock Mode ===")
    print("Controls: r=rock, p=paper, s=scissors, Enter=unknown, Ctrl-C=quit")
    executor.execute("ready")

    for i in range(rounds_total):
        round_id = engine.new_round_id()
        if not _wait_for_start(auto):
            break

        commit = engine.commit_robot_choice(round_id)
        print(f"\n{round_id} | Robot committed (hash {commit.commit_hash[:8]}...)")

        pred = recognizer.predict(None)  # keyboard doesn't need frame
        print(f"Human predicted: {pred.label} (conf={pred.confidence})")

        robot_result = executor.execute(commit.robot_choice)
        print(f"Robot gesture: {commit.robot_choice} verified={robot_result.verified}")
        if robot_result.failure_reason:
            print(f"  failure: {robot_result.failure_reason}")

        round_obj = engine.resolve_round(round_id, commit, pred, robot_result)
        result_gesture_name = engine.result_gesture_map.get(round_obj.result, "error")
        executor.execute(result_gesture_name)

        logger.log_round(round_obj)
        print(f"Result: {round_obj.result} -> {result_gesture_name}")

    executor.execute("error")  # safe open
    summary = engine.summary(logger.rounds)
    logger.write_summary(summary)
    print("\nSummary:", summary)
    print(f"Run log: {logger.current_run_dir}")


def run_camera_only(gestures: Dict[str, GestureConfig], demo_config: dict) -> None:
    camera = build_camera_source(demo_config["camera"])
    recognizer = build_recognizer(demo_config["camera"])
    ui = SimpleOpenCVUI()
    vote = MajorityVoteBuffer(
        window_size=int(demo_config["capture"]["vote_window_size"]),
        min_confidence=float(demo_config["capture"]["min_confidence"]),
        majority_ratio=float(demo_config["capture"]["majority_ratio"]),
    )
    hand = MockHandController()
    executor = GestureExecutor(hand, gestures, GestureVerifier())
    countdown = demo_config["countdown"]["labels"]
    step_s = float(demo_config["countdown"]["step_s"])

    print("=== RH56 RPS Camera-Only Mode ===")
    print("Show rock/paper/scissors to the camera. Press 'q' to quit.")

    executor.execute("ready")
    capturing = False
    capture_deadline = 0.0

    while True:
        frame = camera.read()
        if frame is None:
            time.sleep(0.05)
            continue

        pred = recognizer.predict(frame)
        canvas = ui.render(frame, countdown_label="")
        ui.show(canvas)
        key = ui.wait_key(1)
        if key == ord("q"):
            break
        if key == ord(" ") and not capturing:
            capturing = True
            vote.reset()
            print("Countdown started...")
            for label in countdown:
                canvas = ui.render(frame, countdown_label=label)
                ui.show(canvas)
                time.sleep(step_s)
            capture_deadline = time.time() + float(demo_config["capture"]["window_s"])

        if capturing:
            vote.update(pred)
            if time.time() >= capture_deadline:
                final = vote.final()
                print(f"Captured human gesture: {final.label} (conf={final.confidence})")
                capturing = False

    executor.execute("error")
    camera.release()
    ui.close()


def run_hand_test(gestures: Dict[str, GestureConfig], demo_config: dict) -> None:
    hand = build_hand_controller(demo_config["hand"])
    executor = GestureExecutor(hand, gestures, GestureVerifier())
    sequence = ["ready", "rock", "paper", "scissors", "win", "lose", "draw", "error"]
    print("=== RH56 RPS Hand-Test Mode ===")
    print(f"Sequence: {' -> '.join(sequence)}")
    print("Watch the hand; press Ctrl-C to stop.")
    try:
        for name in sequence:
            print(f"\nExecuting gesture: {name}")
            result = executor.execute(name)
            print(f"  verified={result.verified}, duration={result.duration_s:.2f}s")
            if result.failure_reason:
                print(f"  failure: {result.failure_reason}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nSafe opening hand...")
        executor.execute("error")
        hand.close()


def run_full(gestures: Dict[str, GestureConfig], demo_config: dict, headless: bool = False) -> None:
    hand = build_hand_controller(demo_config["hand"])
    executor = GestureExecutor(hand, gestures, GestureVerifier())
    engine = GameEngine()
    camera = build_camera_source(demo_config["camera"])
    recognizer = build_recognizer(demo_config["camera"])
    vote = MajorityVoteBuffer(
        window_size=int(demo_config["capture"]["vote_window_size"]),
        min_confidence=float(demo_config["capture"]["min_confidence"]),
        majority_ratio=float(demo_config["capture"]["majority_ratio"]),
    )
    worker = RecognitionWorker(camera, recognizer, vote, process_every_n=2)
    worker.start()

    ui = None if headless else SimpleOpenCVUI()
    logger = RoundLogger(
        Path(demo_config["logging"]["root_dir"]) / f"full_{uuid.uuid4().hex[:8]}",
        save_frames=demo_config["logging"].get("save_frames", True) and not headless,
        save_telemetry=demo_config["logging"].get("save_telemetry", True),
    )
    countdown_labels = demo_config["countdown"]["labels"]
    countdown_gestures = demo_config["countdown"].get("gestures", [])
    step_s = float(demo_config["countdown"]["step_s"])
    rounds_total = int(demo_config["demo"]["rounds"])
    auto = bool(demo_config["demo"].get("auto", False)) or headless

    print("=== RH56 剪刀石头布 完整模式 ===")
    if headless:
        print("HEADLESS 模式：无 OpenCV 窗口，按提示出手势")
    else:
        print("空格=开始下一轮， q=退出， o=安全张开")
    executor.execute("ready")

    def render_show(frame, waiting=False, **kwargs):
        if ui is None:
            return
        canvas = ui.render(frame, waiting_for_start=waiting, **kwargs)
        ui.show(canvas)

    def wait_or_sleep(delay_ms: int) -> int:
        if ui is None:
            time.sleep(delay_ms / 1000.0)
            return 0xFF
        return ui.wait_key(delay_ms)

    def latest_state():
        frame, pred = worker.get_latest()
        return frame, pred.label if pred else "unknown"

    # Run hand movements in a background thread so the UI feed never freezes.
    _exec_result: List[Optional[object]] = [None]
    _exec_thread: List[Optional[threading.Thread]] = [None]
    _exec_lock = threading.Lock()

    def run_gesture_async(name: str) -> None:
        if _exec_thread[0] is not None and _exec_thread[0].is_alive():
            _exec_thread[0].join()

        def target():
            res = executor.execute(name)
            with _exec_lock:
                _exec_result[0] = res

        t = threading.Thread(target=target)
        t.start()
        _exec_thread[0] = t

    def gesture_async_done() -> bool:
        return _exec_thread[0] is None or not _exec_thread[0].is_alive()

    def last_gesture_result():
        with _exec_lock:
            return _exec_result[0]

    def wait_gesture_async(min_wait_s: float = 0.0) -> Optional[object]:
        deadline = time.time() + min_wait_s
        while True:
            if gesture_async_done() and time.time() >= deadline:
                break
            frame, human_label = latest_state()
            render_show(frame, round_id=round_id, robot_committed=True, human_label=human_label)
            if wait_or_sleep(20) == ord("q"):
                raise KeyboardInterrupt
        if _exec_thread[0] is not None:
            _exec_thread[0].join()
        return last_gesture_result()

    try:
        for _ in range(rounds_total):
            round_id = engine.new_round_id()
            frame, human_label = latest_state()
            render_show(frame, round_id=round_id, robot_committed=False, waiting=True, human_label=human_label)

            # Wait for start
            started = False
            while not started:
                frame, human_label = latest_state()
                render_show(frame, round_id=round_id, robot_committed=False, waiting=True, human_label=human_label)
                key = wait_or_sleep(1)
                if key == ord("q"):
                    raise KeyboardInterrupt
                if key == ord(" ") or auto:
                    started = True
                if key == ord("o"):
                    executor.execute("error")

            # Commit robot choice BEFORE human capture.
            commit = engine.commit_robot_choice(round_id)
            print(f"{round_id} | Robot committed: {commit.robot_choice} (hash {commit.commit_hash[:8]})")

            # Hand-led countdown: 3, 2, 1, OK.  The recognition worker keeps
            # capturing the human gesture in the background the whole time.
            worker.reset_vote()
            for label, gesture_name in zip(countdown_labels, countdown_gestures):
                run_gesture_async(gesture_name)
                robot_result = wait_gesture_async(min_wait_s=step_s)
                print(
                    f"  Hand countdown: {label} ({gesture_name}) "
                    f"verified={robot_result.verified if robot_result else False}"
                )

            # Reveal: robot executes its committed choice.
            run_gesture_async(commit.robot_choice)
            robot_result = wait_gesture_async(min_wait_s=0.0)
            print(f"Robot gesture {commit.robot_choice}: verified={robot_result.verified if robot_result else False}")

            human_pred = worker.final_vote()
            print(f"Human: {human_pred.label} (conf={human_pred.confidence})")

            round_obj = engine.resolve_round(round_id, commit, human_pred, robot_result)
            print(f"结果：{round_obj.result}")

            # Grab one last frame for the log.
            capture_frame, _ = latest_state()
            logger.log_round(round_obj, capture_frame=capture_frame)

            # Result display: keep the hand at the ready (OK) pose and only show text.
            for _ in range(3):
                frame, human_label = latest_state()
                render_show(
                    frame,
                    round_id=round_id,
                    robot_committed=True,
                    robot_choice=commit.robot_choice,
                    human_label=human_pred.label,
                    result=round_obj.result,
                    bodysense="verified" if robot_result.verified else robot_result.failure_reason,
                )
                if wait_or_sleep(500) == ord("q"):
                    raise KeyboardInterrupt

            # Return to ready (OK) so the user sees a clear "ready for next round" pose.
            run_gesture_async("ready")
            wait_gesture_async(min_wait_s=0.0)
    except KeyboardInterrupt:
        pass
    finally:
        if _exec_thread[0] is not None and _exec_thread[0].is_alive():
            _exec_thread[0].join()
        executor.execute("error")
        summary = engine.summary(logger.rounds)
        logger.write_summary(summary)
        worker.stop()
        camera.release()
        if ui is not None:
            ui.close()
        hand.close()
        print("\nSummary:", summary)
        print(f"Run log: {logger.current_run_dir}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="RH56 Rock-Paper-Scissors Demo")
    parser.add_argument(
        "--mode",
        choices=["mock", "camera-only", "hand-test", "full"],
        default="mock",
        help="Demo mode",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "configs",
        help="Directory containing rh56_gestures.yaml and rps_demo.yaml",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Override number of rounds",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-advance rounds in mock/full mode",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without OpenCV UI (useful over SSH or for automation)",
    )
    args = parser.parse_args(argv)

    gestures, demo_config = load_configs(args.config_dir)
    demo_config["demo"]["mode"] = args.mode
    if args.rounds is not None:
        demo_config["demo"]["rounds"] = args.rounds
    if args.auto:
        demo_config["demo"]["auto"] = True

    mode = args.mode
    if mode == "mock":
        run_mock(gestures, demo_config)
    elif mode == "camera-only":
        run_camera_only(gestures, demo_config)
    elif mode == "hand-test":
        run_hand_test(gestures, demo_config)
    elif mode == "full":
        run_full(gestures, demo_config, headless=args.headless)
    else:
        parser.error(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
