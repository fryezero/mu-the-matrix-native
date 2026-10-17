// Draws the original app icon for Mu The Matrix.app (MAC-BUNDLE-001) into an .iconset directory.
// Authored artwork only: a green Greek letter mu over deterministic "digital rain" on a dark rounded
// square. No game files or game art are used. Usage: make-icon OUT.iconset
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "AppIcon.iconset"
try FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)

func rgb(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: r, green: g, blue: b, alpha: a)
}

/// Fixed-seed LCG so every build draws the same rain.
struct LCG {
    var state: UInt32 = 0x4D75_2121
    mutating func next() -> CGFloat {
        state = state &* 1_664_525 &+ 1_013_904_223
        return CGFloat(state >> 8) / CGFloat(1 << 24)
    }
}

/// Draws the icon on a 1024-unit canvas (y up), scaled to the context size.
func draw(_ ctx: CGContext, size: Int) {
    let s = CGFloat(size) / 1024
    ctx.scaleBy(x: s, y: s)
    ctx.setShouldAntialias(true)
    ctx.interpolationQuality = .high

    // Body: Apple's 824-unit grid inside the 1024 canvas, continuous-ish corners.
    let body = CGRect(x: 100, y: 100, width: 824, height: 824)
    let shape = CGPath(roundedRect: body, cornerWidth: 186, cornerHeight: 186, transform: nil)

    // Drop shadow under the body.
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -10), blur: 28, color: rgb(0, 0, 0, 0.45))
    ctx.addPath(shape); ctx.setFillColor(rgb(0.02, 0.07, 0.04)); ctx.fillPath()
    ctx.restoreGState()

    ctx.saveGState()
    ctx.addPath(shape); ctx.clip()
    let space = CGColorSpace(name: CGColorSpace.sRGB)!
    let bg = CGGradient(colorsSpace: space, colors: [rgb(0.05, 0.20, 0.11), rgb(0.01, 0.05, 0.03)] as CFArray, locations: [0, 1])!
    ctx.drawLinearGradient(bg, start: CGPoint(x: 512, y: 924), end: CGPoint(x: 512, y: 100), options: [])

    // Digital rain: 14 columns of short bars, brightest at each column's head.
    var rng = LCG()
    let columns = 14
    let colW = body.width / CGFloat(columns)
    for c in 0..<columns {
        let x = body.minX + CGFloat(c) * colW + colW * 0.28
        let head = body.minY + 120 + rng.next() * (body.height - 160)
        let length = 5 + Int(rng.next() * 9)
        let cell: CGFloat = 38
        for k in 0..<length {
            let y = head + CGFloat(k) * cell
            if y > body.maxY { break }
            let fade = 1 - CGFloat(k) / CGFloat(length)
            let w = colW * (0.30 + 0.25 * rng.next())
            let h = cell * (0.35 + 0.35 * rng.next())
            let alpha = (k == 0 ? 0.85 : 0.10 + 0.40 * fade) * (0.6 + 0.4 * rng.next())
            ctx.setFillColor(k == 0 ? rgb(0.75, 1.0, 0.82, alpha) : rgb(0.20, 0.85, 0.42, alpha))
            ctx.addPath(CGPath(roundedRect: CGRect(x: x, y: y, width: w, height: h), cornerWidth: 4, cornerHeight: 4, transform: nil))
            ctx.fillPath()
        }
    }

    // Vignette so the letter stands out.
    let vignette = CGGradient(colorsSpace: space, colors: [rgb(0, 0, 0, 0), rgb(0, 0.02, 0.01, 0.75)] as CFArray, locations: [0.25, 1])!
    ctx.drawRadialGradient(vignette, startCenter: CGPoint(x: 512, y: 512), startRadius: 0, endCenter: CGPoint(x: 512, y: 512), endRadius: 520, options: [.drawsAfterEndLocation])

    // Ring.
    ctx.setStrokeColor(rgb(0.35, 1.0, 0.55, 0.55))
    ctx.setLineWidth(10)
    ctx.addEllipse(in: CGRect(x: 232, y: 232, width: 560, height: 560))
    ctx.strokePath()

    // The letter mu: a long left stem with a descender, a bowl, and a right stem with a small tail.
    let mu = CGMutablePath()
    let left: CGFloat = 392, right: CGFloat = 632, top: CGFloat = 660, base: CGFloat = 410, desc: CGFloat = 300
    mu.move(to: CGPoint(x: left, y: top))
    mu.addLine(to: CGPoint(x: left, y: desc))
    mu.move(to: CGPoint(x: left, y: top))
    mu.addLine(to: CGPoint(x: left, y: base + 90))
    mu.addCurve(to: CGPoint(x: right, y: base + 90), control1: CGPoint(x: left, y: base - 30), control2: CGPoint(x: right, y: base - 30))
    mu.move(to: CGPoint(x: right, y: top))
    mu.addLine(to: CGPoint(x: right, y: base + 40))
    mu.addQuadCurve(to: CGPoint(x: right + 62, y: base), control: CGPoint(x: right, y: base))
    ctx.saveGState()
    ctx.setLineCap(.round); ctx.setLineJoin(.round)
    ctx.setShadow(offset: .zero, blur: 40, color: rgb(0.30, 1.0, 0.50, 0.9))
    ctx.addPath(mu); ctx.setStrokeColor(rgb(0.40, 1.0, 0.58)); ctx.setLineWidth(64); ctx.strokePath()
    ctx.restoreGState()
    ctx.setLineCap(.round); ctx.setLineJoin(.round)
    ctx.addPath(mu); ctx.setStrokeColor(rgb(0.86, 1.0, 0.90)); ctx.setLineWidth(22); ctx.strokePath()

    // Top highlight.
    let shine = CGGradient(colorsSpace: space, colors: [rgb(1, 1, 1, 0.10), rgb(1, 1, 1, 0)] as CFArray, locations: [0, 1])!
    ctx.drawLinearGradient(shine, start: CGPoint(x: 512, y: 924), end: CGPoint(x: 512, y: 640), options: [])
    ctx.restoreGState()

    // Hairline edge.
    ctx.addPath(shape); ctx.setStrokeColor(rgb(0.45, 1.0, 0.60, 0.35)); ctx.setLineWidth(3); ctx.strokePath()
}

func png(size: Int, path: String) throws {
    let space = CGColorSpace(name: CGColorSpace.sRGB)!
    guard let ctx = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { throw NSError(domain: "icon", code: 1) }
    draw(ctx, size: size)
    guard let image = ctx.makeImage(),
          let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL, UTType.png.identifier as CFString, 1, nil)
    else { throw NSError(domain: "icon", code: 2) }
    CGImageDestinationAddImage(dest, image, nil)
    guard CGImageDestinationFinalize(dest) else { throw NSError(domain: "icon", code: 3) }
}

for base in [16, 32, 128, 256, 512] {
    try png(size: base, path: "\(out)/icon_\(base)x\(base).png")
    try png(size: base * 2, path: "\(out)/icon_\(base)x\(base)@2x.png")
}
print("wrote \(out)")
