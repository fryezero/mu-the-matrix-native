// Mu The Matrix.app (MAC-BUNDLE-001, MAC-FREE-001): settings, log and the bridges to mu-launch.sh (start)
// and the bundled installer (Resources/installer/setup-mu-mac.sh). Everything that touches Wine, CrossOver
// or a prefix lives in those scripts; this file only stores settings, writes the app log and runs them.
import Foundation
import CryptoKit

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

    /// Runs the script synchronously with one mode flag (plus its arguments) and returns its combined output.
    static func run(_ mode: String, _ extra: [String] = [], settings: LauncherSettings) -> LaunchResult {
        guard let script = url else { return LaunchResult(status: 2, output: "MU-ERROR 2 mu-launch.sh is missing from the app bundle.") }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = [script.path, mode] + extra
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

    /// The in-game FPS counter (mugl, C:\mutools\mugl-fps.txt): `on` nil reads it, true/false sets it.
    /// Returns the state afterwards, or nil when the prefix/bottle has no game folder yet.
    @discardableResult
    static func fpsCounter(_ on: Bool? = nil, settings: LauncherSettings) -> Bool? {
        let r = run("--fps-counter", on.map { [$0 ? "on" : "off"] } ?? [], settings: settings)
        guard r.status == 0 else { return nil }
        return r.lines.contains("fps-counter on")
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

/// A child process in its own process group (posix_spawn with POSIX_SPAWN_SETPGROUP), so everything it starts
/// (curl, tar, winetricks, Wine) can be signalled at once with kill(-pgid). stdout and stderr arrive as chunks on a
/// background queue; `onExit` gets the exit status (128 + signal number when it was killed by a signal).
final class ProcessGroupChild {
    let pid: pid_t
    private let lock = NSLock()
    private var exitStatus: Int32?
    private var reader: FileHandle?            // kept: closing it would SIGPIPE the child
    var status: Int32? { lock.lock(); defer { lock.unlock() }; return exitStatus }
    var isRunning: Bool { status == nil }

    init(executable: String, arguments: [String], environment: [String: String],
         output: @escaping (Data) -> Void, onExit: @escaping (Int32) -> Void) throws {
        var fds: [Int32] = [-1, -1]
        guard pipe(&fds) == 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
        var actions: posix_spawn_file_actions_t?
        posix_spawn_file_actions_init(&actions)
        defer { posix_spawn_file_actions_destroy(&actions) }
        posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", O_RDONLY, 0)
        posix_spawn_file_actions_adddup2(&actions, fds[1], 1)
        posix_spawn_file_actions_adddup2(&actions, fds[1], 2)
        var attr: posix_spawnattr_t?
        posix_spawnattr_init(&attr)
        defer { posix_spawnattr_destroy(&attr) }
        posix_spawnattr_setpgroup(&attr, 0)                       // new group, id = the child's pid
        var noSignals = sigset_t(); sigemptyset(&noSignals)
        posix_spawnattr_setsigmask(&attr, &noSignals)
        var defaults = sigset_t(); sigfillset(&defaults); sigdelset(&defaults, SIGKILL); sigdelset(&defaults, SIGSTOP)
        posix_spawnattr_setsigdefault(&attr, &defaults)
        // CLOEXEC_DEFAULT: the child gets only fds 0-2, none of the app's own descriptors.
        posix_spawnattr_setflags(&attr, Int16(POSIX_SPAWN_SETPGROUP | POSIX_SPAWN_SETSIGMASK | POSIX_SPAWN_SETSIGDEF | POSIX_SPAWN_CLOEXEC_DEFAULT))
        let argv: [UnsafeMutablePointer<CChar>?] = ([executable] + arguments).map { strdup($0) } + [nil]
        let envp: [UnsafeMutablePointer<CChar>?] = environment.map { strdup("\($0.key)=\($0.value)") } + [nil]
        defer { argv.forEach { free($0) }; envp.forEach { free($0) } }
        var child: pid_t = 0
        let rc = posix_spawn(&child, executable, &actions, &attr, argv, envp)
        close(fds[1])
        guard rc == 0 else { close(fds[0]); throw POSIXError(POSIXErrorCode(rawValue: rc) ?? .EIO) }
        pid = child
        let reader = FileHandle(fileDescriptor: fds[0], closeOnDealloc: true)
        self.reader = reader
        reader.readabilityHandler = { h in
            let data = h.availableData
            if data.isEmpty { h.readabilityHandler = nil } else { output(data) }
        }
        // A plain thread blocks in waitpid for this one pid (Foundation's Process never reaps it).
        Thread { [self] in
            var st: Int32 = 0
            while waitpid(child, &st, 0) < 0 && errno == EINTR {}
            let code = (st & 0x7f) == 0 ? (st >> 8) & 0xff : 128 + (st & 0x7f)
            lock.lock(); exitStatus = code; lock.unlock()
            onExit(code)
        }.start()
    }

    /// Sends `sig` to the whole process group (ESRCH, an empty group, is ignored).
    func signalGroup(_ sig: Int32) { kill(-pid, sig) }
}

/// Splits a byte stream into lines; curl's carriage returns count as line ends too.
final class LineSplitter {
    private var buffer = Data()
    private let lock = NSLock()
    func feed(_ chunk: Data, _ line: (String) -> Void) {
        lock.lock(); defer { lock.unlock() }
        buffer.append(chunk)
        while let i = buffer.firstIndex(where: { $0 == 10 || $0 == 13 }) {
            let l = String(decoding: buffer[buffer.startIndex..<i], as: UTF8.self)
            buffer.removeSubrange(buffer.startIndex...i)
            if !l.isEmpty { line(l) }
        }
    }
}

/// Turns the installer's "MU-PROGRESS BYTES TOTAL NAME" lines (one per second while it downloads) into
/// "812 MB of 2.18 GB (37%) · 4.2 MB/s · about 5 minutes left". The speed is the average of the last 20 seconds.
final class DownloadMeter {
    private(set) var name = ""
    private(set) var bytes: Int64 = 0
    private(set) var total: Int64 = 0
    private var samples: [(t: TimeInterval, b: Int64)] = []

    /// Returns false when `line` is not a progress line.
    @discardableResult
    func feed(_ line: String, now: TimeInterval = ProcessInfo.processInfo.systemUptime) -> Bool {
        let f = line.split(separator: " ")
        guard f.count >= 3, f[0] == "MU-PROGRESS", let b = Int64(f[1]), let t = Int64(f[2]) else { return false }
        let n = f.count > 3 ? f[3...].joined(separator: " ") : ""
        if n != name || b < bytes { samples = [] }
        name = n; bytes = b; total = t
        samples.append((now, b))
        samples.removeAll { now - $0.t > 20 }
        return true
    }

    /// Bytes per second, nil until there are a few seconds of samples.
    var speed: Double? {
        guard let first = samples.first, let last = samples.last, last.t - first.t >= 3 else { return nil }
        return Double(last.b - first.b) / (last.t - first.t)
    }
    var fraction: Double? { total > 0 ? min(1, Double(bytes) / Double(total)) : nil }

    private static let formatter: ByteCountFormatter = {
        let f = ByteCountFormatter(); f.countStyle = .file; f.allowsNonnumericFormatting = false   // "0 bytes", not "Zero KB"
        return f
    }()
    static func size(_ b: Int64) -> String { formatter.string(fromByteCount: b) }

    static func timeLeft(_ seconds: Double) -> String {
        if seconds < 60 { return "less than a minute left" }
        let m = Int((seconds / 60).rounded())
        if m < 60 { return "about \(m) minute\(m == 1 ? "" : "s") left" }
        let h = m / 60, r = m % 60
        return "about \(h) hour\(h == 1 ? "" : "s")" + (r == 0 ? "" : " \(r) min") + " left"
    }

    var summary: String {
        var parts: [String] = []
        if total > 0 { parts.append("\(Self.size(bytes)) of \(Self.size(total)) (\(Int((fraction ?? 0) * 100))%)") }
        else { parts.append(Self.size(bytes)) }
        if let s = speed {
            if s > 0 {
                parts.append("\(Self.size(Int64(s)))/s")
                if total > bytes { parts.append(Self.timeLeft(Double(total - bytes) / s)) }
            } else { parts.append("waiting for data…") }
        }
        return parts.joined(separator: " · ")
    }
}

/// Rosetta 2 (Apple's translator for Intel programs; the Wine runtime is x86_64). MU_ROSETTA_CHECK and
/// MU_ROSETTA_INSTALL replace the check and the install command (tests).
enum Rosetta {
    static func isInstalled() -> Bool {
        let env = ProcessInfo.processInfo.environment
        if let cmd = env["MU_ROSETTA_CHECK"], !cmd.isEmpty { return run("/bin/sh", ["-c", cmd]).status == 0 }
        var info = utsname(); uname(&info)
        let machine = withUnsafeBytes(of: &info.machine) { String(decoding: $0.prefix { $0 != 0 }, as: UTF8.self) }
        guard machine == "arm64" else { return true }
        return run("/usr/bin/arch", ["-x86_64", "/usr/bin/true"]).status == 0
    }

    static let terminalCommand = "sudo softwareupdate --install-rosetta --agree-to-license"

    /// Installs Rosetta through the standard macOS administrator prompt (osascript "with administrator privileges").
    static func install() -> (ok: Bool, declined: Bool, output: String) {
        let r: (status: Int32, output: String)
        if let cmd = ProcessInfo.processInfo.environment["MU_ROSETTA_INSTALL"], !cmd.isEmpty {
            r = run("/bin/sh", ["-c", cmd])
        } else {
            let script = "do shell script \"/usr/sbin/softwareupdate --install-rosetta --agree-to-license\" with prompt "
                + "\"Mu The Matrix wants to install Rosetta 2, Apple's free translator for Intel programs.\" with administrator privileges"
            r = run("/usr/bin/osascript", ["-e", script])
        }
        // osascript reports "User canceled. (-128)" when the prompt is dismissed.
        let declined = r.status != 0 && r.output.contains("-128")
        return (r.status == 0, declined, r.output.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    private static func run(_ exe: String, _ args: [String]) -> (status: Int32, output: String) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: exe)
        p.arguments = args
        let pipe = Pipe()
        p.standardOutput = pipe; p.standardError = pipe; p.standardInput = FileHandle.nullDevice
        do { try p.run() } catch { return (127, error.localizedDescription) }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return (p.terminationStatus, String(decoding: data, as: UTF8.self))
    }
}

/// The bundled installer (Resources/installer/setup-mu-mac.sh; MU_SETUP_SCRIPT overrides). It runs with the
/// free runtime in its own process group and streams its output line by line; the app shows the "== N/M step"
/// lines as progress and the "MU-PROGRESS" lines as download progress.
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

    /// The fast x87 translator bundled at build time (make EMBED_FAST_X87=...), passed as --fast-x87-dir.
    static var bundledFastX87: URL? {
        guard let fx = Bundle.main.resourceURL?.appendingPathComponent("fast-x87") else { return nil }
        let fm = FileManager.default
        let need = ["libtimewalker.dylib", "runtime_loader", "libRuntimeRosettax87", "x87-main-only-wrapper"]
        return need.allSatisfy { fm.fileExists(atPath: fx.appendingPathComponent($0).path) } ? fx : nil
    }

    /// The Wine runtime bundled at build time (make EMBED_RUNTIME=...): Resources/runtime/<RuntimeFile.testedName>.
    /// Passed as --runtime-archive with its pinned SHA-256, so every install and repair uses it and nothing is
    /// downloaded for it; the installer checks the hash before it unpacks the file.
    static var bundledRuntime: URL? {
        guard let u = Bundle.main.resourceURL?.appendingPathComponent("runtime/\(RuntimeFile.testedName)") else { return nil }
        return FileManager.default.fileExists(atPath: u.path) ? u : nil
    }

    /// The files a player build must contain (make player-app); empty for a complete app.
    static var missingEmbeds: [String] {
        var m: [String] = []
        let d = bundledDLLs
        if d.mugl == nil { m.append("mugl (opengl32.dll, EMBED_MUGL)") }
        if d.mscoree == nil { m.append("mscoree proxy (mscoree.dll, EMBED_MSCOREE)") }
        if bundledFastX87 == nil { m.append("fast x87 translator (EMBED_FAST_X87)") }
        if bundledRuntime == nil { m.append("Wine runtime (\(RuntimeFile.testedName), EMBED_RUNTIME)") }
        return m
    }

    /// gameDir nil = download and run the official installer. runtimeArchive = another Wine runtime file
    /// (--runtime-archive; the installer hashes and checks it); nil = the bundled runtime, or the default
    /// download in a development build without one.
    static func arguments(gameDir: String?, runtimeArchive: String? = nil, dryRun: Bool = false) -> [String] {
        var a = ["--runtime", "free", "--no-desktop"]
        if let g = gameDir { a += ["--game-dir", g] } else { a += ["--game-installer", "official"] }
        if let r = runtimeArchive { a += ["--runtime-archive", r] }
        else if let r = bundledRuntime { a += ["--runtime-archive", r.path, "--runtime-sha256", RuntimeFile.testedSHA256] }
        let d = bundledDLLs
        if let g = d.mugl { a += ["--mugl-dll", g.path]; if let m = d.mscoree { a += ["--mscoree-dll", m.path] } }
        if let fx = bundledFastX87 { a += ["--fast-x87-dir", fx.path] }
        if dryRun { a.append("--dry-run") }
        return a
    }

    static var environment: [String: String] {
        var env = ProcessInfo.processInfo.environment
        for k in env.keys where k.hasPrefix("CLAUDE") { env[k] = nil }
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")
        env["MUKIT_PROGRESS"] = "lines"
        return env
    }

    /// Seconds between SIGTERM and SIGKILL when an install is cancelled (MU_CANCEL_GRACE overrides).
    static var cancelGrace: TimeInterval {
        ProcessInfo.processInfo.environment["MU_CANCEL_GRACE"].flatMap(TimeInterval.init) ?? 10
    }

    /// Starts the installer; `line` is called on the main queue for every output line, `done` with the status and
    /// whether the install was cancelled. Returns nil when it could not start (then `done` was already called).
    static func start(gameDir: String?, runtimeArchive: String? = nil, dryRun: Bool = false, line: @escaping (String) -> Void,
                      done: @escaping (_ status: Int32, _ cancelled: Bool) -> Void) -> InstallSession? {
        guard let url = script, FileManager.default.fileExists(atPath: url.path) else {
            line("The installer is missing from the app bundle."); done(2, false); return nil
        }
        let s = InstallSession(line: line, done: done)
        do {
            try s.start(arguments: [url.path] + arguments(gameDir: gameDir, runtimeArchive: runtimeArchive, dryRun: dryRun))
        } catch {
            line("Could not start the installer: \(error.localizedDescription)"); done(2, false); return nil
        }
        return s
    }

    /// After a cancel: `setup-mu-mac.sh --runtime free --stop` stops what is left (this prefix's wineserver, leftover
    /// downloads) and removes the setup lock, so Try Again works right away. Returns its output.
    static func stopLeftovers() -> String {
        guard let url = script else { return "" }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = [url.path, "--runtime", "free", "--stop"]
        p.environment = environment
        let pipe = Pipe()
        p.standardOutput = pipe; p.standardError = pipe; p.standardInput = FileHandle.nullDevice
        do { try p.run() } catch { return "Could not run the clean-up: \(error.localizedDescription)" }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return String(decoding: data, as: UTF8.self)
    }
}

/// The Wine runtime the app is tested with: the CrossOver 26.3 build of packaging/build-wine.sh (LGPL-2.1+).
/// make player-app bundles exactly this file (EMBED_RUNTIME, checked against testedSHA256; the Makefile reads both
/// values from here) in Resources/runtime, next to its license (COPYING.LIB) and the sources note (SOURCES.txt).
enum RuntimeFile {
    static let testedName = "winecx-26.3.0-mu1.tar.xz"
    static let pinnedSHA256 = "c50cb614576764fa0c08595d6901402353c1954f20b3b7ad997286727f116599"
    /// MU_RUNTIME_SHA256 replaces the pin for the synthetic test suite only (like the MUKIT_*_SHA256 pins).
    static var testedSHA256: String {
        ProcessInfo.processInfo.environment["MU_RUNTIME_SHA256"].flatMap { $0.isEmpty ? nil : $0 } ?? pinnedSHA256
    }

    /// Hex SHA-256 of the file, read in 1 MB chunks; nil when it cannot be read.
    static func sha256(of path: String) -> String? {
        guard let h = FileHandle(forReadingAtPath: path) else { return nil }
        defer { try? h.close() }
        var hasher = SHA256()
        do {
            // read(upToCount:) returns nil or empty data at the end of the file.
            while let chunk = try h.read(upToCount: 1 << 20), !chunk.isEmpty { hasher.update(data: chunk) }
        } catch { return nil }
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }

    static func isTested(_ path: String) -> Bool { sha256(of: path) == testedSHA256 }
}

/// One installer run. cancel() stops the whole tree: SIGTERM to the process group, SIGKILL after
/// Installer.cancelGrace seconds, then `setup-mu-mac.sh --stop` for this prefix's wineserver and the lock.
final class InstallSession {
    private let line: (String) -> Void
    private let done: (Int32, Bool) -> Void
    private var child: ProcessGroupChild?
    private let splitter = LineSplitter()
    private(set) var cancelRequested = false   // main queue only

    init(line: @escaping (String) -> Void, done: @escaping (Int32, Bool) -> Void) { self.line = line; self.done = done }

    fileprivate func start(arguments: [String]) throws {
        child = try ProcessGroupChild(executable: "/bin/bash", arguments: arguments, environment: Installer.environment,
            output: { [splitter, line] data in splitter.feed(data) { l in DispatchQueue.main.async { line(l) } } },
            onExit: { [weak self] status in
                // Let the last output lines arrive first.
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                    guard let self, !self.cancelRequested else { return }
                    self.done(status, false)
                }
            })
    }

    var isRunning: Bool { child?.isRunning ?? false }
    var pid: pid_t? { child?.pid }

    /// Call on the main queue. `done(status, true)` follows once everything has stopped.
    func cancel() {
        guard !cancelRequested, let c = child, c.isRunning else { return }
        cancelRequested = true
        AppLog.write("install cancel: SIGTERM to process group \(c.pid)")
        c.signalGroup(SIGTERM)
        let grace = Installer.cancelGrace
        DispatchQueue.global(qos: .userInitiated).async { [line, done] in
            let deadline = Date().addingTimeInterval(grace)
            while c.isRunning && Date() < deadline { usleep(100_000) }
            if c.isRunning { AppLog.write("install cancel: still running after \(Int(grace)) s, SIGKILL") }
            c.signalGroup(SIGKILL)               // the leader if it ignored SIGTERM, and any straggler in the group
            while c.isRunning { usleep(50_000) }
            let out = Installer.stopLeftovers()
            AppLog.write("install cancel: clean-up\n" + out.trimmingCharacters(in: .newlines))
            DispatchQueue.main.async {
                for l in out.split(separator: "\n") { line(String(l)) }
                done(c.status ?? 143, true)
            }
        }
    }
}
