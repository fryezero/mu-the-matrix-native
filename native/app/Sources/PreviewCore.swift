// Mu The Matrix Native Preview.app (NATIVE-APP-001): settings, data discovery, the first-run data setup,
// the mu-client launch plan, logs and the child process. No AppKit here (main.swift has the UI), no network.
import Foundation

// ---------------------------------------------------------------- paths

enum Paths {
    static let home = FileManager.default.homeDirectoryForCurrentUser.path
    static let env = ProcessInfo.processInfo.environment

    /// Settings and the default Native Data folder (MU_NATIVE_SUPPORT_DIR overrides it, for tests).
    static var support: String {
        env["MU_NATIVE_SUPPORT_DIR"] ?? home + "/Library/Application Support/MuTheMatrixNative"
    }
    static var settingsFile: String { support + "/settings.json" }
    static var defaultNativeData: String { support + "/Native Data" }

    /// ~/Library/Logs/MuTheMatrixNative (MU_NATIVE_LOG_DIR overrides it).
    static var logs: String { env["MU_NATIVE_LOG_DIR"] ?? home + "/Library/Logs/MuTheMatrixNative" }

    /// The owner's free install (read-only). MU_NATIVE_GAME_ROOT replaces this default (tests).
    static var defaultGameRoot: String {
        env["MU_NATIVE_GAME_ROOT"] ?? home + "/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
    }
    /// Local plaintexts made by the repository's live readers (never in the repository or the bundle).
    static var defaultScratch: String {
        env["MU_NATIVE_SCRATCH"] ?? home + "/Documents/mu-mac-tools/native/scratch"
    }

    static var bundle: String { Bundle.main.bundlePath }
    static var contents: String { bundle + "/Contents" }
    static var resources: String { contents + "/Resources" }
    static var frameworks: String { contents + "/Frameworks" }
    static var client: String { contents + "/MacOS/mu-client" }
    static var nonet: String { frameworks + "/libmu-nonet.dylib" }
    static var mugfx: String { frameworks + "/libmugfx.dylib" }
    /// The offline demo session (MU_NATIVE_SESSION replaces it, for tests with synthetic data).
    static var session: String { env["MU_NATIVE_SESSION"] ?? resources + "/session/demo-session.txt" }
    static var placement: String { resources + "/world/lorencia-demo-placement.txt" }
    static var npcDemo: String { resources + "/world/lorencia-demo-npc.txt" }
    static var players: String { resources + "/world/lorencia-demo-players.txt" }   // NATIVE-HELPERS-001
    static var manifestTool: String { contents + "/MacOS/mu-native-data" }
    static var converter: String { contents + "/MacOS/gfxconvert" }

    static func exists(_ p: String) -> Bool { FileManager.default.fileExists(atPath: p) }
    static func isDir(_ p: String) -> Bool {
        var d: ObjCBool = false
        return FileManager.default.fileExists(atPath: p, isDirectory: &d) && d.boolValue
    }
    static func files(_ dir: String, _ match: (String) -> Bool) -> [String] {
        ((try? FileManager.default.contentsOfDirectory(atPath: dir)) ?? []).filter(match).sorted()
    }
}

// ---------------------------------------------------------------- log

enum AppLog {
    static let stamp: String = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyyMMdd-HHmmss"
        return f.string(from: Date())
    }()
    static var launcherLog: String { Paths.logs + "/launcher.log" }
    static var clientLog: String { Paths.logs + "/mu-client-\(stamp).log" }
    static var nonetReport: String { Paths.logs + "/nonet-\(stamp).json" }

    static func ensureDir() {
        try? FileManager.default.createDirectory(atPath: Paths.logs, withIntermediateDirectories: true)
    }

    /// One line in launcher.log (kept below 1 MB: the old half is dropped).
    static func write(_ line: String) {
        ensureDir()
        let f = ISO8601DateFormatter()
        let text = "\(f.string(from: Date())) \(line)\n"
        if let attrs = try? FileManager.default.attributesOfItem(atPath: launcherLog),
           let size = attrs[.size] as? Int, size > 1_000_000,
           let old = try? String(contentsOfFile: launcherLog, encoding: .utf8) {
            try? String(old.suffix(old.count / 2)).write(toFile: launcherLog, atomically: true, encoding: .utf8)
        }
        if let h = FileHandle(forWritingAtPath: launcherLog) {
            h.seekToEndOfFile()
            h.write(Data(text.utf8))
            h.closeFile()
        } else {
            try? text.write(toFile: launcherLog, atomically: true, encoding: .utf8)
        }
    }

    /// Keeps the newest `keep` client logs and guard reports.
    static func prune(keep: Int = 20) {
        for prefix in ["mu-client-", "nonet-"] {
            let names = Paths.files(Paths.logs) { $0.hasPrefix(prefix) }
            for name in names.dropLast(keep) { try? FileManager.default.removeItem(atPath: Paths.logs + "/" + name) }
        }
    }

    static func tail(_ path: String, lines: Int = 12) -> String {
        guard let text = try? String(contentsOfFile: path, encoding: .utf8) else { return "" }
        return text.split(separator: "\n", omittingEmptySubsequences: false).suffix(lines).joined(separator: "\n")
    }
}

