// Mu The Matrix Native Preview.app (NATIVE-APP-001): entry point, command-line modes and the AppKit UI.
//
// Double-click: find the game folder (the free install, else ask once), run the first-run data setup when the
// Native Data folder has none, then start the native client (mu-client) offline with every feature on and watch
// it: a crash or an error exit shows the log. Hold Option while opening the app for the settings window.
// Command line (no window): --print-settings, --print-plan, --setup [--force], --smoke, --check-bundle,
// --version, --help. Nothing here opens a network connection; mu-client runs under the mu-nonet guard.
import AppKit

let appVersion = (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "dev"

func fail(_ text: String, _ status: Int32 = 1) -> Never {
    FileHandle.standardError.write(Data((text + "\n").utf8))
    exit(status)
}

func option(_ args: [String], _ name: String) -> String? {
    guard let i = args.firstIndex(of: name), i + 1 < args.count else { return nil }
    return args[i + 1]
}

// ---------------------------------------------------------------- command line

/// --smoke: the launch path headless. Runs the setup when needed, then mu-client --headless --auto under the
/// guard; succeeds when the client exits 0 after reaching the world (scene 6) and the guard saw no network call.
func smoke(_ args: [String]) -> Int32 {
    let s = PreviewSettings.load()
    guard let root = GameData.resolve(s) else { fail("smoke: no game folder (set MU_NATIVE_GAME_ROOT or the settings)") }
    if !NativeData(dir: s.nativeDataDir).setupDone {
        _ = DataSetup.run(settings: s, gameRoot: root, force: false) { print("setup: \($0)") }
    }
    let plan = LaunchPlan.make(settings: s, gameRoot: root, screen: nil)
    var extra = ["--headless", "--backend", option(args, "--backend") ?? "soft", "--auto",
                 "--frames", option(args, "--frames") ?? "300", "--quiet"]
    if let size = option(args, "--size") {
        let wh = size.split(separator: "x")
        if wh.count == 2 { extra += ["--width", String(wh[0]), "--height", String(wh[1])] }
    }
    if let out = option(args, "--out-dir") { extra += ["--out-dir", out, "--every", option(args, "--every") ?? "50"] }
    if !args.contains("--audio") { extra.append("--no-audio") }
    let run = ClientRun(plan: plan)
    var finished = false, status: Int32 = 0, signalled = false
    do {
        try run.start(extraArgs: extra) { st, sig in status = st; signalled = sig; finished = true }
    } catch { fail("smoke: cannot start mu-client: \(error)") }
    let deadline = Date().addingTimeInterval(Double(option(args, "--timeout") ?? "300") ?? 300)
    while !finished && Date() < deadline { RunLoop.main.run(until: Date().addingTimeInterval(0.05)) }
    if !finished { run.stop(); fail("smoke: mu-client did not finish in time (log \(run.logPath))") }
    let log = (try? String(contentsOfFile: run.logPath, encoding: .utf8)) ?? ""
    let summaryLine = log.split(separator: "\n").last { $0.hasPrefix("{\"summary\"") }.map(String.init)
    var summary: [String: Any] = [:]
    if let line = summaryLine, let obj = try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any] {
        summary = obj
    }
    let transitions = (summary["transitions"] as? [String]) ?? []
    let reachedWorld = transitions.contains { $0.hasPrefix("4 -> 6") }
    let report = readNonetReport(AppLog.nonetReport)
    let guardOK = report != nil && (report?["phase"] as? String) == "exit" && nonetViolations(report!) == 0
    let ok = status == 0 && !signalled && reachedWorld && guardOK
    let result: [String: Any] = [
        "smoke": ok ? "ok" : "failed", "status": Int(status), "signalled": signalled, "reached_world": reachedWorld,
        "transitions": transitions, "renderer": summary["renderer"] ?? "", "nonet": report ?? [:],
        "plan": ["args": plan.args, "env": plan.env, "notes": plan.notes], "log": run.logPath,
    ]
    let data = (try? JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])) ?? Data()
    print(String(decoding: data, as: UTF8.self))
    AppLog.write("smoke \(ok ? "ok" : "failed") status \(status) world \(reachedWorld) guard \(guardOK)")
    return ok ? 0 : 1
}

