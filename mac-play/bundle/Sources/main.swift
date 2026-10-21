// Mu The Matrix.app (MAC-BUNDLE-001): entry point, command-line modes and the AppKit UI.
//
// Double-click: start the launcher (free Wine runtime by default, or a CrossOver bottle) and quit. Outside the Applications folder
// (the disk image, Downloads) it first offers to copy itself there and open again. Before the game is installed it shows one
// install window (Install, then the game starts by itself). The settings window opens when Option is held, from the menu,
// when "Start right away" is off, or after an error.
// Command line (no window): --dry-run, --check, --status, --install, --install-dry-run, --check-bundle, --rosetta-status,
// --install-rosetta, --fps-counter, --print-settings, --settings-path, --version, --help.
import AppKit

let appVersion = (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "dev"

// ---------------------------------------------------------------- command line
let cliArgs = CommandLine.arguments.dropFirst().filter { !$0.hasPrefix("-psn_") && !$0.hasPrefix("-NS") && !$0.hasPrefix("-Apple") }
if let arg = cliArgs.first {
    let s = LauncherSettings.load()
    switch arg {
    case "--dry-run", "--check":
        let r = LaunchScript.run(arg, settings: s)
        print(r.output, terminator: r.output.hasSuffix("\n") || r.output.isEmpty ? "" : "\n")
        AppLog.write("cli \(arg) runtime=\(s.runtime) bottle=\(s.bottle) fastX87=\(s.fastX87) resolution=\(s.resolution.isEmpty ? "keep" : s.resolution) -> status \(r.status)")
        exit(r.status)
    case "--print-settings":
        print("settings file: \(LauncherSettings.fileURL.path)\(LauncherSettings.fileExists ? "" : " (missing; defaults)")")
        for k in LauncherSettings.keys { print("\(k) = \(s.dictionary[k]!)") }
        print("log directory: \(AppLog.directory.path)")
        exit(0)
    case "--status":
        let st = LaunchScript.freeStatus()
        print("free runtime: \(st.runtime ? "installed" : "missing")\nprefix: \(st.prefix ? "ok" : "missing")\ngame: \(st.game ? "installed" : "missing")")
        exit(st.runtime && st.prefix && st.game ? 0 : 1)
    case "--install-dry-run", "--install":
        // Headless install (what the Install window runs); --install-dry-run prints the plan and changes nothing.
        // Ctrl-C (SIGINT) or SIGTERM cancels like the window's Cancel button: the installer runs in its own process
        // group, so the app forwards the cancel to the whole tree and cleans up.
        var rest = Array(cliArgs.dropFirst()), runtimeArchive: String?
        if let i = rest.firstIndex(of: "--runtime-archive") {
            guard i + 1 < rest.count else { FileHandle.standardError.write(Data("--runtime-archive needs a file\n".utf8)); exit(2) }
            runtimeArchive = rest[i + 1]; rest.removeSubrange(i...(i + 1))
        }
        let gameDir = rest.first
        var finished = false, status: Int32 = 0
        AppLog.write("cli \(arg) source=\(gameDir ?? "official installer") runtime=\(runtimeArchive ?? "default")")
        let meter = DownloadMeter(); var lastProgress = Date.distantPast
        let session = Installer.start(gameDir: gameDir, runtimeArchive: runtimeArchive, dryRun: arg == "--install-dry-run", line: { l in
            if meter.feed(l) {
                // One condensed progress line every 15 seconds instead of one per second.
                guard Date().timeIntervalSince(lastProgress) >= 15 else { return }
                lastProgress = Date(); print("downloading \(meter.name): \(meter.summary)")
            } else { print(l) }
            fflush(stdout)
        }, done: { st, cancelled in
            status = cancelled ? 130 : st; finished = true
            if cancelled { print("The installation was cancelled. Run it again to continue where it stopped.") }
            AppLog.write("cli \(arg) finished status \(st)\(cancelled ? " (cancelled)" : "")")
        })
        var signalSources: [DispatchSourceSignal] = []
        for sig in [SIGINT, SIGTERM, SIGHUP] {
            signal(sig, SIG_IGN)
            let src = DispatchSource.makeSignalSource(signal: sig, queue: .main)
            src.setEventHandler { FileHandle.standardError.write(Data("Stopping the installation…\n".utf8)); session?.cancel() }
            src.resume(); signalSources.append(src)
        }
        withExtendedLifetime(signalSources) {
            while !finished { RunLoop.main.run(until: Date().addingTimeInterval(0.05)) }
        }
        exit(status)
    case "--check-bundle":
        // A player build (make player-app) bundles mugl, the mscoree proxy, the fast x87 translator and the runtime.
        let missing = Installer.missingEmbeds
        if missing.isEmpty, let rt = Installer.bundledRuntime {
            guard RuntimeFile.isTested(rt.path) else {
                print("bundle damaged: \(rt.lastPathComponent) does not have the pinned SHA-256 \(RuntimeFile.testedSHA256)"); exit(1)
            }
            print("bundle complete: mugl, mscoree proxy, fast x87 and the Wine runtime (SHA-256 checked) are bundled"); exit(0)
        }
        print("bundle incomplete: missing " + missing.joined(separator: ", "))
        print("Build the app for players with: make player-app EMBED_MUGL=... EMBED_MSCOREE=... EMBED_FAST_X87=... EMBED_RUNTIME=...")
        exit(1)
    case "--rosetta-status":
        let ok = Rosetta.isInstalled()
        print(ok ? "rosetta: installed" : "rosetta: missing (\(Rosetta.terminalCommand))"); exit(ok ? 0 : 1)
    case "--install-rosetta":
        if Rosetta.isInstalled() { print("rosetta: already installed"); exit(0) }
        let r = Rosetta.install()
        AppLog.write("cli --install-rosetta ok=\(r.ok) declined=\(r.declined)\n\(r.output)")
        if !r.output.isEmpty { print(r.output) }
        print(r.ok ? "rosetta: installed" : r.declined ? "rosetta: not installed (the administrator prompt was cancelled)" : "rosetta: install failed")
        exit(r.ok ? 0 : 1)
    case "--fps-counter":
        // Show or hide the in-game FPS counter for the configured prefix/bottle (no option: print the state).
        let want: Bool?
        switch cliArgs.dropFirst().first {
        case nil: want = nil
        case "on": want = true
        case "off": want = false
        case let v?: FileHandle.standardError.write(Data("--fps-counter takes on or off, not \(v)\n".utf8)); exit(2)
        }
        guard let state = LaunchScript.fpsCounter(want, settings: s) else { print("fps-counter unavailable (install the game first)"); exit(1) }
        print("fps-counter \(state ? "on" : "off")"); exit(0)
    case "--location":
        // Where the app runs from, and whether it would offer to move itself to Applications (tests, support).
        let (orig, translocated) = AppMover.origin(of: Bundle.main.bundleURL)
        print("app: \(orig.path)\(translocated ? " (translocated)" : "")")
        print("in Applications: \(AppMover.targets.contains { AppMover.isInside(orig, $0) } ? "yes" : "no")")
        print("read-only volume: \(AppMover.readOnlyVolume(of: orig)?.path ?? "no")")
        exit(0)
    case "--move-to-applications":
        // The copy step of "Move to Applications" without the dialog and the relaunch (tests).
        do {
            let dest = try AppMover.copyToApplications(from: Bundle.main.bundleURL, name: Bundle.main.bundleURL.lastPathComponent)
            print("copied to \(dest.path)"); exit(0)
        } catch { print("move failed: \(error.localizedDescription)"); exit(1) }
    case "--settings-path": print(LauncherSettings.fileURL.path); exit(0)
    case "--version": print("Mu The Matrix.app \(appVersion)"); exit(0)
    case "--help", "-h":
        print("""
        Mu The Matrix.app \(appVersion): installs and starts Mu The Matrix (free Wine runtime, or a CrossOver bottle).
          (no option)       open the app (double-click behaviour)
          --dry-run         preflight and print what a start would do; changes nothing
          --check           preflight only
          --status          free runtime install state (exit 0 when ready)
          --install [--runtime-archive FILE] [GAME_DIR]
                            install without a window (default: download the official game; the Wine runtime
                            bundled in the app; --runtime-archive: use another Wine runtime file instead)
          --install-dry-run [--runtime-archive FILE] [GAME_DIR]  print the installer's plan; changes nothing
          --check-bundle    exit 0 when mugl, the mscoree proxy, fast x87 and the pinned Wine runtime are bundled
          --rosetta-status  exit 0 when Rosetta 2 is installed
          --install-rosetta install Rosetta 2 (asks for administrator approval)
          --fps-counter [on|off]  show or hide the in-game FPS counter (also while the game runs)
          --location        where the app runs from and whether it is in an Applications folder
          --move-to-applications  copy the app into Applications (what "Move to Applications" does, without relaunch)
          --print-settings  show the effective settings and file locations
          --settings-path   print the settings plist path
          --version
        Environment: MU_SETTINGS_FILE, MU_LOG_DIR, MU_LAUNCH_SCRIPT, MU_SETUP_SCRIPT, MUKIT_FREE_HOME, CX_ROOT, MUKIT_BOTTLES_DIR,
          MU_CANCEL_GRACE, MU_ROSETTA_CHECK, MU_ROSETTA_INSTALL, MU_APPLICATIONS_DIR (where "Move to Applications"
          copies the app; testing), MU_SKIP_MOVE=1 (no move offer; development builds).
        """)
        exit(0)
    default:
        FileHandle.standardError.write(Data("unknown option \(arg); see --help\n".utf8))
        exit(2)
    }
}

// ---------------------------------------------------------------- UI helpers
func label(_ text: String, small: Bool = false) -> NSTextField {
    let l = NSTextField(labelWithString: text)
    if small { l.font = .systemFont(ofSize: NSFont.smallSystemFontSize); l.textColor = .secondaryLabelColor }
    l.lineBreakMode = .byWordWrapping
    l.maximumNumberOfLines = 0
    return l
}

func openLog() {
    let fm = FileManager.default
    try? fm.createDirectory(at: AppLog.directory, withIntermediateDirectories: true)
    if !fm.fileExists(atPath: AppLog.url.path) { AppLog.write("log created") }
    NSWorkspace.shared.activateFileViewerSelecting([AppLog.url])
}

// ---------------------------------------------------------------- settings window
final class SettingsWindowController: NSWindowController {
    var onPlay: ((LauncherSettings) -> Void)?
    private var settings: LauncherSettings
    var onInstall: (() -> Void)?
    private let runtimePopup = NSPopUpButton()
    private let installState = label("", small: true)
    private lazy var installButton = NSButton(title: "Install…", target: self, action: #selector(install))
    private let bottlePopup = NSPopUpButton()
    private let resolutionPopup = NSPopUpButton()
    private let modesNote = label("", small: true)
    private let fastCheck = NSButton(checkboxWithTitle: "Run main.exe through rosetta-timewalker (fast x87 math)", target: nil, action: nil)
    private let twPath = label("")
    private let twNote = label("", small: true)
    private let fpsCheck = NSButton(checkboxWithTitle: "Show the FPS counter in the game", target: nil, action: nil)
    private let startCheck = NSButton(checkboxWithTitle: "Start the game right away when the app opens", target: nil, action: nil)
    private let startNote = label("Hold ⌥ Option while opening the app to see this window again.", small: true)
    private let status = label("", small: true)
    private var bottleNames: [String] = []
    private var grid: NSGridView?

    init(settings: LauncherSettings) {
        self.settings = settings
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 600, height: 400), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        w.title = "Mu The Matrix"
        super.init(window: w)
        build()
        load()
        w.center()
    }
    required init?(coder: NSCoder) { fatalError("not used") }

    private func build() {
        guard let content = window?.contentView else { return }
        let icon = NSImageView(image: NSApp.applicationIconImage)
        icon.imageScaling = .scaleProportionallyUpOrDown
        icon.widthAnchor.constraint(equalToConstant: 64).isActive = true
        icon.heightAnchor.constraint(equalToConstant: 64).isActive = true
        let title = label("Mu The Matrix")
        title.font = .boldSystemFont(ofSize: 17)
        let subtitle = label("Installs and starts the original launcher. No CrossOver needed: the free Wine runtime is the default. Settings are saved in \(LauncherSettings.fileURL.path).", small: true)
        subtitle.preferredMaxLayoutWidth = 470
        let head = NSStackView(views: [icon, NSStackView(views: [title, subtitle])])
        (head.views[1] as? NSStackView)?.orientation = .vertical
        (head.views[1] as? NSStackView)?.alignment = .leading
        head.alignment = .centerY

        runtimePopup.addItems(withTitles: ["Free Wine runtime (recommended, no CrossOver)", "CrossOver bottle (legacy, needs CrossOver)"])
        runtimePopup.target = self; runtimePopup.action = #selector(runtimeChanged)
        installState.preferredMaxLayoutWidth = 340
        let installRow = NSStackView(views: [installState, installButton])
        installRow.widthAnchor.constraint(equalToConstant: 440).isActive = true
        bottlePopup.target = self; bottlePopup.action = #selector(bottleChanged)
        fastCheck.target = self; fastCheck.action = #selector(fastChanged)
        fpsCheck.target = self; fpsCheck.action = #selector(fpsChanged)
        fpsCheck.toolTip = "Frames per second and frame time in the top-left corner. Takes effect within a second, also while the game runs."
        twPath.maximumNumberOfLines = 1
        twPath.lineBreakMode = .byTruncatingMiddle
        twPath.setContentHuggingPriority(.defaultLow, for: .horizontal)
        twPath.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        for note in [modesNote, twNote, startNote] { note.preferredMaxLayoutWidth = 440 }
        let choose = NSButton(title: "Choose…", target: self, action: #selector(chooseTimewalker))
        let auto = NSButton(title: "Auto", target: self, action: #selector(autoTimewalker))
        auto.toolTip = "Use the validated cache of mac-play/install-fast-x87.sh"
        let twRow = NSStackView(views: [twPath, choose, auto])

        let grid = NSGridView(views: [
            [label("Runtime:"), runtimePopup],
            [label("Game:"), installRow],
            [label("Bottle:"), bottlePopup],
            [label("Resolution:"), resolutionPopup],
            [NSGridCell.emptyContentView, modesNote],
            [label("Fast x87:"), fastCheck],
            [label("Timewalker:"), twRow],
            [NSGridCell.emptyContentView, twNote],
            [label("FPS counter:"), fpsCheck],
            [NSGridCell.emptyContentView, startCheck],
            [NSGridCell.emptyContentView, startNote],
        ])
        self.grid = grid
        grid.column(at: 0).xPlacement = .trailing
        grid.rowSpacing = 8
        grid.columnSpacing = 8
        grid.column(at: 1).width = 440
        twRow.widthAnchor.constraint(equalToConstant: 440).isActive = true

        let logButton = NSButton(title: "Open Log", target: self, action: #selector(showLog))
        let quit = NSButton(title: "Quit", target: NSApp, action: #selector(NSApplication.terminate(_:)))
        let save = NSButton(title: "Save", target: self, action: #selector(saveOnly))
        let play = NSButton(title: "Play", target: self, action: #selector(play))
        play.keyEquivalent = "\r"
        quit.keyEquivalent = "\u{1b}"
        let spacer = NSView()
        spacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let buttons = NSStackView(views: [logButton, spacer, quit, save, play])

        let stack = NSStackView(views: [head, grid, status, buttons])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 14
        stack.edgeInsets = NSEdgeInsets(top: 18, left: 20, bottom: 18, right: 20)
        stack.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            stack.topAnchor.constraint(equalTo: content.topAnchor),
            stack.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            buttons.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
            status.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
        ])
    }

    private func load() {
        bottlePopup.removeAllItems()
        bottleNames = []
        let found = LaunchScript.bottles()
        for b in found {
            var t = b.name
            if b.arch != "win32" { t += "  (not 32-bit)" } else if !b.hasGame { t += "  (no game)" }
            bottlePopup.addItem(withTitle: t); bottleNames.append(b.name)
        }
        if !bottleNames.contains(settings.bottle) {
            bottlePopup.addItem(withTitle: "\(settings.bottle)  (missing)"); bottleNames.append(settings.bottle)
        }
        bottlePopup.selectItem(at: bottleNames.firstIndex(of: settings.bottle) ?? 0)
        runtimePopup.selectItem(at: settings.runtime == "crossover" ? 1 : 0)
        refreshRuntime()
        fastCheck.state = settings.fastX87 ? .on : .off
        startCheck.state = settings.startImmediately ? .on : .off
        refreshTimewalker()
        refreshModes()
        refreshFPS()
    }

    /// The checkbox mirrors C:\mutools\mugl-fps.txt of the selected prefix/bottle (also toggled in game).
    private func refreshFPS() {
        let state = LaunchScript.fpsCounter(settings: collect())
        fpsCheck.isEnabled = state != nil
        fpsCheck.state = state == true ? .on : .off
    }
    @objc private func fpsChanged() {
        let on = fpsCheck.state == .on
        let state = LaunchScript.fpsCounter(on, settings: collect())
        AppLog.write("fps counter \(on ? "on" : "off") -> \(state.map { $0 ? "on" : "off" } ?? "failed")")
        if state == nil { status.stringValue = "Could not change the FPS counter: install the game first." }
        refreshFPS()
    }

    private func refreshTimewalker() {
        let p = (settings.timewalkerDir as NSString).expandingTildeInPath
        twPath.stringValue = p.isEmpty ? "Auto" : p
        twPath.toolTip = p.isEmpty ? nil : p
        twNote.stringValue = p.isEmpty ? "Auto uses the validated cache of mac-play/install-fast-x87.sh."
            : "Runs scripts/run-crossover.sh from this folder with TIMEWALKER_X87_ONLY=main.exe."
        twPath.textColor = fastCheck.state == .on ? .labelColor : .disabledControlTextColor
    }

    private var isFree: Bool { runtimePopup.indexOfSelectedItem != 1 }

    func refreshRuntime() {
        bottlePopup.isEnabled = !isFree
        installButton.isHidden = !isFree
        if isFree {
            let st = LaunchScript.freeStatus()
            let ready = st.runtime && st.prefix && st.game
            installState.stringValue = ready ? "Installed (free runtime, ~/Library/Application Support/MuTheMatrix)."
                : "Not installed yet. Click Install… (downloads Wine, .NET 4.8 and the game; about 10 minutes plus the game download)."
            installButton.title = ready ? "Repair…" : "Install…"
        } else {
            installState.stringValue = "Uses a CrossOver bottle chosen below."
        }
        fastCheck.isEnabled = true
        // Rows 2 (Bottle), 6 and 7 (Timewalker folder and note) only apply to the CrossOver runtime.
        for r in [2, 6, 7] where r < (grid?.numberOfRows ?? 0) { grid?.row(at: r).isHidden = isFree }
        fastCheck.title = isFree ? "Fast x87 math for main.exe (rosetta-timewalker; used when installed)"
                                 : "Run main.exe through rosetta-timewalker (fast x87 math)"
    }

    private func refreshModes() {
        let bottle = bottleNames.isEmpty ? settings.bottle : bottleNames[bottlePopup.indexOfSelectedItem]
        let m = LaunchScript.modes(runtime: isFree ? "free" : "crossover", bottle: bottle)
        resolutionPopup.removeAllItems()
        resolutionPopup.addItem(withTitle: "Keep launcher setting")
        for (i, mode) in m.modes.enumerated() {
            resolutionPopup.addItem(withTitle: mode.replacingOccurrences(of: "x", with: " × ") + (i == m.current ? "  (current)" : ""))
            resolutionPopup.lastItem?.representedObject = mode
        }
        if !settings.resolution.isEmpty, !m.modes.contains(settings.resolution) {
            resolutionPopup.addItem(withTitle: "\(settings.resolution)  (not in this bottle)")
            resolutionPopup.lastItem?.representedObject = settings.resolution
        }
        let idx = resolutionPopup.itemArray.firstIndex { ($0.representedObject as? String) == settings.resolution } ?? 0
        resolutionPopup.selectItem(at: settings.resolution.isEmpty ? 0 : idx)
        modesNote.stringValue = m.modes.isEmpty
            ? "No C:\\mutools\\mu-modes.txt yet; the launcher's own Settings choose the resolution."
            : "From C:\\mutools\\mu-modes.txt. A choice is written to LauncherOption.if (DevModeIndex) before each start."
    }

    private func collect() -> LauncherSettings {
        var s = settings
        s.runtime = isFree ? "free" : "crossover"
        if !bottleNames.isEmpty { s.bottle = bottleNames[bottlePopup.indexOfSelectedItem] }
        s.resolution = (resolutionPopup.selectedItem?.representedObject as? String) ?? ""
        s.fastX87 = fastCheck.state == .on
        s.startImmediately = startCheck.state == .on
        return s
    }

    @discardableResult private func persist() -> Bool {
        settings = collect()
        do { try settings.save(); AppLog.write("settings saved: \(settings.dictionary)"); return true } catch {
            status.stringValue = "Could not save settings: \(error.localizedDescription)"
            return false
        }
    }

    func showStatus(_ text: String) { status.stringValue = text }

    @objc private func bottleChanged() { settings = collect(); refreshModes(); refreshFPS() }
    @objc private func runtimeChanged() { settings = collect(); refreshRuntime(); refreshModes(); refreshFPS() }
    @objc private func install() { if persist() { onInstall?() } }
    func reloadAfterInstall() { refreshRuntime(); refreshModes(); refreshFPS() }
    @objc private func fastChanged() { refreshTimewalker() }
    @objc private func showLog() { openLog() }
    @objc private func saveOnly() {
        guard persist() else { return }
        let r = LaunchScript.run("--check", settings: settings)
        status.stringValue = r.error.map { "Saved. Check: \(errorTitle($0.code, free: settings.runtime == "free")). \($0.message)" } ?? "Saved. Preflight check passed."
    }
    @objc private func chooseTimewalker() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.allowsMultipleSelection = false
        panel.message = "Choose a built rosetta-timewalker folder (it contains scripts/run-crossover.sh)."
        if panel.runModal() == .OK, let url = panel.url { settings = collect(); settings.timewalkerDir = url.path; refreshTimewalker() }
    }
    @objc private func autoTimewalker() { settings = collect(); settings.timewalkerDir = ""; refreshTimewalker() }
    @objc private func play() { if persist() { onPlay?(settings) } }
}

// ---------------------------------------------------------------- install window
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

/// The first-run window (and Repair): one sentence and one Install button; then one progress view with plain step
/// names, an overall bar, download speed and time left, and Cancel; on failure a plain message with Try Again and
/// Show Details (the installer's output). After a successful install the game starts by itself (onPlay).
final class InstallWindowController: NSWindowController, NSWindowDelegate {
    enum Mode { case install, repair }
    private enum Phase { case welcome, checking, installing, stopping, failed, done }
    /// Called after every run (true = installed), e.g. to refresh the settings window.
    var onFinished: ((Bool) -> Void)?
    /// Starts the game: right after a successful install, or from the Play button after a repair.
    var onPlay: (() -> Void)?
    let mode: Mode
    private var phase = Phase.welcome

    private let icon = NSImageView()
    private let titleLabel = label("Mu The Matrix")
    private let message = label("")
    private let stepLabel = label("")
    private let bar = NSProgressIndicator()
    private let detail = label("", small: true)
    private let note = label("You can keep using your Mac while Mu The Matrix installs.", small: true)
    private lazy var mainButton = NSButton(title: "Install", target: self, action: #selector(mainAction))
    private lazy var cancelButton = NSButton(title: "Cancel", target: self, action: #selector(cancelPressed))
    private lazy var detailsButton = NSButton(title: "Show Details", target: self, action: #selector(toggleDetails))
    private lazy var logButton = NSButton(title: "Open Log Folder", target: self, action: #selector(openLogs))
    private lazy var folderLink = NSButton(title: "", target: self, action: #selector(chooseFolder))
    private let logView = NSTextView()
    private let logScroll = NSScrollView()
    private var stack: NSStackView!

    private var folder: String?
    private var session: InstallSession?
    private var progress = InstallProgress(fromFolder: false)
    private var ticker: Timer?
    private var stepName = ""
    private let meter = DownloadMeter()
    private var lastError: String?
    private var sawRosettaError = false, sawSummaryFail = false, sawDLLFail = false
    private var activity: NSObjectProtocol?
    private var startedAt = Date()
    /// Called once a cancel has finished (used when the app quits during an install).
    private var afterCancel: (() -> Void)?
    var isInstalling: Bool { session != nil }

    init(mode: Mode) {
        self.mode = mode
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 520, height: 400), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        w.title = "Mu The Matrix"
        super.init(window: w)
        w.delegate = self
        build()
        showWelcome()
        w.center()
    }
    required init?(coder: NSCoder) { fatalError("not used") }

    private func build() {
        guard let content = window?.contentView else { return }
        icon.image = NSApp.applicationIconImage
        icon.imageScaling = .scaleProportionallyUpOrDown
        icon.widthAnchor.constraint(equalToConstant: 112).isActive = true
        icon.heightAnchor.constraint(equalToConstant: 112).isActive = true
        titleLabel.font = .boldSystemFont(ofSize: 22)
        titleLabel.alignment = .center
        for l in [message, stepLabel, detail, note] { l.alignment = .center; l.preferredMaxLayoutWidth = 440 }
        message.font = .systemFont(ofSize: 14)
        stepLabel.font = .systemFont(ofSize: 15, weight: .semibold)
        bar.isIndeterminate = false; bar.minValue = 0; bar.maxValue = 1; bar.style = .bar
        mainButton.controlSize = .large
        mainButton.keyEquivalent = "\r"
        mainButton.widthAnchor.constraint(greaterThanOrEqualToConstant: 180).isActive = true
        cancelButton.controlSize = .large
        detailsButton.controlSize = .large
        folderLink.isBordered = false
        folderLink.attributedTitle = NSAttributedString(string: "Use a game folder I already have…", attributes: [
            .foregroundColor: NSColor.linkColor, .font: NSFont.systemFont(ofSize: NSFont.smallSystemFontSize)])
        logView.isEditable = false
        logView.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        logView.autoresizingMask = [.width]
        logScroll.documentView = logView; logScroll.hasVerticalScroller = true; logScroll.borderType = .bezelBorder
        logScroll.heightAnchor.constraint(equalToConstant: 180).isActive = true
        let buttons = NSStackView(views: [detailsButton, cancelButton, mainButton])
        buttons.spacing = 12
        buttons.setHuggingPriority(.required, for: .horizontal)     // stay centred, as wide as its buttons
        stack = NSStackView(views: [icon, titleLabel, message, stepLabel, bar, detail, note, buttons, folderLink, logScroll, logButton])
        stack.orientation = .vertical; stack.alignment = .centerX; stack.spacing = 12
        stack.setCustomSpacing(18, after: message); stack.setCustomSpacing(18, after: note)
        stack.edgeInsets = NSEdgeInsets(top: 28, left: 32, bottom: 24, right: 32)
        stack.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor), stack.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            stack.topAnchor.constraint(equalTo: content.topAnchor), stack.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            stack.widthAnchor.constraint(equalToConstant: 520),
            bar.widthAnchor.constraint(equalToConstant: 440),
            logScroll.widthAnchor.constraint(equalToConstant: 456),
        ])
    }

    /// Shows exactly the given views (the rest of the stack is hidden) and fits the window, keeping its top edge.
    private func show(_ visible: [NSView]) {
        for v in [icon, titleLabel, message, stepLabel, bar, detail, note, mainButton, cancelButton, detailsButton, folderLink, logScroll, logButton] {
            v.isHidden = !visible.contains(v)
        }
        mainButton.superview?.isHidden = ![mainButton, cancelButton, detailsButton].contains { visible.contains($0) }
        guard let w = window, let content = w.contentView else { return }
        content.layoutSubtreeIfNeeded()
        let size = stack.fittingSize
        var frame = w.frameRect(forContentRect: NSRect(origin: .zero, size: size))
        frame.origin = NSPoint(x: w.frame.minX, y: w.frame.maxY - frame.height)
        w.setFrame(frame, display: true, animate: w.isVisible)
    }

    private var estimate: String { folder == nil ? "about 45 minutes" : "about 10 minutes" }

    private func showWelcome() {
        phase = .welcome
        switch mode {
        case .install:
            titleLabel.stringValue = "Mu The Matrix"
            message.stringValue = "Mu The Matrix needs to download the game (about 2.2 GB) and set itself up. This takes \(estimate)."
            mainButton.title = "Install"
            show([icon, titleLabel, message, mainButton, folderLink])
        case .repair:
            titleLabel.stringValue = "Repair Mu The Matrix"
            message.stringValue = "Mu The Matrix checks its files and puts back anything that is missing or damaged. Your game and your settings stay. This takes a few minutes."
            mainButton.title = "Repair"
            show([icon, titleLabel, message, mainButton])
        }
    }

    private func showInstalling() {
        phase = .installing
        titleLabel.stringValue = mode == .repair ? "Repairing Mu The Matrix" : "Installing Mu The Matrix"
        cancelButton.title = "Cancel"; cancelButton.isEnabled = true
        show([icon, titleLabel, stepLabel, bar, detail, note, cancelButton])
    }

    private func showFailed(_ title: String, _ text: String, button: String = "Try Again") {
        phase = .failed
        titleLabel.stringValue = title
        message.stringValue = text
        mainButton.title = button; mainButton.isEnabled = true
        detailsButton.title = logScroll.isHidden ? "Show Details" : "Hide Details"
        var views: [NSView] = [icon, titleLabel, message, detailsButton, mainButton]
        if !logScroll.isHidden { views += [logScroll, logButton] }
        show(views)
    }

    @objc private func mainAction() {
        switch phase {
        case .welcome, .failed: startInstall()
        case .done: onPlay?()
        default: break
        }
    }
    @objc private func toggleDetails() {
        let showing = logScroll.isHidden
        detailsButton.title = showing ? "Hide Details" : "Show Details"
        var views: [NSView] = [icon, titleLabel, message, detailsButton, mainButton]
        if showing { views += [logScroll, logButton]; logView.scrollToEndOfDocument(nil) }
        show(views)
    }
    @objc private func openLogs() { openLog() }

    @objc private func chooseFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.allowsMultipleSelection = false
        panel.message = "Choose your Mu The Matrix folder (it contains MuTheMatrix.exe and main.exe). It is copied, not moved."
        panel.prompt = "Use This Folder"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        folder = url.path
        startInstall()
    }

    /// Test hook (MU_AUTOTEST_INSTALL=1): press Install programmatically, optionally with a game folder
    /// (MU_AUTOTEST_GAME_DIR). Same code path as the button, without the questions.
    func autotest(gameDir: String?) {
        if let g = gameDir { folder = g }
        runInstaller()
    }

    private func append(_ text: String) {
        logView.textStorage?.append(NSAttributedString(string: text + "\n", attributes: [.font: logView.font as Any, .foregroundColor: NSColor.textColor]))
        if !logScroll.isHidden { logView.scrollToEndOfDocument(nil) }
    }

    // ---- before the installer runs: Rosetta 2, and an app built without the files players need

    private func startInstall() {
        phase = .checking
        stepLabel.stringValue = "Getting ready"; detail.stringValue = ""; bar.doubleValue = 0
        showInstalling()
        cancelButton.isEnabled = false
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let rosetta = Rosetta.isInstalled()
            DispatchQueue.main.async {
                guard let self else { return }
                if !rosetta { self.offerRosetta(); return }
                guard self.confirmIncompleteApp() else { self.showWelcome(); return }
                self.runInstaller()
            }
        }
    }

    /// Rosetta 2 is missing: explain it and offer to install it through the standard macOS administrator prompt.
    private func offerRosetta() {
        AppLog.write("rosetta missing: offering to install it")
        let a = NSAlert()
        a.messageText = "Mu The Matrix needs Rosetta 2"
        a.informativeText = "Rosetta 2 is a free tool from Apple that lets your Mac run programs made for Intel processors. Mu The Matrix needs it to run.\n\nMu The Matrix can install it for you now. macOS will ask for your Mac login to approve this. It takes a minute or two and needs the internet."
        a.addButton(withTitle: "Install Rosetta")
        a.addButton(withTitle: "Not Now")
        guard let w = window else { return }
        a.beginSheetModal(for: w) { [weak self] response in
            guard let self else { return }
            guard response == .alertFirstButtonReturn else { self.rosettaNotInstalled(declined: true); return }
            self.stepLabel.stringValue = "Installing Rosetta 2 from Apple…"
            self.bar.isIndeterminate = true; self.bar.startAnimation(nil)
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                let r = Rosetta.install()
                let nowOK = r.ok && Rosetta.isInstalled()
                DispatchQueue.main.async {
                    guard let self else { return }
                    self.bar.stopAnimation(nil); self.bar.isIndeterminate = false
                    AppLog.write("rosetta install ok=\(r.ok) declined=\(r.declined) installed=\(nowOK)\n\(r.output)")
                    if !r.output.isEmpty { self.append(r.output) }
                    guard nowOK else { self.rosettaNotInstalled(declined: r.declined); return }
                    self.append("Rosetta 2 is installed.")
                    guard self.confirmIncompleteApp() else { self.showWelcome(); return }
                    self.runInstaller()
                }
            }
        }
    }

    private func rosettaNotInstalled(declined: Bool) {
        append("To install Rosetta 2 in Terminal:\n    \(Rosetta.terminalCommand)")
        showFailed(declined ? "Rosetta 2 is needed first" : "Rosetta 2 could not be installed",
                   "Click Try Again to install it. Or install it yourself: open Terminal (in Applications > Utilities), paste the line shown under Show Details and press Return, type your Mac login when asked, then click Try Again.")
    }

    /// An app built without the files players need (not with make player-app) installs a slow game whose final
    /// check fails. Say so before starting; returns false when the player prefers not to go on.
    private func confirmIncompleteApp() -> Bool {
        let missing = Installer.missingEmbeds
        guard !missing.isEmpty else { return true }
        AppLog.write("app bundle incomplete: missing \(missing.joined(separator: ", "))")
        let a = NSAlert()
        a.alertStyle = .warning
        a.messageText = "This copy of Mu The Matrix is incomplete"
        a.informativeText = "It was built without some of the files that make the game run well (missing: \(missing.joined(separator: ", "))). The game may run very slowly, and the installation may end with a failed check.\n\nDownload Mu The Matrix again from the official website, or tell the server team. You can still install now; installing the complete app later and choosing Repair fixes it."
        a.addButton(withTitle: "Cancel")
        a.addButton(withTitle: "Install Anyway")
        return a.runModal() == .alertSecondButtonReturn
    }

    // ---- the installer

    private func runInstaller() {
        showInstalling()
        stepName = ""; lastError = nil
        sawRosettaError = false; sawSummaryFail = false; sawDLLFail = false
        stepLabel.stringValue = "Getting ready"; detail.stringValue = ""
        progress = InstallProgress(fromFolder: folder != nil)
        bar.doubleValue = 0
        startedAt = Date()
        AppLog.write("install start (\(mode == .repair ? "repair" : "install")) source=\(folder ?? "official installer") runtime=\(Installer.bundledRuntime?.lastPathComponent ?? "default download")")
        // Keep the Mac from idle-sleeping while the installer runs (closing the lid still sleeps it).
        activity = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .idleSystemSleepDisabled], reason: "Installing Mu The Matrix")
        ticker = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in self?.tick() }
        session = Installer.start(gameDir: folder, line: { [weak self] l in self?.handle(l) },
                                  done: { [weak self] st, cancelled in self?.finished(st, cancelled: cancelled) })
    }

    private func tick() {
        guard phase == .installing else { return }
        let f = progress.update(now: ProcessInfo.processInfo.systemUptime)
        bar.doubleValue = f
        let pct = Int(f * 100)
        NSApp.dockTile.badgeLabel = "\(pct)%"
        window?.title = "Mu The Matrix — \(pct)%"
    }

    /// The plain title of the running step; the game step depends on where the game comes from and on its phase.
    private func setStep(_ name: String, phase gamePhase: String? = nil) {
        if name == "game files" {
            stepLabel.stringValue = folder != nil ? "Copying your game folder" : (gamePhase ?? "Downloading the game")
        } else {
            stepLabel.stringValue = installStepInfo[name]?.title ?? "Setting up Mu The Matrix"
        }
        detail.stringValue = name == ".NET Framework 4.8" ? "This part takes a few minutes." : ""
    }

    private func handle(_ l: String) {
        if meter.feed(l) {
            // "MU-PROGRESS BYTES TOTAL NAME" once a second while a download runs: sizes, speed and time left.
            detail.stringValue = meter.summary
            if stepName == "game files" { progress.download(meter.fraction ?? 0) }
            return
        }
        AppLog.write("install: " + l)
        append(l)
        let now = ProcessInfo.processInfo.systemUptime
        if l.hasPrefix("== ") {
            // "== 7/14 game files" (also "== 6b/14 ..."): the step name follows the "N/M".
            var name = String(l.dropFirst(3))
            if let sp = name.firstIndex(of: " "), name[name.startIndex..<sp].contains("/") { name = String(name[name.index(after: sp)...]) }
            stepName = name
            progress.begin(name, now: now)
            setStep(name)
        } else if stepName == "game files" && l.contains("[do]   run the official installer") {
            progress.installerRuns(now: now)
            setStep(stepName, phase: "Installing the game")
            detail.stringValue = "This part takes a few minutes."
        } else if l.range(of: #"^[\s#=O\-]*([0-9]+(\.[0-9])?%)?\s*$"#, options: .regularExpression) != nil {
            // curl's own progress bar (downloads outside the app's progress lines): nothing to show.
        } else {
            if l.hasPrefix("Error: ") { lastError = String(l.dropFirst("Error: ".count)) }
            if l.contains("Rosetta 2 is not installed") { sawRosettaError = true }
            if l.hasPrefix("Summary: ") && !l.hasSuffix(" 0 FAIL") { sawSummaryFail = true }
            if l.hasPrefix("FAIL  mugl opengl32.dll") || l.hasPrefix("FAIL  mscoree proxy") { sawDLLFail = true }
        }
    }

    /// A plain explanation of why the installation stopped.
    private func failureText(status: Int32) -> (title: String, text: String) {
        let e = lastError ?? ""
        let again = "Click Try Again: the steps that already finished are kept."
        if e.hasPrefix("Not enough free disk space") {
            return ("Not enough free space", "\(e) Free up some space on your Mac, then click Try Again.")
        }
        if e.contains("download failed") || e.contains("internet") {
            return ("A download did not finish", "Mu The Matrix could not download what it needs. Check your internet connection, then click Try Again. It continues where it stopped.")
        }
        if sawDLLFail && !Installer.missingEmbeds.isEmpty {
            return ("This copy of Mu The Matrix is incomplete", "The game was installed, but this copy of the app lacks files the game needs to run well. Download Mu The Matrix again from the official website, open it and choose Repair.")
        }
        if sawSummaryFail && lastError == nil {
            return ("The final check found a problem", "\(again) If it happens again, click Show Details and send the details to the Mu The Matrix team.")
        }
        return ("The installation could not finish", "Something went wrong while Mu The Matrix was setting itself up. \(again) If it happens again, click Show Details and send the details to the Mu The Matrix team.")
    }

    private func finished(_ status: Int32, cancelled: Bool) {
        session = nil
        ticker?.invalidate(); ticker = nil
        if let a = activity { ProcessInfo.processInfo.endActivity(a); activity = nil }
        NSApp.dockTile.badgeLabel = nil
        window?.title = "Mu The Matrix"
        let ok = status == 0 && !cancelled
        let minutes = Int(Date().timeIntervalSince(startedAt) / 60)
        AppLog.write("install finished status \(status)\(cancelled ? " (cancelled)" : "") after \(minutes) min")
        if ok {
            phase = .done
            bar.doubleValue = 1
            if mode == .install {
                titleLabel.stringValue = "Mu The Matrix is ready"
                stepLabel.stringValue = "Starting the game…"
                show([icon, titleLabel, stepLabel, bar])
                onFinished?(true)
                // Let the player see "ready" for a moment, then the official launcher opens.
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { [weak self] in self?.onPlay?() }
            } else {
                titleLabel.stringValue = "Mu The Matrix is repaired"
                message.stringValue = "Everything is in place."
                mainButton.title = "Play"
                show([icon, titleLabel, message, mainButton])
                onFinished?(true)
            }
            return
        }
        if cancelled {
            showFailed("The installation was stopped", "Click Continue to go on where it stopped: the steps that already finished and the part already downloaded are kept.", button: "Continue")
        } else if sawRosettaError {
            offerRosetta()
        } else {
            let f = failureText(status: status)
            showFailed(f.title, f.text)
        }
        onFinished?(false)
        if cancelled, let next = afterCancel { afterCancel = nil; next() }
    }

    /// Asks, then stops the installation (the installer, its downloads and everything it started). `then` runs once
    /// everything has stopped. Returns false when the player chose to continue.
    @discardableResult
    func confirmCancel(quitting: Bool = false, then: (() -> Void)? = nil) -> Bool {
        guard let s = session, s.isRunning else { then?(); return true }
        let a = NSAlert(); a.messageText = quitting ? "Stop the installation and quit?" : "Stop the installation?"
        a.informativeText = "You can continue later: the steps that already finished and the part already downloaded are kept."
        a.addButton(withTitle: "Stop"); a.addButton(withTitle: "Continue Installing")
        guard a.runModal() == .alertFirstButtonReturn else { return false }
        guard s.isRunning else { then?(); return true }
        afterCancel = then
        phase = .stopping
        stepLabel.stringValue = "Stopping…"
        detail.stringValue = "This takes a few seconds."
        cancelButton.isEnabled = false
        s.cancel()
        return true
    }

    @objc private func cancelPressed() { if session != nil { confirmCancel() } }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        if session != nil { confirmCancel(); return false }
        return phase != .checking && phase != .done
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