// ---------------------------------------------------------------- settings

struct PreviewSettings: Codable, Equatable {
    var gameRoot: String? = nil       // nil: the free install (Paths.defaultGameRoot)
    var nativeData: String? = nil     // nil: Paths.defaultNativeData
    var scratch: String? = nil        // nil: Paths.defaultScratch
    var windowSize = "fit"            // "fit", "WxH" (points) or "full" (full screen; the window is resizable)
    var gfx = true                    // GFx interface (Ruffle), when the library and movies exist
    var combat = true                 // combat demo (mu-world --combat)
    var items = true                  // dropped items and labels
    var names = true                  // overhead names, HP bars, chat bubbles
    var npc = true                    // NPC talk, shop, vault (demo table)
    var env = true                    // ambient creatures and weather
    var particles = true              // particles, sprites, blob shadows
    var objects = true                // local decoded object placements
    var lang = true                   // local game text tables (MU_LANG_DIR)
    var sound = true                  // audio (world sound needs the local sound table)
    var players = true                // NATIVE-HELPERS-001: demo players in Lorencia, with their pets and mounts
    var helper = "none"               // NATIVE-HELPERS-001: the hero's helper (mu-client --helper, demo)

    static let featureKeys = ["gfx", "combat", "items", "names", "npc", "env", "particles", "objects", "lang", "sound",
                              "players"]
    static let helpers = ["none", "angel", "imp", "uniria", "dinorant", "darkhorse", "fenrir", "fenrir-black",
                          "fenrir-blue", "fenrir-gold",
                          "ghost-horse", "ice-dragon", "pierce-lion", "shining-tail", "ur", "leviathan", "tauros",
                          "divine-horse",
                          "dark-raven", "dark-raven-20", "dark-raven-40",
                          "demon", "spirit", "rudolph", "panda", "unicorn", "skeleton"]   // NATIVE-HELPERS-002 pets