/// --check-bundle: the files the app needs (the GFx library is optional).
func checkBundle() -> Int32 {
    let required = [Paths.client, Paths.nonet, Paths.session, Paths.resources + "/session/demo-servers.txt",
                    Paths.resources + "/session/demo-characters.txt", Paths.placement, Paths.npcDemo, Paths.converter,
                    Paths.resources + "/converter/native/gfx/gfxswf.py",
                    Paths.resources + "/converter/model-recovery/libmodulus.dylib", Paths.resources + "/AppIcon.icns"]
    let missing = required.filter { !Paths.exists($0) }
    for m in missing { print("missing: \(m)") }
    print("mu-client: \(Paths.exists(Paths.client) ? "bundled" : "MISSING")")
    print("network guard: \(Paths.exists(Paths.nonet) ? "bundled" : "MISSING")")
    print("GFx library (Ruffle): \(Paths.exists(Paths.mugfx) ? "bundled" : "not bundled (stand-ins)")")
    print(missing.isEmpty ? "bundle complete" : "bundle incomplete")
    return missing.isEmpty ? 0 : 1
}

let cliArgs = CommandLine.arguments.dropFirst().filter { !$0.hasPrefix("-psn_") && !$0.hasPrefix("-NS") && !$0.hasPrefix("-Apple") }
var guiSeconds: String? = nil
var guiSettings = false
if let first = cliArgs.first {
    let args = Array(cliArgs)
    switch first {
    case "--version":
        print("Mu The Matrix Native Preview \(appVersion)")
        exit(0)
    case "--help", "-h":
        print("""
        Mu The Matrix Native Preview \(appVersion): the native macOS client offline (no server connection).
          (no arguments)        open the app (hold Option for the settings window)
          --seconds S           open the app and close the client after S seconds
          --settings            open the settings window (as Option at launch)
          --print-settings      settings, folders and what Native Data holds
          --print-plan          the mu-client command line and environment the app would use (JSON)
          --setup [--force]     the first-run data setup (converted movies, local text, objects, sound table)
          --smoke [--backend soft|gl] [--frames N] [--size WxH] [--out-dir DIR]
                                headless run of the whole flow under the network guard; exit 0 when it reached the world
          --check-bundle        check the bundled files
        Environment: MU_NATIVE_SUPPORT_DIR, MU_NATIVE_LOG_DIR, MU_NATIVE_GAME_ROOT, MU_NATIVE_SCRATCH, MU_NATIVE_PYTHON,
          MU_NATIVE_SESSION (tests); MU_NATIVE_EXTRA_ARGS (more mu-client options, separated by spaces)
        """)
        exit(0)
    case "--print-settings":
        let s = PreviewSettings.load()
        let nd = NativeData(dir: s.nativeDataDir)
        print("settings file: \(Paths.settingsFile)\(Paths.exists(Paths.settingsFile) ? "" : " (missing; defaults)")")
        print("game folder: \(GameData.resolve(s) ?? "none (the app asks)")")
        print("native data: \(nd.dir) (\(nd.summary); setup \(nd.setupDone ? "done" : "not run"))")
        print("scratch: \(s.scratchDir)")
        print("window size: \(s.windowSize)")
        for k in PreviewSettings.featureKeys { print("\(k): \(s.feature(k) ? "on" : "off")") }
        print("logs: \(Paths.logs)")
        exit(0)
    case "--print-plan":
        let s = PreviewSettings.load()
        guard let root = GameData.resolve(s) else { fail("no game folder") }
        var screen: (Double, Double)? = nil
        if let sz = option(args, "--screen") {
            let wh = sz.split(separator: "x").compactMap { Double($0) }
            if wh.count == 2 { screen = (wh[0], wh[1]) }
        }
        print(LaunchPlan.make(settings: s, gameRoot: root, screen: screen).json)
        exit(0)
    case "--setup":
        let s = PreviewSettings.load()
        let r = DataSetup.run(settings: s, gameRoot: GameData.resolve(s), force: args.contains("--force")) { print($0) }
        for (k, v) in r.sorted(by: { $0.key < $1.key }) { print("\(k): \(v.status) (\(v.files) files) \(v.source) \(v.detail)") }
        exit(0)
    case "--smoke":
        exit(smoke(args))
    case "--check-bundle":
        exit(checkBundle())
    case "--seconds":
        guiSeconds = option(args, "--seconds")
    case "--settings":
        guiSettings = true
    default:
        fail("unknown option \(first) (see --help)", 2)
    }
}

