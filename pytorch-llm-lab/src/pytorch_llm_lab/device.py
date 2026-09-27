"""Report the compute device that PyTorch can use."""

import torch


def main() -> None:
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("Device: CPU")


if __name__ == "__main__":
    main()