    init() {}

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let d = PreviewSettings()
        gameRoot = try c.decodeIfPresent(String.self, forKey: .gameRoot)
        nativeData = try c.decodeIfPresent(String.self, forKey: .nativeData)
        scratch = try c.decodeIfPresent(String.self, forKey: .scratch)
        windowSize = try c.decodeIfPresent(String.self, forKey: .windowSize) ?? d.windowSize
        gfx = try c.decodeIfPresent(Bool.self, forKey: .gfx) ?? d.gfx
        combat = try c.decodeIfPresent(Bool.self, forKey: .combat) ?? d.combat
        items = try c.decodeIfPresent(Bool.self, forKey: .items) ?? d.items
        names = try c.decodeIfPresent(Bool.self, forKey: .names) ?? d.names
        npc = try c.decodeIfPresent(Bool.self, forKey: .npc) ?? d.npc
        env = try c.decodeIfPresent(Bool.self, forKey: .env) ?? d.env
        particles = try c.decodeIfPresent(Bool.self, forKey: .particles) ?? d.particles
        objects = try c.decodeIfPresent(Bool.self, forKey: .objects) ?? d.objects
        lang = try c.decodeIfPresent(Bool.self, forKey: .lang) ?? d.lang
        sound = try c.decodeIfPresent(Bool.self, forKey: .sound) ?? d.sound
        players = try c.decodeIfPresent(Bool.self, forKey: .players) ?? d.players
        helper = try c.decodeIfPresent(String.self, forKey: .helper) ?? d.helper
        if !Self.helpers.contains(helper) { helper = d.helper }
    }

    static func load() -> PreviewSettings {
        guard let data = FileManager.default.contents(atPath: Paths.settingsFile),
              let s = try? JSONDecoder().decode(PreviewSettings.self, from: data) else { return PreviewSettings() }
        return s
    }

    func save() {
        try? FileManager.default.createDirectory(atPath: Paths.support, withIntermediateDirectories: true)
        let e = JSONEncoder()
        e.outputFormatting = [.prettyPrinted, .sortedKeys]
        if let data = try? e.encode(self) { try? data.write(to: URL(fileURLWithPath: Paths.settingsFile), options: .atomic) }
    }

    var nativeDataDir: String { nativeData ?? Paths.defaultNativeData }
    var scratchDir: String { scratch ?? Paths.defaultScratch }

    func feature(_ key: String) -> Bool {
        switch key {
        case "gfx": return gfx
        case "combat": return combat
        case "items": return items
        case "names": return names
        case "npc": return npc
        case "env": return env
        case "particles": return particles
        case "objects": return objects
        case "lang": return lang
        case "sound": return sound
        case "players": return players
        default: return false
        }
    }

    mutating func setFeature(_ key: String, _ on: Bool) {
        switch key {
        case "gfx": gfx = on
        case "combat": combat = on
        case "items": items = on
        case "names": names = on
        case "npc": npc = on
        case "env": env = on
        case "particles": particles = on
        case "objects": objects = on
        case "lang": lang = on
        case "sound": sound = on
        case "players": players = on
        default: break
        }
    }
}

// ---------------------------------------------------------------- game data

enum GameData {
    /// A game folder: Data/Player/Player.bmd and a Data/World1 folder (what every scene loads first).
    static func valid(_ root: String) -> Bool {
        Paths.exists(root + "/Data/Player/Player.bmd") && Paths.isDir(root + "/Data/World1")
    }

    /// The remembered folder, else the free install; nil when neither is a game folder (the UI asks).
    static func resolve(_ s: PreviewSettings) -> String? {
        if let r = s.gameRoot, valid(r) { return r }
        if valid(Paths.defaultGameRoot) { return Paths.defaultGameRoot }
        return nil
    }
}

// ---------------------------------------------------------------- Native Data

enum DataManifest {
    static let name = "native-data.manifest"
    static func check(_ dir: String, gameRoot: String) -> String? {
        let r = DataSetup.run(Paths.manifestTool, ["check", dir, gameRoot + "/main.exe"])
        return r.status == 0 ? nil : r.output
    }
}


/// What the Native Data folder holds: lang/ (game text tables), objects/ (decoded EncTerrain<n>.plain),
/// gfx/ (converted GFx movies), sound/audio-tables.tsv; setup.json records the first-run setup.
struct NativeData {
    let dir: String
    var lang: String { dir + "/lang" }
    var objects: String { dir + "/objects" }
    var gfx: String { dir + "/gfx" }
    var soundTable: String { dir + "/sound/audio-tables.tsv" }
    var setupRecord: String { dir + "/setup.json" }

    var langFiles: [String] { Paths.files(lang) { $0.hasSuffix(".tsv") || $0.hasSuffix(".txt") } }
    var objectFiles: [String] { Paths.files(objects) { $0.hasPrefix("EncTerrain") && $0.hasSuffix(".plain") } }
    var movies: [String] { Paths.files(gfx) { $0.hasSuffix(".swf") } }
    var hasMovies: Bool { Paths.exists(gfx + "/base.swf") && Paths.exists(gfx + "/main.swf") }
    var hasSoundTable: Bool { Paths.exists(soundTable) }
    var setupDone: Bool { Paths.exists(setupRecord) }

    var summary: String {
        "GFx movies \(movies.count), text tables \(langFiles.count), object files \(objectFiles.count), "
            + "sound table \(hasSoundTable ? "yes" : "no")"
    }
}

/// The first-run setup: everything that needs no running game. The converter reads the game folder
/// (read-only) and writes only below Native Data; the plaintexts come from the scratch folder.
enum DataSetup {
    struct Step: Codable { var status: String; var files: Int; var source: String; var detail: String }