// ---------------------------------------------------------------- UI

final class AppDelegate: NSObject, NSApplicationDelegate {
    var settings = PreviewSettings.load()
    var run: ClientRun?
    var window: NSWindow?
    var statusLabel: NSTextField?
    var signalSources: [DispatchSourceSignal] = []

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        AppLog.write("launch \(appVersion) bundle \(Paths.bundle)")
        AppLog.prune()
        for sig in [SIGTERM, SIGINT, SIGHUP] {
            signal(sig, SIG_IGN)
            // Not on the main queue: a modal alert would hold the signal back.
            let src = DispatchSource.makeSignalSource(signal: sig, queue: .global())
            src.setEventHandler { [weak self] in
                self?.run?.stop()
                AppLog.write("signal \(sig): stopped")
                exit(0)
            }
            src.resume()
            signalSources.append(src)
        }
        if guiSettings || NSEvent.modifierFlags.contains(.option) { showSettings(); return }
        proceed()
    }

    func applicationWillTerminate(_ note: Notification) { run?.stop() }
    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { run == nil }

    func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Settings…", action: #selector(menuSettings), keyEquivalent: ",")
        appMenu.addItem(withTitle: "Open Logs Folder", action: #selector(openLogs), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Mu The Matrix Native Preview", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        NSApp.mainMenu = main
    }

    @objc func menuSettings() { if run == nil { showSettings() } }
    @objc func openLogs() {
        AppLog.ensureDir()
        NSWorkspace.shared.open(URL(fileURLWithPath: Paths.logs))
    }

    // ---- flow: game folder -> setup -> client

    func proceed() {
        guard let root = resolveOrAsk() else { NSApp.terminate(nil); return }
        if !NativeData(dir: settings.nativeDataDir).setupDone {
            runSetup(force: false) { [weak self] in self?.launch(root) }
        } else {
            launch(root)
        }
    }

    func resolveOrAsk() -> String? {
        if let r = GameData.resolve(settings) { return r }
        while true {
            NSApp.activate(ignoringOtherApps: true)
            let panel = NSOpenPanel()
            panel.canChooseDirectories = true
            panel.canChooseFiles = false
            panel.allowsMultipleSelection = false
            panel.prompt = "Use This Folder"
            panel.message = "Choose the Mu The Matrix game folder (the folder that contains Data). It is only read."
            guard panel.runModal() == .OK, let url = panel.url else { return nil }
            if GameData.valid(url.path) {
                settings.gameRoot = url.path
                settings.save()
                AppLog.write("game folder chosen: \(url.path)")
                return url.path
            }
            let a = NSAlert()
            a.messageText = "This is not a Mu The Matrix game folder"
            a.informativeText = "\(url.path) has no Data/Player/Player.bmd and Data/World1. Choose the folder that contains Data."
            a.runModal()
        }
    }

    func runSetup(force: Bool, then: @escaping () -> Void) {
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 460, height: 120), styleMask: [.titled], backing: .buffered, defer: false)
        w.title = "Mu The Matrix Native Preview — preparing local data"
        let spinner = NSProgressIndicator(frame: NSRect(x: 20, y: 52, width: 32, height: 32))
        spinner.style = .spinning
        spinner.startAnimation(nil)
        let label = NSTextField(wrappingLabelWithString: "Preparing…")
        label.frame = NSRect(x: 64, y: 44, width: 376, height: 56)
        let hint = NSTextField(wrappingLabelWithString: "macOS may ask to let the app read the local tables in the "
                               + "Documents folder (\(settings.scratchDir)); Don't Allow skips them.")
        hint.frame = NSRect(x: 20, y: 6, width: 420, height: 34)
        hint.font = .systemFont(ofSize: NSFont.smallSystemFontSize)
        hint.textColor = .secondaryLabelColor
        w.contentView?.addSubview(hint)
        w.contentView?.addSubview(spinner)
        w.contentView?.addSubview(label)
        w.center()
        w.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        let s = settings
        let root = GameData.resolve(s)
        DispatchQueue.global(qos: .userInitiated).async {
            _ = DataSetup.run(settings: s, gameRoot: root, force: force) { text in
                DispatchQueue.main.async { label.stringValue = text }
            }
            DispatchQueue.main.async { w.orderOut(nil); then() }
        }
        window = w
    }

    func launch(_ root: String) {
        let size = NSScreen.main.map { ($0.visibleFrame.width, $0.visibleFrame.height) }.map { (Double($0.0), Double($0.1)) }
        let plan = LaunchPlan.make(settings: settings, gameRoot: root, screen: size)
        AppLog.write("plan \(plan.args) env \(plan.env) notes \(plan.notes)")
        let r = ClientRun(plan: plan)
        do {
            try r.start(extraArgs: guiSeconds.map { ["--seconds", $0] } ?? []) { [weak self] status, signalled in
                self?.clientEnded(status: status, signalled: signalled)
            }
        } catch {
            showFailure("The native client could not start: \(error)", log: r.logPath)
            return
        }
        run = r
        window?.orderOut(nil)
        // The client is its own app process (its executable is in this bundle); the launcher only watches it.
        NSApp.setActivationPolicy(.accessory)
    }

    func clientEnded(status: Int32, signalled: Bool) {
        let log = run?.logPath ?? AppLog.clientLog
        let report = readNonetReport(AppLog.nonetReport)
        let blocked = report.map(nonetViolations) ?? 0
        AppLog.write("mu-client ended status \(status)\(signalled ? " (signal)" : "") guard \(report.map { "\($0)" } ?? "no report") ")
        run = nil
        if status == 0 && !signalled {
            NSApp.terminate(nil)
            return
        }
        let what = signalled ? "stopped by signal \(status) (a crash)" : "exited with status \(status)"
        showFailure("The native client \(what).\(blocked > 0 ? " The network guard refused \(blocked) network call(s)." : "")", log: log)
    }

    func showFailure(_ text: String, log: String) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
        let a = NSAlert()
        a.alertStyle = .warning
        a.messageText = "Mu The Matrix Native Preview stopped"
        let tail = AppLog.tail(log, lines: 10)
        a.informativeText = "\(text)\n\nLog: \(log)\n\n\(tail)"
        a.addButton(withTitle: "Quit")
        a.addButton(withTitle: "Show Log")
        a.addButton(withTitle: "Settings…")
        switch a.runModal() {
        case .alertSecondButtonReturn:
            NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: log)])
            NSApp.terminate(nil)
        case .alertThirdButtonReturn:
            showSettings()
        default:
            NSApp.terminate(nil)
        }
    }

    // ---- settings window (Option at launch, or after a failure)

    var gameLabel = NSTextField(labelWithString: "")
    var dataLabel = NSTextField(labelWithString: "")
    var dataSummary = NSTextField(labelWithString: "")
    var sizePopup = NSPopUpButton()
    var boxes: [String: NSButton] = [:]
    static let sizes = ["fit", "1024x640", "1280x800", "1440x900", "1600x1000", "1920x1200"]
    static let featureTitles: [(String, String)] = [
        ("gfx", "GFx interface (Ruffle; stand-ins without it)"), ("combat", "Combat demo"), ("items", "Dropped items and labels"),
        ("names", "Overhead names and HP bars"), ("npc", "NPC talk, shop and vault (demo)"), ("env", "Ambient creatures and weather"),
        ("particles", "Particles, sprites and shadows"), ("objects", "World objects (local decoded placements)"),
        ("lang", "Game text (local tables)"), ("sound", "Sound"),
    ]

    func refreshLabels() {
        gameLabel.stringValue = GameData.resolve(settings) ?? "not found — choose the game folder"
        dataLabel.stringValue = settings.nativeDataDir
        let nd = NativeData(dir: settings.nativeDataDir)
        dataSummary.stringValue = nd.summary + (Paths.exists(Paths.mugfx) ? "" : " · this build has no GFx library")
    }

    func showSettings() {
        NSApp.setActivationPolicy(.regular)
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 560), styleMask: [.titled, .closable],
                         backing: .buffered, defer: false)
        w.title = "Mu The Matrix Native Preview — Settings (OFFLINE PREVIEW, no server connection)"
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 8
        stack.edgeInsets = NSEdgeInsets(top: 16, left: 20, bottom: 16, right: 20)

        func row(_ title: String, _ value: NSTextField, _ buttons: [NSButton]) -> NSView {
            let t = NSTextField(labelWithString: title)
            t.font = .boldSystemFont(ofSize: NSFont.systemFontSize)
            value.lineBreakMode = .byTruncatingMiddle
            value.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
            value.widthAnchor.constraint(lessThanOrEqualToConstant: 340).isActive = true
            let h = NSStackView(views: [t, value] + buttons)
            h.orientation = .horizontal
            return h
        }
        let chooseGame = NSButton(title: "Choose…", target: self, action: #selector(chooseGame))
        let chooseData = NSButton(title: "Choose…", target: self, action: #selector(chooseData))
        let rerun = NSButton(title: "Prepare again", target: self, action: #selector(rerunSetup))
        stack.addArrangedSubview(row("Game folder (read-only):", gameLabel, [chooseGame]))
        stack.addArrangedSubview(row("Native Data folder:", dataLabel, [chooseData, rerun]))
        dataSummary.textColor = .secondaryLabelColor
        stack.addArrangedSubview(dataSummary)

        sizePopup = NSPopUpButton()
        for s in Self.sizes { sizePopup.addItem(withTitle: s == "fit" ? "Fit the screen" : s.replacingOccurrences(of: "x", with: " × ")) }
        sizePopup.selectItem(at: Self.sizes.firstIndex(of: settings.windowSize) ?? 0)
        let sizeRow = NSStackView(views: [NSTextField(labelWithString: "Window size:"), sizePopup])
        stack.addArrangedSubview(sizeRow)

        let featureLabel = NSTextField(labelWithString: "Features:")
        featureLabel.font = .boldSystemFont(ofSize: NSFont.systemFontSize)
        stack.addArrangedSubview(featureLabel)
        for (key, title) in Self.featureTitles {
            let b = NSButton(checkboxWithTitle: title, target: nil, action: nil)
            b.state = settings.feature(key) ? .on : .off
            boxes[key] = b
            stack.addArrangedSubview(b)
        }
        let note = NSTextField(wrappingLabelWithString: "Offline preview of the native port: the server list, login and characters are a local demo, nothing is sent anywhere. Logs: \(Paths.logs)")
        note.textColor = .secondaryLabelColor
        note.preferredMaxLayoutWidth = 600
        stack.addArrangedSubview(note)

        let quit = NSButton(title: "Quit", target: NSApp, action: #selector(NSApplication.terminate(_:)))
        let logs = NSButton(title: "Open Logs", target: self, action: #selector(openLogs))
        let save = NSButton(title: "Save", target: self, action: #selector(saveSettings))
        let launchButton = NSButton(title: "Launch", target: self, action: #selector(saveAndLaunch))
        launchButton.keyEquivalent = "\r"
        let buttons = NSStackView(views: [quit, logs, save, launchButton])
        stack.addArrangedSubview(buttons)

        refreshLabels()
        w.contentView = stack
        w.center()
        w.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        window = w
    }

    func collect() {
        settings.windowSize = Self.sizes[max(0, sizePopup.indexOfSelectedItem)]
        for (k, b) in boxes { settings.setFeature(k, b.state == .on) }
    }

    @objc func chooseGame() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.message = "Choose the Mu The Matrix game folder (the folder that contains Data). It is only read."
        if panel.runModal() == .OK, let url = panel.url {
            if GameData.valid(url.path) { settings.gameRoot = url.path } else {
                let a = NSAlert()
                a.messageText = "This is not a Mu The Matrix game folder"
                a.informativeText = "\(url.path) has no Data/Player/Player.bmd and Data/World1."
                a.runModal()
            }
        }
        refreshLabels()
    }

    @objc func chooseData() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.message = "Choose the Native Data folder (local converted movies, text tables and object placements)."
        if panel.runModal() == .OK, let url = panel.url { settings.nativeData = url.path }
        refreshLabels()
    }

    @objc func rerunSetup() {
        collect()
        settings.save()
        let w = window
        w?.orderOut(nil)
        runSetup(force: true) { [weak self] in
            guard let self else { return }
            self.refreshLabels()
            self.window = w
            w?.makeKeyAndOrderFront(nil)
        }
    }

    @objc func saveSettings() {
        collect()
        settings.save()
        AppLog.write("settings saved")
    }

    @objc func saveAndLaunch() {
        saveSettings()
        window?.orderOut(nil)
        proceed()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
