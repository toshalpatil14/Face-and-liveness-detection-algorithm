import argparse

from app import register_from_camera


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a face offline from webcam.")
    parser.add_argument("--name", required=True, help="Person name to store.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index.")
    args = parser.parse_args()

    record = register_from_camera(name=args.name, camera_index=args.camera)
    print(f"Registered {record.name} using backend={record.backend} id={record.person_id}")


if __name__ == "__main__":
    main()
