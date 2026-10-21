// dmg-tool (MAC-DMG-001): build-time helper of make-dmg.sh. Only system frameworks; no committed artwork.
//
//   dmg-tool background OUT.png SCALE         the window background ("drag to Applications"), 660 x 400 points
//   dmg-tool dsstore VOLUME BACKGROUND APP    VOLUME/.DS_Store: icon view, window size, background picture and the
//                                             positions of APP and the Applications link (Finder reads it on mount)
//
// The .DS_Store writer follows the format Finder uses (a "Bud1" buddy-allocator file with one B-tree leaf of
// records, as documented by Mark Mentovai and Wim Lewis and implemented by the ds_store/dmgbuild Python packages).
// The background picture is referenced by an Alias Manager record that macOS itself creates for the file on the
// mounted image (FSNewAlias, looked up at run time: it has no Swift header any more).
import AppKit

// ---------------------------------------------------------------- layout (points, Finder window coordinates)
let windowSize = (w: 660, h: 400)
let appIcon = (x: 170, y: 205)
let appsIcon = (x: 490, y: 205)
let iconSize = 128.0
let textSize = 13.0

func die(_ s: String) -> Never { FileHandle.standardError.write(Data("dmg-tool: \(s)\n".utf8)); exit(1) }

// ---------------------------------------------------------------- background
func drawBackground(out: String, scale: Int) {
    let w = windowSize.w, h = windowSize.h
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w * scale, pixelsHigh: h * scale, bitsPerSample: 8,
                                     samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                                     bytesPerRow: 0, bitsPerPixel: 0) else { die("no bitmap") }
    rep.size = NSSize(width: w, height: h)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    // A light, slightly green surface: Finder draws the icon names in dark text on it.
    let top = NSColor(srgbRed: 0.97, green: 0.98, blue: 0.97, alpha: 1)
    let bottom = NSColor(srgbRed: 0.86, green: 0.91, blue: 0.87, alpha: 1)
    NSGradient(starting: bottom, ending: top)!.draw(in: NSRect(x: 0, y: 0, width: w, height: h), angle: 90)
    // Matrix green for the arrow.
    let green = NSColor(srgbRed: 0.05, green: 0.45, blue: 0.20, alpha: 1)
    // Arrow between the two icons (Finder's y grows downwards; AppKit's upwards).
    let ay = CGFloat(h - appIcon.y)
    let x0 = CGFloat(appIcon.x) + 88, x1 = CGFloat(appsIcon.x) - 88
    let arrow = NSBezierPath()
    arrow.lineWidth = 10; arrow.lineCapStyle = .round; arrow.lineJoinStyle = .round
    arrow.move(to: NSPoint(x: x0, y: ay)); arrow.line(to: NSPoint(x: x1 - 6, y: ay))
    green.setStroke(); arrow.stroke()
    let head = NSBezierPath()
    head.move(to: NSPoint(x: x1 + 10, y: ay))
    head.line(to: NSPoint(x: x1 - 22, y: ay + 22))
    head.line(to: NSPoint(x: x1 - 22, y: ay - 22))
    head.close()
    green.setFill(); head.fill()
    // Text.
    let para = NSMutableParagraphStyle(); para.alignment = .center
    func text(_ s: String, y: CGFloat, size: CGFloat, weight: NSFont.Weight, color: NSColor) {
        let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: size, weight: weight), .foregroundColor: color, .paragraphStyle: para]
        NSAttributedString(string: s, attributes: attrs).draw(in: NSRect(x: 0, y: y, width: CGFloat(w), height: size * 1.6))
    }
    // Both lines at the top: Finder may cover the bottom of the window with its path and status bars.
    text("Drag Mu The Matrix to Applications", y: CGFloat(h) - 60, size: 22, weight: .semibold, color: NSColor(white: 0.13, alpha: 1))
    text("Then open it from your Applications folder: it installs the game and starts it.", y: CGFloat(h) - 88, size: 13,
         weight: .regular, color: NSColor(white: 0.30, alpha: 1))
    NSGraphicsContext.restoreGraphicsState()
    guard let png = rep.representation(using: .png, properties: [:]) else { die("png encoding failed") }
    do { try png.write(to: URL(fileURLWithPath: out)) } catch { die("cannot write \(out): \(error)") }
}