    static let converterOptions = ["--bridge", "--transparent", "--var", "_root.isClient=true", "--fontconfig",
                                   "English", "--font-subset", "latin"]

    static func run(settings s: PreviewSettings, gameRoot: String?, force: Bool, progress: (String) -> Void) -> [String: Step] {
        let nd = NativeData(dir: s.nativeDataDir)
        let fm = FileManager.default
        try? fm.createDirectory(atPath: nd.dir, withIntermediateDirectories: true)
        var result: [String: Step] = [:]
        let scratch = s.scratchDir
        guard let root = gameRoot else {
            return ["manifest": Step(status: "failed", files: 0, source: "", detail: "Native Data cannot be used: no game folder. Choose the installed client, then run Setup again.")]
        }
        let pin = run(Paths.manifestTool, ["pin", root + "/main.exe"])
        if pin.status != 0 { return ["manifest": Step(status: "failed", files: 0, source: root, detail: pin.output)] }
        // Never bless legacy, damaged or mismatched outputs, even with --force.
        if !Paths.files(nd.dir, { _ in true }).isEmpty {
            if let error = DataManifest.check(nd.dir, gameRoot: root) {
                return ["manifest": Step(status: "failed", files: 0, source: nd.dir, detail: error)]
            }
            if !force { return ["manifest": Step(status: "kept", files: 1, source: nd.dir, detail: "verified; run --force to regenerate")]
            }
        }
        // Reject unversioned exports before touching the destination.
        for src in [scratch + "/lang", scratch + "/objects/live/plain", scratch + "/audio/tables"] {
            if Paths.isDir(src) && !Paths.files(src, { _ in true }).isEmpty,
               let error = DataManifest.check(src, gameRoot: root) {
                return ["manifest": Step(status: "failed", files: 0, source: src, detail: error)]
            }
        }
        try? fm.removeItem(atPath: nd.dir + "/" + DataManifest.name)

        // 1. GFx movies: gfxconvert over the installed .ozg files, else copies of already converted movies.
        progress("Converting the game's interface movies (GFx → SWF)…")
        if !force && nd.hasMovies {
            result["gfx"] = Step(status: "kept", files: nd.movies.count, source: nd.gfx, detail: "already converted")
        } else {
            result["gfx"] = convertMovies(nd: nd, gameRoot: gameRoot, scratch: scratch)
        }

        // 2..4. Plaintexts and tables from the local readers (copies; the sources stay untouched).
        progress("Copying local game text tables…")
        result["lang"] = copyStep(from: scratch + "/lang", to: nd.lang, force: force) {
            ($0.hasSuffix(".tsv") || $0.hasSuffix(".txt"))
        }
        progress("Copying local object placements…")
        result["objects"] = copyStep(from: scratch + "/objects/live/plain", to: nd.objects, force: force) {
            $0.hasPrefix("EncTerrain") && ($0.hasSuffix(".plain") || $0.hasSuffix(".hidden") || $0.hasSuffix(".velocity"))
        }
        progress("Copying the local sound table…")
        result["sound"] = copyStep(from: scratch + "/audio/tables", to: nd.dir + "/sound", force: force) {
            $0 == "audio-tables.tsv"
        }

        var record: [String: Any] = ["version": 1, "date": ISO8601DateFormatter().string(from: Date()),
                                     "game_root": gameRoot ?? "", "scratch": scratch]
        for (k, v) in result {
            record[k] = ["status": v.status, "files": v.files, "source": v.source, "detail": v.detail]
        }
        if let data = try? JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: URL(fileURLWithPath: nd.setupRecord), options: .atomic)
        }
        for dir in [nd.gfx, nd.lang, nd.objects, nd.dir + "/sound"] where Paths.isDir(dir) {
            let r = run(Paths.manifestTool, ["check", dir, root + "/main.exe"])
            if r.status != 0 {
                result["component"] = Step(status: "failed", files: 0, source: dir, detail: r.output)
            }
        }
        let failed = result.values.contains { $0.status == "partial" || $0.status == "failed" || ($0.status == "missing" && $0.files != 0) }
        if !failed {
            var inputs = [root + "/main.exe"]
            for dir in [nd.gfx, nd.lang, nd.objects, nd.dir + "/sound"] where Paths.exists(dir + "/" + DataManifest.name) {
                inputs.append(dir + "/" + DataManifest.name)
            }
            let r = run(Paths.manifestTool, ["write", nd.dir, root + "/main.exe", "app-setup-v1"] + inputs)
            result["manifest"] = Step(status: r.status == 0 ? "written" : "failed", files: r.status == 0 ? 1 : 0, source: nd.dir, detail: r.output)
        } else {
            result["manifest"] = Step(status: "failed", files: 0, source: nd.dir, detail: "Native Data cannot be used: setup is incomplete. Re-acquire into a new folder and run Setup again.")
        }
        for (k, v) in result.sorted(by: { $0.key < $1.key }) {
            AppLog.write("setup \(k): \(v.status) files=\(v.files) source=\(v.source) \(v.detail)")
        }
        return result
    }

    static func copyStep(from src: String, to dst: String, force: Bool, match: (String) -> Bool) -> Step {
        let fm = FileManager.default
        let have = Paths.files(dst, match)
        if !force && !have.isEmpty { return Step(status: "kept", files: have.count, source: dst, detail: "already present") }
        let versioned = Paths.exists(src + "/" + DataManifest.name)
        let names = Paths.files(src) { name in
            var d: ObjCBool = false
            return (versioned || match(name)) && fm.fileExists(atPath: src + "/" + name, isDirectory: &d) && !d.boolValue
        }
        if names.isEmpty { return Step(status: "missing", files: 0, source: src, detail: "no local files (optional)") }
        try? fm.createDirectory(atPath: dst, withIntermediateDirectories: true)
        var copied = 0
        for name in names {
            let target = dst + "/" + name
            try? fm.removeItem(atPath: target)
            if (try? fm.copyItem(atPath: src + "/" + name, toPath: target)) != nil { copied += 1 }
        }
        return Step(status: copied == names.count ? "copied" : "partial", files: copied - (versioned ? 1 : 0), source: src, detail: "")
    }

    static func convertMovies(nd: NativeData, gameRoot: String?, scratch: String) -> Step {
        let fm = FileManager.default
        var why = ""
        if let root = gameRoot, Paths.isDir(root + "/Data/Interface/GFx"), Paths.exists(Paths.converter) {
            let tmp = nd.dir + "/gfx.converting"
            try? fm.removeItem(atPath: tmp)
            let r = run(Paths.converter, ["--root", root, "--out", tmp]
                        + converterOptions + ["--report", nd.dir + "/gfx-convert.json"])
            AppLog.write("gfxconvert (C) status \(r.status)\n" + String(r.output.suffix(4000)))
            let made = Paths.files(tmp) { $0.hasSuffix(".swf") }
            if r.status == 0 && Paths.exists(tmp + "/base.swf") && Paths.exists(tmp + "/main.swf") {
                let manifest = run(Paths.manifestTool, ["write", tmp, root + "/main.exe", "gfxconvert-app-v1-bridge-transparent-isClient-English-latin", root + "/Data/Interface/GFx"])
                if manifest.status != 0 {
                    try? fm.removeItem(atPath: tmp)
                    return Step(status: "failed", files: 0, source: root, detail: manifest.output)
                }
                do {
                    // Publish a complete conversion; keep the old set if installation fails.
                    if Paths.exists(nd.gfx) {
                        _ = try fm.replaceItemAt(URL(fileURLWithPath: nd.gfx),
                                                 withItemAt: URL(fileURLWithPath: tmp))
                    } else {
                        try fm.moveItem(atPath: tmp, toPath: nd.gfx)
                    }
                    return Step(status: "converted", files: made.count,
                                source: root + "/Data/Interface/GFx", detail: "bundled gfxconvert (C)")
                } catch {
                    why = "cannot install converted movies: \(error)"
                }
            } else {
                why = "gfxconvert failed (status \(r.status), see launcher.log)"
            }
            try? fm.removeItem(atPath: tmp)
        } else {
            why = gameRoot == nil ? "no game folder" : "no Data/Interface/GFx in the game folder"
        }
        // Fallback: movies converted earlier by the repository's tools (NATIVE-GFX-003 / NATIVE-NPC-001).
        if let root = gameRoot, Paths.isDir(root + "/Data/Interface/GFx") {
            return Step(status: "failed", files: 0, source: root, detail: why)
        }
        for src in [scratch + "/npc/movies", scratch + "/gfx3/movies"]
        where Paths.exists(src + "/base.swf") && Paths.exists(src + "/main.swf") {
            guard let root = gameRoot, DataManifest.check(src, gameRoot: root) == nil else {
                return Step(status: "failed", files: 0, source: src, detail: "Native Data cannot be used: converted movies need a matching manifest. Re-acquire them and run Setup again.")
            }
            let step = copyStep(from: src, to: nd.gfx, force: true) { $0.hasSuffix(".swf") }
            return Step(status: step.status, files: step.files, source: src, detail: "copied (\(why))")
        }
        return Step(status: "missing", files: 0, source: gameRoot ?? "", detail: why + "; the interface uses its stand-ins")
    }

    /// Runs a tool and returns its exit status and combined output.
    @discardableResult
    static func run(_ tool: String, _ args: [String], env extra: [String: String] = [:]) -> (status: Int32, output: String) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: tool)
        p.arguments = args
        var e = ProcessInfo.processInfo.environment
        for (k, v) in extra { e[k] = v }
        p.environment = e
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        p.standardInput = FileHandle.nullDevice
        do { try p.run() } catch { return (127, "\(error)") }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return (p.terminationStatus, String(decoding: data, as: UTF8.self))
    }
}

