import Foundation
import WebKit
import Cocoa

let args = CommandLine.arguments
if args.count < 3 {
    print("Usage: render_poster_wk <html_path> <out_png_path>")
    exit(1)
}

let htmlPath = args[1]
let outPath = args[2]

let htmlUrl = URL(fileURLWithPath: htmlPath)
guard let htmlString = try? String(contentsOf: htmlUrl, encoding: .utf8) else {
    print("Failed to read HTML file: \(htmlPath)")
    exit(1)
}

let config = WKWebViewConfiguration()
let webView = WKWebView(frame: CGRect(x: 0, y: 0, width: 1024, height: 1024), configuration: config)

let semaphore = DispatchSemaphore(value: 0)

webView.loadHTMLString(htmlString, baseURL: htmlUrl)

// Wait for layout and image decoding
DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
    let snapConfig = WKSnapshotConfiguration()
    snapConfig.rect = CGRect(x: 0, y: 0, width: 1024, height: 1024)
    webView.takeSnapshot(with: snapConfig) { image, error in
        if let image = image,
           let tiffData = image.tiffRepresentation,
           let bitmap = NSBitmapImageRep(data: tiffData),
           let pngData = bitmap.representation(using: .png, properties: [:]) {
            try? pngData.write(to: URL(fileURLWithPath: outPath))
            print("RENDER_SUCCESS: \(outPath)")
        } else {
            print("RENDER_ERROR: \(String(describing: error))")
        }
        semaphore.signal()
    }
}

let start = Date()
while semaphore.wait(timeout: .now() + 0.1) == .timedOut {
    RunLoop.current.run(mode: .default, before: Date(timeIntervalSinceNow: 0.1))
    if Date().timeIntervalSince(start) > 6 { break }
}