// ---------------------------------------------------------------- alias record (Alias Manager, via dlsym)
func aliasRecord(for path: String) -> Data {
    typealias MakeRef = @convention(c) (UnsafePointer<CChar>, UnsafeMutableRawPointer, UnsafeMutablePointer<UInt8>?) -> Int16
    typealias NewAlias = @convention(c) (UnsafeRawPointer?, UnsafeRawPointer, UnsafeMutablePointer<UnsafeMutablePointer<UnsafeMutableRawPointer?>?>) -> Int16
    typealias HandleSize = @convention(c) (UnsafeMutablePointer<UnsafeMutableRawPointer?>) -> Int
    typealias DisposeHandle = @convention(c) (UnsafeMutablePointer<UnsafeMutableRawPointer?>) -> Void
    guard let h = dlopen("/System/Library/Frameworks/CoreServices.framework/CoreServices", RTLD_NOW),
          let fMake = dlsym(h, "FSPathMakeRef"), let fAlias = dlsym(h, "FSNewAlias"), let fSize = dlsym(h, "GetHandleSize")
    else { die("the Alias Manager functions are not available") }
    var ref = [UInt8](repeating: 0, count: 80)            // FSRef: 80 opaque bytes
    let e1 = ref.withUnsafeMutableBytes { unsafeBitCast(fMake, to: MakeRef.self)(path, $0.baseAddress!, nil) }
    guard e1 == 0 else { die("FSPathMakeRef(\(path)) failed: \(e1)") }
    var handle: UnsafeMutablePointer<UnsafeMutableRawPointer?>?
    let e2 = ref.withUnsafeBytes { unsafeBitCast(fAlias, to: NewAlias.self)(nil, $0.baseAddress!, &handle) }
    guard e2 == 0, let hd = handle, let p = hd.pointee else { die("FSNewAlias(\(path)) failed: \(e2)") }
    let data = Data(bytes: p, count: unsafeBitCast(fSize, to: HandleSize.self)(hd))
    if let fd = dlsym(h, "DisposeHandle") { unsafeBitCast(fd, to: DisposeHandle.self)(hd) }
    return data
}

// ---------------------------------------------------------------- .DS_Store
struct Record {
    let name: String, code: String, type: String, payload: Data
}

extension Data {
    mutating func u32(_ v: UInt32) { var b = v.bigEndian; Swift.withUnsafeBytes(of: &b) { append(contentsOf: $0) } }
    mutating func ascii4(_ s: String) { precondition(s.utf8.count == 4); append(contentsOf: Array(s.utf8)) }
    mutating func utf16(_ s: String) { u32(UInt32(s.utf16.count)); for c in s.utf16 { append(UInt8(c >> 8)); append(UInt8(c & 0xff)) } }
}

func blob(_ d: Data) -> Data { var x = Data(); x.u32(UInt32(d.count)); x.append(d); return x }
func bplist(_ o: [String: Any]) -> Data {
    do { return try PropertyListSerialization.data(fromPropertyList: o, format: .binary, options: 0) } catch { die("plist: \(error)") }
}
func iloc(_ x: Int, _ y: Int) -> Data {
    var d = Data(); d.u32(UInt32(x)); d.u32(UInt32(y)); d.append(contentsOf: [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0, 0]); return blob(d)
}

/// The buddy allocator of the file format: blocks are powers of two at multiples of their size.
struct Buddy {
    var free: [[UInt32]] = Array(repeating: [], count: 32)
    init() { free[31] = [0] }
    mutating func alloc(_ size: Int) -> (offset: UInt32, width: Int) {
        var w = 5; while (1 << w) < size { w += 1 }
        var k = w; while free[k].isEmpty { k += 1; if k > 31 { die("allocator full") } }
        let off = free[k].removeFirst()
        while k > w { k -= 1; free[k].append(off + (UInt32(1) << UInt32(k))); free[k].sort() }
        return (off, w)
    }
}

