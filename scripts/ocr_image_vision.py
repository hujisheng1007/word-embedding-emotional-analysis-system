"""Recognize one image with macOS Vision. Run in a venv with pyobjc-framework-Vision."""
from __future__ import annotations

import sys
from pathlib import Path

import Foundation
import Vision


def recognize(path: Path) -> list[str]:
    request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(None)
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(["zh-Hans", "en-US"])
    request.setUsesLanguageCorrection_(True)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(
        Foundation.NSURL.fileURLWithPath_(str(path)), {}
    )
    ok, error = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(str(error))
    observations = sorted(
        request.results() or [],
        key=lambda item: (-item.boundingBox().origin.y, item.boundingBox().origin.x),
    )
    lines: list[str] = []
    for observation in observations:
        candidates = observation.topCandidates_(1)
        if candidates:
            lines.append(str(candidates[0].string()))
    return lines


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：ocr_image_vision.py 图片路径")
    print("\n".join(recognize(Path(sys.argv[1]))))