// ---------------------------------------------------------------- app delegate
final class AppDelegate: NSObject, NSApplicationDelegate {
    var settingsWindow: SettingsWindowController?
    var installWindow: InstallWindowController?
    var progress: NSWindow?

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        if AppMover.offerIfNeeded() { return }
        let s = LauncherSettings.load()
        let option = NSEvent.modifierFlags.contains(.option)
        AppLog.write("app \(appVersion) opened from \(Bundle.main.bundlePath) (settings file \(LauncherSettings.fileExists ? "present" : "missing"), option key \(option ? "held" : "not held"))")
        let freeReady: Bool = {
            guard s.runtime == "free" else { return true }
            let st = LaunchScript.freeStatus(); return st.runtime && st.prefix && st.game
        }()
        let env = ProcessInfo.processInfo.environment
        if env["MU_AUTOTEST_INSTALL"] == "1" {
            showInstaller()
            installWindow?.autotest(gameDir: env["MU_AUTOTEST_GAME_DIR"].flatMap { $0.isEmpty ? nil : $0 })
        } else if option {
            showSettings(nil)
        } else if !freeReady {
            // First start: only the install window (one sentence, one Install button); it starts the game when done.
            showInstaller()
        } else if !s.startImmediately {
            showSettings(nil)
        } else {
            start(s)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { !AppMover.busy }

    /// Quitting during an install stops the installer and everything it started first (after asking).
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard let w = installWindow, w.isInstalling else { return .terminateNow }
        w.showWindow(nil)
        let stopping = w.confirmCancel(quitting: true) { DispatchQueue.main.async { NSApp.reply(toApplicationShouldTerminate: true) } }
        return stopping ? .terminateLater : .terminateCancel
    }