// ---------------------------------------------------------------- launch plan

struct LaunchPlan {
    var executable: String
    var args: [String]
    var env: [String: String]
    var notes: [String]

    static let label = "OFFLINE PREVIEW - no server connection"
    static let title = "Mu The Matrix Native Preview \u{2014} OFFLINE PREVIEW (no server connection)"

    /// Window size in points: the setting "WxH", or 16:10 fitting the screen's visible area (`screen`).
    static func windowSize(_ setting: String, screen: (Double, Double)?) -> (Int, Int) {
        let parts = setting.lowercased().split(separator: "x").compactMap { Int($0) }
        if parts.count == 2, parts[0] >= 640, parts[1] >= 400, parts[0] <= 8192, parts[1] <= 8192 { return (parts[0], parts[1]) }
        guard let (sw, sh) = screen, sw > 0, sh > 0 else { return (1280, 800) }
        var w = min(1600.0, (sw * 0.9).rounded(.down))
        var h = (w * 10 / 16).rounded(.down)
        let maxH = (sh - 28) * 0.92   // the window's title bar
        if h > maxH { h = maxH.rounded(.down); w = (h * 16 / 10).rounded(.down) }
        let wi = max(800, Int(w) / 8 * 8), hi = max(500, Int(h) / 8 * 8)
        return (wi, hi)
    }

