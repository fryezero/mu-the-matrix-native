// Mu The Matrix.app (MAC-BUNDLE-001, MAC-FREE-001): settings, log and the bridges to mu-launch.sh (start)
// and the bundled installer (Resources/installer/setup-mu-mac.sh). Everything that touches Wine, CrossOver
// or a prefix lives in those scripts; this file only stores settings, writes the app log and runs them.
import Foundation

/// The user settings, stored as a plain XML plist (default
/// ~/Library/Application Support/MuTheMatrix/Launcher.plist, override with MU_SETTINGS_FILE).
struct LauncherSettings: Equatable {
    var runtime: String         // "free" (default: the free Wine runtime) or "crossover" (legacy bottle)
    var bottle: String
    var fastX87: Bool
    var timewalkerDir: String   // "" = the validated install-fast-x87.sh cache
    var resolution: String      // "" = keep the launcher's DevModeIndex, else "WxH" from mu-modes.txt
    var startImmediately: Bool

    static let keys = ["Runtime", "Bottle", "FastX87", "TimewalkerDir", "Resolution", "StartImmediately"]

    /// Built-in defaults, overridable at build time through Info.plist (make DEFAULT_BOTTLE=... etc.).
    static func defaults(info: [String: Any]? = Bundle.main.infoDictionary) -> LauncherSettings {
        let info = info ?? [:]
        let bottle = (info["MUDefaultBottle"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? "MuMatrixKit"
        let fast = (info["MUDefaultFastX87"] as? Bool) ?? ((info["MUDefaultFastX87"] as? String) == "1")
        let tw = (info["MUDefaultTimewalkerDir"] as? String) ?? ""
        let rt = (info["MUDefaultRuntime"] as? String).flatMap { ["free", "crossover"].contains($0) ? $0 : nil } ?? "free"
        // With the free runtime fast x87 is used whenever the installer set it up (about 45% less frame work).
        return LauncherSettings(runtime: rt, bottle: bottle, fastX87: fast || rt == "free", timewalkerDir: tw, resolution: "", startImmediately: true)
    }

    static var fileURL: URL {
        if let p = ProcessInfo.processInfo.environment["MU_SETTINGS_FILE"], !p.isEmpty { return URL(fileURLWithPath: p) }
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("MuTheMatrix/Launcher.plist")
    }

    static var fileExists: Bool { FileManager.default.fileExists(atPath: fileURL.path) }

    /// Values from the file override the defaults key by key; unknown or mistyped values are ignored.
    static func load() -> LauncherSettings {
        var s = defaults()
        guard let data = try? Data(contentsOf: fileURL),
              let dict = (try? PropertyListSerialization.propertyList(from: data, format: nil)) as? [String: Any]
        else { return s }
        if let v = dict["Runtime"] as? String, ["free", "crossover"].contains(v) { s.runtime = v }
        if let v = dict["Bottle"] as? String, !v.isEmpty { s.bottle = v }
        if let v = dict["FastX87"] as? Bool { s.fastX87 = v }
        if let v = dict["TimewalkerDir"] as? String { s.timewalkerDir = v }
        if let v = dict["Resolution"] as? String { s.resolution = v }
        if let v = dict["StartImmediately"] as? Bool { s.startImmediately = v }
        return s
    }

    var dictionary: [String: Any] {
        ["Runtime": runtime, "Bottle": bottle, "FastX87": fastX87, "TimewalkerDir": timewalkerDir,
         "Resolution": resolution, "StartImmediately": startImmediately]
    }

    func save() throws {
        let url = Self.fileURL
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = try PropertyListSerialization.data(fromPropertyList: dictionary, format: .xml, options: 0)
        try data.write(to: url, options: .atomic)
    }

    /// Environment for mu-launch.sh.
    var environment: [String: String] {
        ["MU_RUNTIME": runtime, "MU_BOTTLE": bottle, "MU_FAST_X87": fastX87 ? "1" : "0",
         "MU_TIMEWALKER_DIR": (timewalkerDir as NSString).expandingTildeInPath, "MU_RESOLUTION": resolution,
         "MU_LOG_DIR": AppLog.directory.path]
    }
}

/// Append-only text log in ~/Library/Logs/MuTheMatrix/app.log (MU_LOG_DIR overrides the directory).
/// The launcher's own Wine output goes to wine-BOTTLE.log in the same directory (written by mu-launch.sh).
enum AppLog {
    static var directory: URL {
        if let p = ProcessInfo.processInfo.environment["MU_LOG_DIR"], !p.isEmpty { return URL(fileURLWithPath: p) }
        return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/MuTheMatrix")
    }
    static var url: URL { directory.appendingPathComponent("app.log") }

    static func write(_ message: String) {
        let fm = FileManager.default
        try? fm.createDirectory(at: directory, withIntermediateDirectories: true)
        // Keep one previous generation once the log passes 512 KiB.
        if let size = (try? fm.attributesOfItem(atPath: url.path))?[.size] as? Int, size > 512 * 1024 {
            let old = directory.appendingPathComponent("app.log.1")
            try? fm.removeItem(at: old)
            try? fm.moveItem(at: url, to: old)
        }
        let stamp = ISO8601DateFormatter.string(from: Date(), timeZone: .current, formatOptions: [.withInternetDateTime])
        let line = message.split(separator: "\n", omittingEmptySubsequences: false)
            .map { "\(stamp) \($0)" }.joined(separator: "\n") + "\n"
        if let h = try? FileHandle(forWritingTo: url) {
            h.seekToEndOfFile(); h.write(Data(line.utf8)); try? h.close()
        } else {
            try? Data(line.utf8).write(to: url)
        }
    }
}

/// Result of one mu-launch.sh invocation.
struct LaunchResult {
    var status: Int32
    var output: String

    /// The "MU-ERROR CODE text" line, if any.
    var error: (code: Int, message: String)? {
        for line in output.split(separator: "\n") where line.hasPrefix("MU-ERROR ") {
            let rest = line.dropFirst("MU-ERROR ".count)
            let parts = rest.split(separator: " ", maxSplits: 1)
            if let code = Int(parts.first ?? "") { return (code, parts.count > 1 ? String(parts[1]) : "") }
        }
        return status == 0 ? nil : (Int(status), "mu-launch.sh failed with status \(status).")
    }

    var lines: [String] { output.split(separator: "\n").map(String.init) }
}

enum LaunchScript {
    static var url: URL? {
        if let p = ProcessInfo.processInfo.environment["MU_LAUNCH_SCRIPT"], !p.isEmpty { return URL(fileURLWithPath: p) }
        return Bundle.main.url(forResource: "mu-launch", withExtension: "sh")
    }

    /// Runs the script synchronously with one mode flag and returns its combined output.
    static func run(_ mode: String, settings: LauncherSettings) -> LaunchResult {
        guard let script = url else { return LaunchResult(status: 2, output: "MU-ERROR 2 mu-launch.sh is missing from the app bundle.") }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = [script.path, mode]
        var env = ProcessInfo.processInfo.environment
        for (k, v) in settings.environment { env[k] = v }
        p.environment = env
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        p.standardInput = FileHandle.nullDevice
        do { try p.run() } catch {
            return LaunchResult(status: 2, output: "MU-ERROR 2 could not run mu-launch.sh: \(error.localizedDescription)")
        }
        // Read before waiting so a full pipe cannot block the script. The started launcher's own output is
        // redirected to its log by the script, so this read ends when the script exits.
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return LaunchResult(status: p.terminationStatus, output: String(decoding: data, as: UTF8.self))
    }

    /// Free runtime install state from `mu-launch.sh --status`.
    static func freeStatus() -> (runtime: Bool, prefix: Bool, game: Bool) {
        var s = LauncherSettings.load(); s.runtime = "free"; s.resolution = ""; s.fastX87 = false
        let lines = run("--status", settings: s).lines
        return (lines.contains { $0.hasPrefix("runtime ok") }, lines.contains("prefix ok"), lines.contains("game ok"))
    }

    static func bottles() -> [(name: String, arch: String, hasGame: Bool)] {
        run("--list-bottles", settings: LauncherSettings.load()).lines.compactMap { line in
            let f = line.split(separator: "\t").map(String.init)
            return f.count == 3 ? (f[0], f[1], f[2] == "game") : nil
        }
    }

    static func modes(runtime: String, bottle: String) -> (modes: [String], current: Int?) {
        var s = LauncherSettings.load(); s.runtime = runtime; s.bottle = bottle; s.resolution = ""; s.fastX87 = false
        let r = run("--list-modes", settings: s)
        guard r.status == 0 else { return ([], nil) }
        var modes: [String] = []; var current: Int?
        for l in r.lines {
            if l.hasPrefix("current ") { current = Int(l.dropFirst(8)) } else if !l.hasPrefix("MU-") { modes.append(l) }
        }
        return (modes, current)
    }
}

/// User-facing titles for the script's exit codes (`free`: the free runtime, where there is no bottle).
func errorTitle(_ code: Int, free: Bool = false) -> String {
    if free && code == 13 { return errorTitle(30) }
    switch code {
    case 10: return "CrossOver is not installed"
    case 11: return "The CrossOver bottle was not found"
    case 12: return "The bottle is not a 32-bit bottle"
    case 13: return "Mu The Matrix is not installed in this bottle"
    case 14: return "Mu The Matrix is already running"
    case 15: return "The fast x87 runtime is missing"
    case 16: return "This resolution is not available"
    case 17: return "The resolution could not be saved"
    case 20: return "The launcher stopped right away"
    case 30: return "Mu The Matrix is not installed yet"
    case 31: return "The game folder is missing or damaged"
    default: return "Mu The Matrix could not be started"
    }
}

/// The bundled installer (Resources/installer/setup-mu-mac.sh; MU_SETUP_SCRIPT overrides). It runs with the
/// free runtime and streams its output line by line; the app shows the "== N/M step" lines as progress.
enum Installer {
    static var script: URL? {
        if let p = ProcessInfo.processInfo.environment["MU_SETUP_SCRIPT"], !p.isEmpty { return URL(fileURLWithPath: p) }
        return Bundle.main.resourceURL?.appendingPathComponent("installer/setup-mu-mac.sh")
    }

    /// DLLs bundled at build time (make EMBED_MUGL=... EMBED_MSCOREE=...), passed as --mugl-dll / --mscoree-dll.
    static var bundledDLLs: (mugl: URL?, mscoree: URL?) {
        guard let dir = Bundle.main.resourceURL?.appendingPathComponent("dlls") else { return (nil, nil) }
        let fm = FileManager.default
        let g = dir.appendingPathComponent("opengl32.dll"), m = dir.appendingPathComponent("mscoree.dll")
        return (fm.fileExists(atPath: g.path) ? g : nil, fm.fileExists(atPath: m.path) ? m : nil)
    }

    /// gameDir nil = download and run the official installer.
    static func arguments(gameDir: String?, dryRun: Bool = false) -> [String] {
        var a = ["--runtime", "free", "--no-desktop"]
        if let g = gameDir { a += ["--game-dir", g] } else { a += ["--game-installer", "official"] }
        let d = bundledDLLs
        if let g = d.mugl { a += ["--mugl-dll", g.path]; if let m = d.mscoree { a += ["--mscoree-dll", m.path] } }
        if let fx = Bundle.main.resourceURL?.appendingPathComponent("fast-x87"),
           FileManager.default.fileExists(atPath: fx.appendingPathComponent("runtime_loader").path) {
            a += ["--fast-x87-dir", fx.path]
        }
        if dryRun { a.append("--dry-run") }
        return a
    }

    /// Starts the installer; `line` is called on the main queue for every output line, `done` with the status.
    @discardableResult
    static func start(gameDir: String?, dryRun: Bool = false, line: @escaping (String) -> Void, done: @escaping (Int32) -> Void) -> Process? {
        guard let url = script, FileManager.default.fileExists(atPath: url.path) else {
            line("The installer is missing from the app bundle."); done(2); return nil
        }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = [url.path] + arguments(gameDir: gameDir, dryRun: dryRun)
        var env = ProcessInfo.processInfo.environment
        for k in env.keys where k.hasPrefix("CLAUDE") { env[k] = nil }
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")
        p.environment = env
        let pipe = Pipe()
        p.standardOutput = pipe; p.standardError = pipe; p.standardInput = FileHandle.nullDevice
        var buffer = Data()
        pipe.fileHandleForReading.readabilityHandler = { h in
            let chunk = h.availableData
            if chunk.isEmpty { h.readabilityHandler = nil; return }
            buffer.append(chunk)
            // curl's progress bar uses carriage returns; treat them as line ends too.
            while let i = buffer.firstIndex(where: { $0 == 10 || $0 == 13 }) {
                let l = String(decoding: buffer[buffer.startIndex..<i], as: UTF8.self)
                buffer.removeSubrange(buffer.startIndex...i)
                if !l.isEmpty { DispatchQueue.main.async { line(l) } }
            }
        }
        p.terminationHandler = { proc in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { done(proc.terminationStatus) }
        }
        do { try p.run() } catch { line("Could not start the installer: \(error.localizedDescription)"); done(2); return nil }
        return p
    }
}