func writeDSStore(volume: String, background: String, app: String) {
    let bg = (volume as NSString).appendingPathComponent(background)
    guard FileManager.default.fileExists(atPath: bg) else { die("no \(bg)") }
    let bwsp: [String: Any] = [
        // The bounds include the 28-point title bar: the content area is exactly the background.
        "WindowBounds": "{{200, 120}, {\(windowSize.w), \(windowSize.h + 28)}}",
        "ShowSidebar": false, "ContainerShowSidebar": false, "SidebarWidth": 180, "ShowStatusBar": false,
        "ShowToolbar": false, "ShowPathbar": false, "ShowTabView": false, "PreviewPaneVisibility": false,
    ]
    let icvp: [String: Any] = [
        "viewOptionsVersion": 1, "backgroundType": 2, "backgroundImageAlias": aliasRecord(for: bg),
        "backgroundColorRed": 1.0, "backgroundColorGreen": 1.0, "backgroundColorBlue": 1.0,
        "iconSize": iconSize, "textSize": textSize, "gridSpacing": 100.0, "gridOffsetX": 0.0, "gridOffsetY": 0.0,
        "arrangeBy": "none", "labelOnBottom": true, "showIconPreview": false, "showItemInfo": false,
        "scrollPositionX": 0.0, "scrollPositionY": 0.0,
    ]
    var vSrn = Data(); vSrn.u32(1)
    var records = [
        Record(name: ".", code: "bwsp", type: "blob", payload: blob(bplist(bwsp))),
        Record(name: ".", code: "icvp", type: "blob", payload: blob(bplist(icvp))),
        Record(name: ".", code: "vSrn", type: "long", payload: vSrn),
        Record(name: ".", code: "vstl", type: "type", payload: Data("icnv".utf8)),
        Record(name: app, code: "Iloc", type: "blob", payload: iloc(appIcon.x, appIcon.y)),
        Record(name: "Applications", code: "Iloc", type: "blob", payload: iloc(appsIcon.x, appsIcon.y)),
    ]
    // Finder's order: file name without case, then the four-character code.
    records.sort { a, b in
        let (x, y) = (a.name.lowercased(), b.name.lowercased())
        return x != y ? Array(x.utf16).lexicographicallyPrecedes(Array(y.utf16)) : Array(a.code.utf8).lexicographicallyPrecedes(Array(b.code.utf8))
    }

    var leaf = Data(); leaf.u32(0); leaf.u32(UInt32(records.count))
    for r in records { leaf.utf16(r.name); leaf.ascii4(r.code); leaf.ascii4(r.type); leaf.append(r.payload) }
    guard leaf.count <= 4096 else { die("records do not fit one node") }

    var buddy = Buddy()
    _ = buddy.alloc(32)                         // the file header
    let root = buddy.alloc(2048)                // block 0: bookkeeping
    let node = buddy.alloc(4096)                // block 1: the B-tree's only (leaf) node
    let master = buddy.alloc(32)                // block 2: the "DSDB" master block
    var masterData = Data()
    for v: UInt32 in [1, 0, UInt32(records.count), 1, 4096] { masterData.u32(v) }   // root node, levels, records, nodes, page size

    var rootData = Data()
    let addrs = [root, node, master].map { $0.offset | UInt32($0.width) }
    rootData.u32(UInt32(addrs.count)); rootData.u32(0)
    for a in addrs { rootData.u32(a) }
    for _ in addrs.count..<256 { rootData.u32(0) }
    rootData.u32(1); rootData.append(4); rootData.ascii4("DSDB"); rootData.u32(2)
    for list in buddy.free { rootData.u32(UInt32(list.count)); for o in list { rootData.u32(o) } }
    guard rootData.count <= 2048 else { die("bookkeeping block too large") }

    let end = Int(max(node.offset + 4096, root.offset + 2048, master.offset + 32))
    var file = Data(count: 4 + end)
    func put(_ d: Data, at allocatorOffset: UInt32) { file.replaceSubrange(4 + Int(allocatorOffset) ..< 4 + Int(allocatorOffset) + d.count, with: d) }
    var header = Data(); header.u32(1); header.ascii4("Bud1"); header.u32(root.offset); header.u32(2048); header.u32(root.offset)
    header.append(contentsOf: [0, 0, 0x10, 0x0c, 0, 0, 0, 0x87, 0, 0, 0x20, 0x0b, 0, 0, 0, 0])   // as Finder writes it
    file.replaceSubrange(0..<header.count, with: header)
    put(rootData, at: root.offset)
    put(leaf, at: node.offset)
    put(masterData, at: master.offset)
    let out = (volume as NSString).appendingPathComponent(".DS_Store")
    do { try file.write(to: URL(fileURLWithPath: out)) } catch { die("cannot write \(out): \(error)") }
}

// ---------------------------------------------------------------- main
let args = Array(CommandLine.arguments.dropFirst())
switch args.first {
case "background" where args.count == 3:
    guard let s = Int(args[2]), s >= 1, s <= 3 else { die("scale must be 1, 2 or 3") }
    drawBackground(out: args[1], scale: s)
case "dsstore" where args.count == 4:
    writeDSStore(volume: args[1], background: args[2], app: args[3])
default:
    die("usage: dmg-tool background OUT.png SCALE | dmg-tool dsstore VOLUME BACKGROUND APP")
}
