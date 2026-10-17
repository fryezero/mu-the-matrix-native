// Usage: swift winshot.swift <owner-substring> <out.png>  — captures only matching windows (privacy-safe).
import CoreGraphics
import Foundation
let args = CommandLine.arguments
let needle = args[1].lowercased()
let list = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as! [[String: Any]]
var n = 0
for w in list {
    let owner = (w[kCGWindowOwnerName as String] as? String ?? "").lowercased()
    let name = (w[kCGWindowName as String] as? String ?? "")
    let layer = w[kCGWindowLayer as String] as? Int ?? 0
    let b = w[kCGWindowBounds as String] as? [String: Double] ?? [:]
    guard (owner.contains(needle) || name.lowercased().contains(needle)), layer == 0, (b["Width"] ?? 0) > 100 else { continue }
    let id = w[kCGWindowNumber as String] as! Int
    print("window \(id) owner=\(owner) name=\(name) bounds=\(b)")
    let out = n == 0 ? args[2] : args[2].replacingOccurrences(of: ".png", with: "-\(n).png")
    let p = Process(); p.launchPath = "/usr/sbin/screencapture"; p.arguments = ["-x", "-o", "-l", String(id), out]; p.launch(); p.waitUntilExit()
    n += 1
}
if n == 0 { print("no window matched") }
