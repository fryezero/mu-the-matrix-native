// Mu The Matrix.app (MAC-DMG-001): the parts of the first run that are not window code. The install window's
// step titles and its overall progress (InstallProgress), and "Move to Applications" (AppMover).
import AppKit

// ---------------------------------------------------------------- install progress
/// What the player sees for each installer step ("== 7/14 game files"): a plain title without technical names, and
/// about how long the step takes (seconds), for the overall progress bar. The game download is measured in bytes.
let installStepInfo: [String: (title: String, seconds: Double)] = [
    "free Wine runtime": ("Getting ready", 30),
    "winetricks": ("Getting ready", 5),
    "Wine prefix (32-bit)": ("Getting ready", 25),
    "registry (AeDebug off, overrides)": ("Getting ready", 10),
    ".NET Framework 4.8": ("Installing components from Microsoft", 240),
    "Windows version": ("Installing components from Microsoft", 10),
    "registry re-check after .NET": ("Installing components from Microsoft", 5),
    "game files": ("Installing the game", 150),
    "launcher .NET config": ("Finishing", 3),
    "C:\\mutools": ("Finishing", 3),
    "LauncherOption.if": ("Finishing", 3),
    "proxy DLLs": ("Finishing", 3),
    "launcher skin": ("Finishing", 3),
    "fast x87 and Desktop launcher": ("Finishing", 5),
    "verify": ("Checking that everything works", 20),
]

/// One overall fraction for the whole installation: finished steps count with their estimated time, the running step
/// with its elapsed time (at most 90% of its estimate), the game download with the bytes received. Never goes back.
final class InstallProgress {
    static let downloadSeconds = 2000.0          // the 2.2 GB game download at about 1 MB/s
    private let fromFolder: Bool
    private let total: Double
    private var done = 0.0
    private var current: (name: String, seconds: Double, started: TimeInterval)?
    private var downloadFraction = 0.0
    private var installerStarted: TimeInterval?
    private(set) var fraction = 0.0

    init(fromFolder: Bool) {
        self.fromFolder = fromFolder
        total = installStepInfo.values.reduce(0) { $0 + $1.seconds } + (fromFolder ? 0 : Self.downloadSeconds)
    }
    private func budget(_ name: String) -> Double {
        (installStepInfo[name]?.seconds ?? 5) + (name == "game files" && !fromFolder ? Self.downloadSeconds : 0)
    }
    func begin(_ name: String, now: TimeInterval) {
        if let c = current { done += budget(c.name) }
        current = (name, installStepInfo[name]?.seconds ?? 5, now)
        downloadFraction = 0; installerStarted = nil
    }
    func download(_ f: Double) { downloadFraction = min(max(f, 0), 1) }
    func installerRuns(now: TimeInterval) { if installerStarted == nil { installerStarted = now } }

    @discardableResult
    func update(now: TimeInterval) -> Double {
        guard let c = current else { return fraction }
        var inStep = min((now - c.started) / c.seconds, 0.9) * c.seconds
        if c.name == "game files" && !fromFolder {
            if let s = installerStarted { inStep = Self.downloadSeconds + min((now - s) / c.seconds, 0.9) * c.seconds }
            else { inStep = downloadFraction * Self.downloadSeconds }
        }
        fraction = max(fraction, min((done + inStep) / total, 0.99))
        return fraction
    }
}

// ---------------------------------------------------------------- move to Applications
/// An app opened from the disk image, from Downloads or from any folder outside /Applications and ~/Applications
/// (a downloaded app then runs from a random read-only copy: App Translocation) offers to copy itself to the
/// Applications folder and to open again from there, so the game is never installed from the disk image.
/// MU_APPLICATIONS_DIR replaces the Applications folders (tests and rehearsals); MU_SKIP_MOVE=1 turns it off.
enum AppMover {
    private static var env: [String: String] { ProcessInfo.processInfo.environment }
    /// True while copying and relaunching: no window is open then, and the app must not quit by itself.
    static var busy = false

