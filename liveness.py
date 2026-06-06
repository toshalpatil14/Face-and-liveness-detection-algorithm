import argparse

from app import run_liveness_check


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone offline liveness check.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index.")
    parser.add_argument("--timeout", type=int, default=12, help="Timeout in seconds.")
    parser.add_argument(
        "--allow-passive-only",
        action="store_true",
        help="Allow passive liveness to pass without a mandatory active challenge.",
    )
    args = parser.parse_args()

    passed = run_liveness_check(
        camera_index=args.camera,
        timeout_seconds=args.timeout,
        require_active_challenge=not args.allow_passive_only,
    )
    print(f"Liveness passed: {passed}")


if __name__ == "__main__":
    main()