    static func make(settings s: PreviewSettings, gameRoot: String, screen: (Double, Double)?) -> LaunchPlan {
        let nd = NativeData(dir: s.nativeDataDir)
        let (w, h) = windowSize(s.windowSize, screen: screen)
        var args = ["--game-root", gameRoot, "--session", Paths.session, "--width", String(w), "--height", String(h),
                    "--label", label, "--title", title]
        if s.windowSize == "full" { args.append("--fullscreen") }   // NATIVE-PERF-001
        // NATIVE-PERF-001: the client quits when this launcher is gone (killed), instead of running on alone
        var env: [String: String] = ["MU_NONET_REPORT": AppLog.nonetReport, "MU_EXIT_WITH_PARENT": "1"]
        var notes: [String] = []
        if Paths.exists(Paths.nonet) { env["DYLD_INSERT_LIBRARIES"] = Paths.nonet } else { notes.append("network guard missing") }

        args += ["--placement", Paths.placement]
        if s.npc { args += ["--npc", "--npc-demo", Paths.npcDemo] }
        if s.combat { args += ["--combat", "--progress"] }   // NATIVE-PROGRESS-001: kills give experience
        if s.items { args.append("--items") }
        if !s.names { args.append("--no-names") }
        if !s.env { args.append("--no-env") }
        if !s.particles { args.append("--no-particles") }
        if s.players { args += ["--players", Paths.players] }        // NATIVE-HELPERS-001
        if s.helper != "none" { args += ["--helper", s.helper] }

        // Objects per scene: the login world (95), character select (94) and the walk-around worlds; a scene
        // whose file is missing gets no option (character select refuses a folder without its file).
        if s.objects {
            let files = nd.objectFiles
            if files.contains("EncTerrain95.plain") { args += ["--login-objects", nd.objects] }
            if files.contains("EncTerrain94.plain") { args += ["--charsel-objects", nd.objects] }
            if files.contains(where: { $0 != "EncTerrain94.plain" && $0 != "EncTerrain95.plain" }) {
                args += ["--world-objects", nd.objects]
            }
            if files.isEmpty { notes.append("objects: no local EncTerrain*.plain (terrain only)") }
        }
        if s.lang && !nd.langFiles.isEmpty { env["MU_LANG_DIR"] = nd.lang }
        else if s.lang { notes.append("lang: no local text tables (placeholders)") }
        if !s.sound { args.append("--no-audio") }
        else if nd.hasSoundTable { args += ["--sound-table", nd.soundTable] }
        else { notes.append("sound: no local sound table (music only)") }

        if s.gfx {
            if !Paths.exists(Paths.mugfx) { notes.append("gfx: this build has no libmugfx (stand-ins)") }
            else if !nd.hasMovies { notes.append("gfx: no converted movies in Native Data (stand-ins)") }
            else {
                args += ["--gfx", nd.gfx]
                env["MU_GFX_LIB"] = Paths.mugfx
            }
        }
        if let extra = Paths.env["MU_NATIVE_EXTRA_ARGS"] {   // diagnostics: more mu-client options
            args += extra.split(separator: " ").map(String.init)
        }
        return LaunchPlan(executable: Paths.client, args: args, env: env, notes: notes)
    }