    private func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem(); main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Mu The Matrix", action: #selector(about(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Settings…", action: #selector(showSettings(_:)), keyEquivalent: ",")
        appMenu.addItem(withTitle: "Open Log", action: #selector(openLogAction(_:)), keyEquivalent: "l")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Mu The Matrix", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Quit Mu The Matrix", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        // Edit menu: copy from the details view, paste into the folder dialog.
        let editItem = NSMenuItem(); main.addItem(editItem)
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        NSApp.mainMenu = main
    }

    @objc func openLogAction(_ sender: Any?) { openLog() }

    /// The standard About panel, with the license notice of the bundled Wine runtime.
    @objc func about(_ sender: Any?) {
        var options: [NSApplication.AboutPanelOptionKey: Any] = [:]
        if Installer.bundledRuntime != nil {
            options[.credits] = NSAttributedString(string: "Includes Wine from CodeWeavers' CrossOver 26.3 sources (GNU LGPL 2.1 or later). Its license and where to get the sources: Contents/Resources/runtime in this app.",
                                                   attributes: [.font: NSFont.systemFont(ofSize: NSFont.smallSystemFontSize)])
        }
        NSApp.orderFrontStandardAboutPanel(options: options)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc func showSettings(_ sender: Any?) {
        if settingsWindow == nil {
            let c = SettingsWindowController(settings: LauncherSettings.load())
            c.onPlay = { [weak self] s in self?.start(s) }
            c.onInstall = { [weak self] in self?.showInstaller() }
            settingsWindow = c
        }
        settingsWindow?.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    /// The install window: Install on a first start, Repair when the game is already installed.
    func showInstaller() {
        if let w = installWindow, w.isInstalling || w.window?.isVisible == true {
            w.showWindow(nil); NSApp.activate(ignoringOtherApps: true); return
        }
        let st = LaunchScript.freeStatus()
        let w = InstallWindowController(mode: st.runtime && st.prefix && st.game ? .repair : .install)
        w.onFinished = { [weak self] _ in self?.settingsWindow?.reloadAfterInstall() }
        w.onPlay = { [weak self, weak w] in
            w?.window?.orderOut(nil)
            var s = LauncherSettings.load()
            if s.runtime != "free" { s.runtime = "free" }    // the install was for the free runtime
            self?.start(s)
        }
        installWindow = w
        w.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func showProgress(_ bottle: String) {
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 360, height: 90), styleMask: [.titled], backing: .buffered, defer: false)
        w.title = "Mu The Matrix"
        let spin = NSProgressIndicator(); spin.style = .spinning; spin.startAnimation(nil)
        let text = label(bottle.isEmpty ? "Starting Mu The Matrix…" : "Starting the launcher in bottle \(bottle)…")
        let stack = NSStackView(views: [spin, text])
        stack.edgeInsets = NSEdgeInsets(top: 20, left: 20, bottom: 20, right: 20)
        w.contentView = stack
        w.center(); w.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        progress = w
    }

    func start(_ s: LauncherSettings) {
        settingsWindow?.window?.orderOut(nil)
        showProgress(s.runtime == "free" ? "" : s.bottle)
        AppLog.write("start runtime=\(s.runtime) bottle=\(s.bottle) fastX87=\(s.fastX87) timewalker=\(s.timewalkerDir.isEmpty ? "auto" : s.timewalkerDir) resolution=\(s.resolution.isEmpty ? "keep" : s.resolution)")
        DispatchQueue.global(qos: .userInitiated).async {
            let r = LaunchScript.run("--run", settings: s)
            DispatchQueue.main.async { self.finish(r) }
        }
    }

    private func finish(_ r: LaunchResult) {
        AppLog.write("mu-launch.sh status \(r.status)\n" + r.output.trimmingCharacters(in: .newlines))
        progress?.orderOut(nil); progress = nil
        guard let err = r.error else { NSApp.terminate(nil); return }
        if err.code == 14 {
            // Opened while playing: show the settings (e.g. to turn the FPS counter on or off) instead of an error.
            showSettings(nil)
            settingsWindow?.showStatus("Mu The Matrix is already running. Changes to the FPS counter apply right away; the other settings apply the next time the game starts.")
            return
        }
        let free = LauncherSettings.load().runtime == "free"
        let needsInstall = [30, 31].contains(err.code) || (err.code == 13 && free)
        if needsInstall {
            // Not installed (or the install was removed): the install window says what to do.
            AppLog.write("start: not installed (\(err.code)); showing the install window")
            showInstaller(); return
        }
        let alert = NSAlert()
        alert.alertStyle = .warning
        alert.messageText = errorTitle(err.code, free: free)
        alert.informativeText = err.message + "\n\nLog: \(AppLog.url.path)"
        alert.addButton(withTitle: "Settings…")
        alert.addButton(withTitle: "Open Log")
        alert.addButton(withTitle: "Quit")
        if err.code == 10 { alert.addButton(withTitle: "Get CrossOver") }
        NSApp.activate(ignoringOtherApps: true)
        switch alert.runModal() {
        case .alertFirstButtonReturn:
            showSettings(nil)
            settingsWindow?.showStatus("Last start failed: \(errorTitle(err.code, free: free)). \(err.message)")
        case .alertSecondButtonReturn: openLog(); NSApp.terminate(nil)
        case NSApplication.ModalResponse(rawValue: NSApplication.ModalResponse.alertThirdButtonReturn.rawValue + 1):
            NSWorkspace.shared.open(URL(string: "https://www.codeweavers.com/crossover")!); NSApp.terminate(nil)
        default: NSApp.terminate(nil)
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
