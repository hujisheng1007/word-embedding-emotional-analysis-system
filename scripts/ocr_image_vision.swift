import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write(Data("用法：ocr_image_vision 图片路径\n".utf8))
    exit(2)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: imageURL),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cgImage = bitmap.cgImage else {
    FileHandle.standardError.write(Data("无法读取图片：\(imageURL.path)\n".utf8))
    exit(3)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true

do {
    try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
    let observations = (request.results ?? []).sorted {
        if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.015 {
            return $0.boundingBox.midY > $1.boundingBox.midY
        }
        return $0.boundingBox.minX < $1.boundingBox.minX
    }
    for observation in observations {
        if let candidate = observation.topCandidates(1).first {
            print(candidate.string)
        }
    }
} catch {
    FileHandle.standardError.write(Data("OCR 失败：\(error)\n".utf8))
    exit(4)
}