    var json: String {
        let obj: [String: Any] = ["executable": executable, "args": args, "env": env, "notes": notes]
        let data = (try? JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys])) ?? Data()
        return String(decoding: data, as: UTF8.self)
    }
}

// ---------------------------------------------------------------- the client process

final class ClientRun {
    let process = Process()
    let logPath: String
    let plan: LaunchPlan

    init(plan: LaunchPlan, logPath: String = AppLog.clientLog) {
        self.plan = plan
        self.logPath = logPath
    }

    /// Starts mu-client with stdout and stderr in its log; `done` runs on the main queue with
    /// (exit status, terminated by a signal).
    func start(extraArgs: [String] = [], done: @escaping (Int32, Bool) -> Void) throws {
        AppLog.ensureDir()
        FileManager.default.createFile(atPath: logPath, contents: nil)
        let log = FileHandle(forWritingAtPath: logPath)
        let header = "mu-client \(plan.args + extraArgs)\nenv \(plan.env)\nnotes \(plan.notes)\n\n"
        log?.write(Data(header.utf8))
        process.executableURL = URL(fileURLWithPath: plan.executable)
        process.arguments = plan.args + extraArgs
        var e = ProcessInfo.processInfo.environment
        for k in ["MU_GFX_LIB", "MU_LANG_DIR", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"] { e.removeValue(forKey: k) }
        for (k, v) in plan.env { e[k] = v }
        process.environment = e
        process.currentDirectoryURL = URL(fileURLWithPath: Paths.logs)   // mu-client's O screenshot lands here
        process.standardInput = FileHandle.nullDevice
        if let log { process.standardOutput = log; process.standardError = log }
        process.terminationHandler = { p in
            let signalled = p.terminationReason == .uncaughtSignal
            DispatchQueue.main.async { done(p.terminationStatus, signalled) }
        }
        try process.run()
        AppLog.write("started mu-client pid \(process.processIdentifier) log \(logPath)")
    }

    func stop() {
        if process.isRunning { process.terminate() }
    }
}

/// The guard's report: nil when the guard never loaded.
func readNonetReport(_ path: String) -> [String: Any]? {
    guard let data = FileManager.default.contents(atPath: path),
          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
    return obj
}

func nonetViolations(_ report: [String: Any]) -> Int {
    ["inet_denied", "other_denied", "connects_denied", "lookups_denied"].reduce(0) { $0 + ((report[$1] as? Int) ?? 0) }
}
