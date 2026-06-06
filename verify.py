import argparse

from app import verify_from_camera


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a face offline from webcam.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index.")
    parser.add_argument("--skip-liveness", action="store_true", help="Disable liveness challenge.")
    parser.add_argument(
        "--allow-passive-only",
        action="store_true",
        help="Allow passive liveness to pass without a mandatory active challenge.",
    )
    args = parser.parse_args()

    result = verify_from_camera(
        camera_index=args.camera,
        require_liveness=not args.skip_liveness,
        require_active_challenge=not args.allow_passive_only,
    )
    decision = "Verified" if result.matched else "Not Verified"
    print(f"Face Match: {result.percentage:.2f}%")
    print(f"Decision: {decision}")
    print(f"Recognized Name: {result.name or 'No match'}")
    print(f"Confidence Band: {result.confidence_band}")
    print(f"Risk Level: {result.risk_level}")
    print(f"Challenge Required: {'Yes' if result.challenge_required else 'No'}")
    print(f"Required Threshold: {result.threshold * 100:.2f}%")
    print(f"Liveness Passed: {'Yes' if result.liveness_passed else 'No'}")
    print(f"Backend: {result.backend}")
    print(f"Message: {result.message}")
    print(f"Queued Event ID: {result.event_id or 'Not queued'}")


if __name__ == "__main__":
    main()