    static var targets: [URL] {
        if let d = env["MU_APPLICATIONS_DIR"], !d.isEmpty { return [URL(fileURLWithPath: d)] }
        return [URL(fileURLWithPath: "/Applications"),
                FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Applications")]
    }

    static func isInside(_ url: URL, _ dir: URL) -> Bool {
        let d = dir.resolvingSymlinksInPath().path, p = url.resolvingSymlinksInPath().path
        return p.hasPrefix(d.hasSuffix("/") ? d : d + "/")
    }

    /// The app's real location and whether macOS runs it from a translocated copy (Security's SecTranslocate
    /// functions, looked up at run time; without them the path pattern decides).
    static func origin(of url: URL) -> (url: URL, translocated: Bool) {
        typealias IsTranslocated = @convention(c) (CFURL, UnsafeMutablePointer<DarwinBoolean>, UnsafeMutableRawPointer?) -> DarwinBoolean
        typealias OriginalPath = @convention(c) (CFURL, UnsafeMutableRawPointer?) -> Unmanaged<CFURL>?
        let byPath = url.path.contains("/AppTranslocation/")
        guard let h = dlopen("/System/Library/Frameworks/Security.framework/Security", RTLD_LAZY),
              let f1 = dlsym(h, "SecTranslocateIsTranslocatedURL"), let f2 = dlsym(h, "SecTranslocateCreateOriginalPathForURL")
        else { return (url, byPath) }
        var translocated: DarwinBoolean = false
        guard unsafeBitCast(f1, to: IsTranslocated.self)(url as CFURL, &translocated, nil).boolValue, translocated.boolValue,
              let orig = unsafeBitCast(f2, to: OriginalPath.self)(url as CFURL, nil)?.takeRetainedValue()
        else { return (url, byPath) }
        return (orig as URL, true)
    }

    /// Read-only volume holding `url` (a mounted disk image), or nil.
    static func readOnlyVolume(of url: URL) -> URL? {
        guard let v = try? url.resourceValues(forKeys: [.volumeIsReadOnlyKey, .volumeURLKey]), v.volumeIsReadOnly == true else { return nil }
        return v.volume
    }

    /// Shows the offer when the app is outside Applications. Returns true when the app is moving or quitting
    /// (the caller must not continue).
    static func offerIfNeeded() -> Bool {
        guard env["MU_SKIP_MOVE"] != "1" else { return false }
        let here = Bundle.main.bundleURL
        let (orig, translocated) = origin(of: here)
        guard !targets.contains(where: { isInside(orig, $0) }) else { return false }
        let volume = readOnlyVolume(of: orig)
        AppLog.write("app outside Applications: \(orig.path)\(translocated ? " (translocated)" : "")\(volume != nil ? " (read-only volume)" : "")")
        let a = NSAlert()
        a.messageText = "Move Mu The Matrix to your Applications folder?"
        a.informativeText = "Mu The Matrix needs to be in your Applications folder. It copies itself there and opens again."
            + (volume != nil ? " The Mu The Matrix disk is ejected afterwards." : "")
        a.addButton(withTitle: "Move to Applications")
        let canStay = !translocated && volume == nil
        a.addButton(withTitle: canStay ? "Not Now" : "Quit")
        NSApp.activate(ignoringOtherApps: true)
        guard a.runModal() == .alertFirstButtonReturn else {
            AppLog.write("move to Applications declined")
            if canStay { return false }
            NSApp.terminate(nil); return true
        }
        busy = true
        do {
            let dest = try copyToApplications(from: here, name: orig.lastPathComponent)
            relaunch(dest, ejecting: volume)
        } catch MoveError.alreadyRunning(let app) {
            AppLog.write("move: \(app.bundleURL?.path ?? "?") is already running; switching to it")
            app.activate(options: [])
            NSApp.terminate(nil)
        } catch {
            AppLog.write("move failed: \(error.localizedDescription)")
            let e = NSAlert()
            e.alertStyle = .warning
            e.messageText = "Mu The Matrix could not copy itself to Applications"
            e.informativeText = "\(error.localizedDescription)\n\nDrag Mu The Matrix into your Applications folder yourself, then open it from there."
            e.addButton(withTitle: "Quit")
            e.runModal()
            NSApp.terminate(nil)
        }
        return true
    }

    enum MoveError: LocalizedError {
        case alreadyRunning(NSRunningApplication), copyFailed(String)
        var errorDescription: String? {
            switch self {
            case .alreadyRunning: return "Mu The Matrix is already open from Applications."
            case .copyFailed(let s): return s
            }
        }
    }

    /// Copies the app (ditto keeps its signature) into the first Applications folder it may write to, replacing an
    /// older copy there (moved to the Trash), and removes the download flag from the copy: the player already
    /// approved this app, and a flagged copy would be translocated again on every start.
    static func copyToApplications(from src: URL, name: String) throws -> URL {
        let fm = FileManager.default
        var dir: URL?
        for t in targets {
            if !fm.fileExists(atPath: t.path) { try? fm.createDirectory(at: t, withIntermediateDirectories: true) }
            if fm.isWritableFile(atPath: t.path) { dir = t; break }
        }
        guard let dir else { throw MoveError.copyFailed("No Applications folder can be written to.") }
        let dest = dir.appendingPathComponent(name)
        if fm.fileExists(atPath: dest.path) {
            if let running = NSWorkspace.shared.runningApplications.first(where: { $0.bundleURL?.standardizedFileURL == dest.standardizedFileURL }) {
                throw MoveError.alreadyRunning(running)
            }
            do { try fm.trashItem(at: dest, resultingItemURL: nil) } catch { try fm.removeItem(at: dest) }
            AppLog.write("move: replaced the older copy in \(dir.path)")
        }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
        p.arguments = [src.path, dest.path]
        let pipe = Pipe(); p.standardOutput = pipe; p.standardError = pipe
        try p.run()
        let out = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
        p.waitUntilExit()
        guard p.terminationStatus == 0 else { try? fm.removeItem(at: dest); throw MoveError.copyFailed("Copying failed: \(out)") }
        removeQuarantine(dest)
        AppLog.write("move: copied to \(dest.path)")
        return dest
    }

    static func removeQuarantine(_ root: URL) {
        var paths = [root.path]
        if let e = FileManager.default.enumerator(atPath: root.path) { for case let r as String in e { paths.append(root.appendingPathComponent(r).path) } }
        for p in paths { removexattr(p, "com.apple.quarantine", XATTR_NOFOLLOW) }
    }

    /// Opens the copy (passing the test variables on) and quits; a disk image is ejected once this copy has quit.
    static func relaunch(_ dest: URL, ejecting volume: URL?) {
        let cfg = NSWorkspace.OpenConfiguration()
        cfg.createsNewApplicationInstance = true
        cfg.environment = env.filter { $0.key.hasPrefix("MU_") || $0.key.hasPrefix("MUKIT_") }
        NSWorkspace.shared.openApplication(at: dest, configuration: cfg) { _, error in
            DispatchQueue.main.async {
                if let error { AppLog.write("move: could not open \(dest.path): \(error.localizedDescription)") }
                if let v = volume {
                    let p = Process()
                    p.executableURL = URL(fileURLWithPath: "/bin/sh")
                    p.arguments = ["-c", "sleep 3; /usr/bin/hdiutil detach -quiet \"$0\" || /usr/bin/hdiutil detach -quiet \"$0\"", v.path]
                    p.standardOutput = FileHandle.nullDevice; p.standardError = FileHandle.nullDevice
                    try? p.run()
                    AppLog.write("move: ejecting \(v.path) after quitting")
                }
                NSApp.terminate(nil)
            }
        }
    }
}

