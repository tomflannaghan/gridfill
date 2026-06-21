#!/usr/bin/env python3
"""Train an EMNIST Letters CNN and export to ONNX.

Requires the ``[recognize]`` extra (torch, torchvision)::

    uv pip install -e ".[recognize]"
    python scripts/train_emnist.py --output models/emnist_cnn.onnx

The exported ONNX model is loaded at inference time by ``CnnLetterClassifier``
via ``cv2.dnn`` — no torch dependency at runtime.
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    try:
        import torch
        import torch.nn as nn
        from PIL import Image
        from torch.utils.data import DataLoader
        from torchvision import datasets, transforms
    except ImportError:
        sys.exit(
            "Training requires torch and torchvision.\n"
            "Install with: uv pip install -e '.[recognize]'"
        )

    parser = argparse.ArgumentParser(description="Train EMNIST Letters CNN → ONNX")
    parser.add_argument("--output", default="models/emnist_cnn.onnx", help="ONNX output path")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # --- Model -----------------------------------------------------------

    class EmnistCNN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(1, 32, 3, padding=1),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
            )
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(64 * 7 * 7, 128),
                nn.ReLU(inplace=True),
                nn.Dropout(0.5),
                nn.Linear(128, 26),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.classifier(self.features(x))

    # --- Data ------------------------------------------------------------

    # EMNIST images are stored transposed; fix during loading.
    train_transform = transforms.Compose(
        [
            lambda img: img.transpose(Image.Transpose.TRANSPOSE),
            transforms.RandomAffine(degrees=10, translate=(0.1, 0.1), scale=(0.9, 1.1)),
            transforms.ToTensor(),
        ]
    )
    test_transform = transforms.Compose(
        [
            lambda img: img.transpose(Image.Transpose.TRANSPOSE),
            transforms.ToTensor(),
        ]
    )

    # Labels are 1-indexed (1=A … 26=Z); shift to 0-indexed for CrossEntropyLoss.
    def target_transform(y: int) -> int:
        return y - 1

    train_set = datasets.EMNIST(
        root="data",
        split="letters",
        train=True,
        download=True,
        transform=train_transform,
        target_transform=target_transform,
    )
    test_set = datasets.EMNIST(
        root="data",
        split="letters",
        train=False,
        download=True,
        transform=test_transform,
        target_transform=target_transform,
    )
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_set, batch_size=args.batch_size, num_workers=2)

    print(f"Train: {len(train_set)} samples, Test: {len(test_set)} samples")

    # --- Train -----------------------------------------------------------

    model = EmnistCNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for images, targets in train_loader:
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad()
            loss = criterion(model(images), targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * images.size(0)

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for images, targets in test_loader:
                images, targets = images.to(device), targets.to(device)
                correct += (model(images).argmax(1) == targets).sum().item()
                total += targets.size(0)
        acc = correct / total
        avg_loss = total_loss / len(train_set)
        print(f"Epoch {epoch:2d}/{args.epochs}  loss={avg_loss:.4f}  acc={acc:.4f}")

    # --- Export to ONNX --------------------------------------------------

    model.eval()
    model.cpu()
    dummy = torch.randn(1, 1, 28, 28)
    torch.onnx.export(
        model,
        dummy,
        args.output,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    )
    print(f"Saved ONNX model to {args.output}")


if __name__ == "__main__":
    main()
