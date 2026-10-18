// Mu The Matrix.app (MAC-BUNDLE-001): entry point, command-line modes and the AppKit UI.
//
// Double-click: start the launcher (free Wine runtime by default, or a CrossOver bottle) and quit. The settings window opens instead on
// the first run (no settings file), when Option is held, when "Start right away" is off, or after an error.
// Command line (no window): --dry-run, --check, --status, --install, --install-dry-run, --check-bundle, --rosetta-status,
// --install-rosetta, --print-settings, --settings-path, --version, --help.
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
        let gameDir = cliArgs.dropFirst().first
        var finished = false, status: Int32 = 0
        AppLog.write("cli \(arg) source=\(gameDir ?? "official installer")")
        let meter = DownloadMeter(); var lastProgress = Date.distantPast
        let session = Installer.start(gameDir: gameDir, dryRun: arg == "--install-dry-run", line: { l in
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
        // A player build (make player-app) bundles mugl, the mscoree proxy and the fast x87 translator.
        let missing = Installer.missingEmbeds
        if missing.isEmpty { print("bundle complete: mugl, mscoree proxy and fast x87 are bundled"); exit(0) }
        print("bundle incomplete: missing " + missing.joined(separator: ", "))
        print("Build the app for players with: make player-app EMBED_MUGL=... EMBED_MSCOREE=... EMBED_FAST_X87=...")
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
    case "--settings-path": print(LauncherSettings.fileURL.path); exit(0)
    case "--version": print("Mu The Matrix.app \(appVersion)"); exit(0)
    case "--help", "-h":
        print("""
        Mu The Matrix.app \(appVersion): installs and starts Mu The Matrix (free Wine runtime, or a CrossOver bottle).
          (no option)       open the app (double-click behaviour)
          --dry-run         preflight and print what a start would do; changes nothing
          --check           preflight only
          --status          free runtime install state (exit 0 when ready)
          --install [GAME_DIR]          install without a window (default: download the official game)
          --install-dry-run [GAME_DIR]  print the installer's plan; changes nothing
          --check-bundle    exit 0 when mugl, the mscoree proxy and fast x87 are bundled (a player build)
          --rosetta-status  exit 0 when Rosetta 2 is installed
          --install-rosetta install Rosetta 2 (asks for administrator approval)
          --print-settings  show the effective settings and file locations
          --settings-path   print the settings plist path
          --version
        Environment: MU_SETTINGS_FILE, MU_LOG_DIR, MU_LAUNCH_SCRIPT, MU_SETUP_SCRIPT, MUKIT_FREE_HOME, CX_ROOT, MUKIT_BOTTLES_DIR,
          MU_CANCEL_GRACE, MU_ROSETTA_CHECK, MU_ROSETTA_INSTALL.
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

    @objc private func bottleChanged() { settings = collect(); refreshModes() }
    @objc private func runtimeChanged() { settings = collect(); refreshRuntime(); refreshModes() }
    @objc private func install() { if persist() { onInstall?() } }
    func reloadAfterInstall() { refreshRuntime(); refreshModes() }
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
/// Player-facing names for the installer's steps ("== 7/14 game files" -> "Step 7 of 14: game files").
let installStepNames: [String: String] = [
    "free Wine runtime": "the free Windows layer (Wine)",
    "winetricks": "helper tool (winetricks)",
    "Wine prefix (32-bit)": "the game's Windows folder",
    "registry (AeDebug off, overrides)": "Windows settings",
    ".NET Framework 4.8": "Microsoft .NET Framework 4.8 (about 4 minutes)",
    "Windows version": "Windows version",
    "registry re-check after .NET": "Windows settings, second check",
    "game files": "game files",
    "launcher .NET config": "launcher settings",
    "launcher skin": "launcher appearance",
    "C:\\mutools": "window sizes and speed settings",
    "LauncherOption.if": "window size",
    "proxy DLLs": "speed-up files (mugl)",
    "fast x87 and Desktop launcher": "fast 3D maths (fast x87)",
    "verify": "final check",
]

/// Runs the bundled installer with the free runtime: choose where the game comes from, then watch the steps.
final class InstallWindowController: NSWindowController, NSWindowDelegate {
    var onFinished: ((Bool) -> Void)?
    private let downloadRadio = NSButton(radioButtonWithTitle: "Download the game from the official site (about 2.2 GB)", target: nil, action: nil)
    private let folderRadio = NSButton(radioButtonWithTitle: "Use a Mu The Matrix folder I already have…", target: nil, action: nil)
    private let folderLabel = label("", small: true)
    private let step = label("Ready. Takes about 10 minutes plus the game download (2.2 GB) and needs about 12 GB of free space.")
    private let detail = label("", small: true)
    private let bar = NSProgressIndicator()
    private let logView = NSTextView()
    private lazy var startButton = NSButton(title: "Install", target: self, action: #selector(startInstall))
    private lazy var closeButton = NSButton(title: "Cancel", target: self, action: #selector(closeOrCancel))
    private var folder: String?
    private var session: InstallSession?
    private var steps = 0, total = 14
    private var stepTitle = ""
    private let meter = DownloadMeter()
    private var lastError: String?
    private var sawRosettaError = false, sawSummaryFail = false, sawDLLFail = false
    private var activity: NSObjectProtocol?
    private var startedAt = Date()
    /// Called once a cancel has finished (used when the app quits during an install).
    private var afterCancel: (() -> Void)?
    var isInstalling: Bool { session != nil }

    init() {
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 480), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        w.title = "Install Mu The Matrix"
        w.minSize = NSSize(width: 560, height: 420)
        super.init(window: w)
        w.delegate = self
        build()
        w.center()
    }
    required init?(coder: NSCoder) { fatalError("not used") }

    private func build() {
        guard let content = window?.contentView else { return }
        let icon = NSImageView(image: NSApp.applicationIconImage)
        icon.imageScaling = .scaleProportionallyUpOrDown
        icon.widthAnchor.constraint(equalToConstant: 48).isActive = true
        icon.heightAnchor.constraint(equalToConstant: 48).isActive = true
        let title = label("Install Mu The Matrix"); title.font = .boldSystemFont(ofSize: 15)
        let intro = label("This sets up everything the game needs in ~/Library/Application Support/MuTheMatrix: a free Windows layer (Wine, no CrossOver), Microsoft .NET Framework 4.8 (downloaded from Microsoft) and the game. You can keep using your Mac while it runs; it stays awake until the installation has finished.", small: true)
        intro.preferredMaxLayoutWidth = 520
        let headText = NSStackView(views: [title, intro]); headText.orientation = .vertical; headText.alignment = .leading; headText.spacing = 4
        let head = NSStackView(views: [icon, headText]); head.alignment = .top; head.spacing = 12
        downloadRadio.target = self; downloadRadio.action = #selector(sourceChanged)
        folderRadio.target = self; folderRadio.action = #selector(chooseFolder)
        downloadRadio.state = .on
        folderLabel.maximumNumberOfLines = 1
        folderLabel.lineBreakMode = .byTruncatingMiddle
        folderLabel.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        step.font = .systemFont(ofSize: NSFont.systemFontSize, weight: .medium)
        bar.isIndeterminate = false; bar.minValue = 0; bar.maxValue = Double(total); bar.style = .bar
        logView.isEditable = false
        logView.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        let scroll = NSScrollView(); scroll.documentView = logView; scroll.hasVerticalScroller = true
        logView.autoresizingMask = [.width]
        scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 160).isActive = true
        startButton.keyEquivalent = "\r"
        let spacer = NSView(); spacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let logButton = NSButton(title: "Open Log Folder", target: self, action: #selector(openLogs))
        let buttons = NSStackView(views: [logButton, spacer, closeButton, startButton])
        let stack = NSStackView(views: [head, downloadRadio, folderRadio, folderLabel, step, bar, detail, scroll, buttons])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 10
        stack.setCustomSpacing(16, after: head)
        stack.edgeInsets = NSEdgeInsets(top: 18, left: 20, bottom: 18, right: 20)
        stack.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor), stack.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            stack.topAnchor.constraint(equalTo: content.topAnchor), stack.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            scroll.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
            bar.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
            step.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
            detail.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
            folderLabel.widthAnchor.constraint(lessThanOrEqualTo: stack.widthAnchor, constant: -40),
            buttons.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
        ])
    }

    @objc private func sourceChanged() { folderRadio.state = .off; downloadRadio.state = .on; folder = nil; folderLabel.stringValue = "" }
    @objc private func chooseFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.allowsMultipleSelection = false
        panel.message = "Choose your Mu The Matrix folder (it contains MuTheMatrix.exe and main.exe). It is copied, not moved."
        if panel.runModal() == .OK, let url = panel.url {
            folder = url.path; folderLabel.stringValue = url.path
            folderRadio.state = .on; downloadRadio.state = .off
        } else if folder == nil { sourceChanged() }
    }
    @objc private func openLogs() { openLog() }

    /// Test hook (MU_AUTOTEST_INSTALL=1): press Install programmatically, optionally with a game folder
    /// (MU_AUTOTEST_GAME_DIR). Same code path as the button, without the questions; used for the recorded rehearsal.
    func autotest(gameDir: String?) {
        if let g = gameDir { folder = g; folderLabel.stringValue = g; folderRadio.state = .on; downloadRadio.state = .off }
        runInstaller()
    }

    private func append(_ text: String) {
        logView.textStorage?.append(NSAttributedString(string: text + "\n", attributes: [.font: logView.font as Any, .foregroundColor: NSColor.textColor]))
        logView.scrollToEndOfDocument(nil)
    }

    private func setBusy(_ busy: Bool) {
        startButton.isEnabled = !busy; downloadRadio.isEnabled = !busy; folderRadio.isEnabled = !busy
        closeButton.title = busy ? "Cancel" : "Close"
        closeButton.isEnabled = true
    }

    // ---- before the installer runs: Rosetta 2, and an app built without the speed-up files

    @objc private func startInstall() {
        setBusy(true)
        step.stringValue = "Checking your Mac…"; detail.stringValue = ""
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let rosetta = Rosetta.isInstalled()
            DispatchQueue.main.async {
                guard let self else { return }
                if !rosetta { self.offerRosetta(); return }
                guard self.confirmIncompleteApp() else { self.setBusy(false); self.step.stringValue = "Ready."; return }
                self.runInstaller()
            }
        }
    }

    /// Rosetta 2 is missing: explain it and offer to install it through the standard macOS administrator prompt.
    private func offerRosetta() {
        AppLog.write("rosetta missing: offering to install it")
        let a = NSAlert()
        a.messageText = "Mu The Matrix needs Rosetta 2"
        a.informativeText = "Rosetta 2 is a free tool from Apple that lets your Mac run programs made for Intel processors. The game's Windows layer needs it.\n\nMu The Matrix can install it for you now. macOS will ask for your Mac login to approve this. It takes a minute or two and needs the internet."
        a.addButton(withTitle: "Install Rosetta")
        a.addButton(withTitle: "Not Now")
        guard a.runModal() == .alertFirstButtonReturn else { rosettaNotInstalled(declined: true); return }
        setBusy(true); closeButton.isEnabled = false
        step.stringValue = "Installing Rosetta 2 (Apple's translator for Intel programs)…"
        bar.isIndeterminate = true; bar.startAnimation(nil)
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
                guard self.confirmIncompleteApp() else { self.setBusy(false); self.step.stringValue = "Ready."; return }
                self.runInstaller()
            }
        }
    }

    private func rosettaNotInstalled(declined: Bool) {
        setBusy(false)
        startButton.title = "Try Again"
        step.stringValue = declined ? "Rosetta 2 is needed before the installation can start."
                                    : "Rosetta 2 could not be installed."
        detail.stringValue = "To install it yourself: open Terminal (in Applications > Utilities), paste the line shown in the box below and press Return. Type your Mac login when asked (nothing appears while you type), wait until it says the install finished, then click Try Again."
        append("To install Rosetta 2 in Terminal:\n    \(Rosetta.terminalCommand)")
    }

    /// An app built without the pinned DLLs (not with make player-app) installs a game that runs at about 4 fps and
    /// whose final check fails. Say so before starting; returns false when the player prefers not to go on.
    private func confirmIncompleteApp() -> Bool {
        let missing = Installer.missingEmbeds
        guard !missing.isEmpty else { return true }
        AppLog.write("app bundle incomplete: missing \(missing.joined(separator: ", "))")
        let a = NSAlert()
        a.alertStyle = .warning
        a.messageText = "This copy of Mu The Matrix is incomplete"
        a.informativeText = "It was built without the files that make the game fast (missing: \(missing.joined(separator: ", "))). Without them the game runs very slowly (about 4 frames per second), and the installation ends with a failed final check.\n\nDownload Mu The Matrix.zip again from your server team's link, or tell them. You can still install now; installing the complete app later and clicking Repair… fixes it."
        a.addButton(withTitle: "Cancel")
        a.addButton(withTitle: "Install Anyway")
        return a.runModal() == .alertSecondButtonReturn
    }

    // ---- the installer

    private func runInstaller() {
        setBusy(true)
        startButton.title = "Install"
        steps = 0; bar.doubleValue = 0; stepTitle = ""; lastError = nil
        sawRosettaError = false; sawSummaryFail = false; sawDLLFail = false
        step.stringValue = "Starting…"; detail.stringValue = ""
        startedAt = Date()
        window?.title = "Install Mu The Matrix"
        AppLog.write("install start source=\(folder ?? "official installer")")
        // Keep the Mac from idle-sleeping while the installer runs (closing the lid still sleeps it).
        activity = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .idleSystemSleepDisabled], reason: "Installing Mu The Matrix")
        session = Installer.start(gameDir: folder, line: { [weak self] l in self?.handle(l) },
                                  done: { [weak self] st, cancelled in self?.finished(st, cancelled: cancelled) })
    }

    private func showProgress(fraction: Double?) {
        let within = min(max(fraction ?? 0, 0), 1)
        bar.doubleValue = Double(max(0, steps - 1)) + within
        let pct = Int((bar.doubleValue / max(bar.maxValue, 1)) * 100)
        NSApp.dockTile.badgeLabel = steps > 0 ? "\(pct)%" : nil
        window?.title = steps > 0 ? "Install Mu The Matrix — \(pct)%" : "Install Mu The Matrix"
    }

    private func handle(_ l: String) {
        if meter.feed(l) {
            // "MU-PROGRESS BYTES TOTAL NAME" once a second while a download runs: sizes, speed and time left.
            detail.stringValue = "Downloading \(meter.name): \(meter.summary)"
            showProgress(fraction: meter.fraction)
            return
        }
        AppLog.write("install: " + l)
        // "== 7/14 game files" -> "Step 7 of 14: game files"; curl's "###   12.3%" bar lines only update the detail line.
        if l.hasPrefix("== ") {
            let body = l.dropFirst(3)
            var name = String(body)
            if let slash = body.firstIndex(of: "/"), let n = Int(body[body.startIndex..<slash].filter(\.isNumber)) {
                let rest = body[body.index(after: slash)...]
                if let sp = rest.firstIndex(of: " "), let t = Int(rest[rest.startIndex..<sp]) {
                    total = t; bar.maxValue = Double(t)
                    name = String(rest[rest.index(after: sp)...])
                }
                steps = n
            }
            stepTitle = "Step \(steps) of \(total): " + (installStepNames[name] ?? name)
            step.stringValue = stepTitle
            detail.stringValue = ""
            showProgress(fraction: 0)
            append(l)
        } else if l.range(of: #"^[\s#=O\-]*([0-9]+(\.[0-9])?%)?\s*$"#, options: .regularExpression) != nil {
            if let pct = l.split(separator: " ").last, pct.hasSuffix("%") { detail.stringValue = "Downloading: \(pct)" }
        } else {
            if l.hasPrefix("Error: ") { lastError = String(l.dropFirst("Error: ".count)) }
            if l.contains("Rosetta 2 is not installed") { sawRosettaError = true }
            if l.hasPrefix("Summary: ") && !l.hasSuffix(" 0 FAIL") { sawSummaryFail = true }
            if l.hasPrefix("FAIL  mugl opengl32.dll") || l.hasPrefix("FAIL  mscoree proxy") { sawDLLFail = true }
            append(l)
        }
    }

    private func finished(_ status: Int32, cancelled: Bool) {
        session = nil
        if let a = activity { ProcessInfo.processInfo.endActivity(a); activity = nil }
        NSApp.dockTile.badgeLabel = nil
        window?.title = "Install Mu The Matrix"
        let ok = status == 0 && !cancelled
        let minutes = Int(Date().timeIntervalSince(startedAt) / 60)
        AppLog.write("install finished status \(status)\(cancelled ? " (cancelled)" : "") after \(minutes) min")
        setBusy(false)
        detail.stringValue = ""
        if ok {
            bar.doubleValue = bar.maxValue
            step.stringValue = "Done. Mu The Matrix is installed. Close this window and press Play."
            startButton.title = "Done"; startButton.isEnabled = false
        } else if cancelled {
            step.stringValue = "The installation was stopped."
            detail.stringValue = "Click Try Again to continue where it stopped: finished steps and the part already downloaded are kept."
            startButton.title = "Try Again"
        } else if sawRosettaError {
            startButton.title = "Try Again"
            offerRosetta()
        } else if sawDLLFail && !Installer.missingEmbeds.isEmpty {
            step.stringValue = "The game was installed, but this copy of Mu The Matrix is incomplete."
            detail.stringValue = "It lacks the files that make the game fast, so the final check failed and the game would run at about 4 frames per second. Get the complete Mu The Matrix.zip from your server team, replace the app, then click Repair… in the Mu The Matrix window."
            startButton.title = "Try Again"
        } else if sawSummaryFail && lastError == nil {
            step.stringValue = "The installation finished, but the final check found a problem."
            detail.stringValue = "The FAIL lines above say what. Click Try Again; if it fails again, send the logs to your server team (Open Log Folder)."
            startButton.title = "Try Again"
        } else {
            step.stringValue = "The installation stopped: " + (lastError ?? "status \(status).")
            detail.stringValue = "Fix the problem and click Try Again: finished steps are skipped and an interrupted download continues where it stopped."
            startButton.title = "Try Again"
        }
        onFinished?(ok)
        if cancelled, let next = afterCancel { afterCancel = nil; next() }
    }

    /// Asks, then stops the installation (the installer, its downloads and its Wine processes). `then` runs once
    /// everything has stopped. Returns false when the player chose to continue.
    @discardableResult
    func confirmCancel(quitting: Bool = false, then: (() -> Void)? = nil) -> Bool {
        guard let s = session, s.isRunning else { then?(); return true }
        let a = NSAlert(); a.messageText = quitting ? "Stop the installation and quit?" : "Stop the installation?"
        a.informativeText = "Everything it started is stopped. You can start it again later: finished steps and the part already downloaded are kept."
        a.addButton(withTitle: "Stop"); a.addButton(withTitle: "Continue")
        guard a.runModal() == .alertFirstButtonReturn else { return false }
        guard s.isRunning else { then?(); return true }
        afterCancel = then
        step.stringValue = "Stopping the installation…"
        detail.stringValue = "This takes a few seconds."
        closeButton.isEnabled = false; startButton.isEnabled = false
        s.cancel()
        return true
    }

    @objc private func closeOrCancel() {
        if session != nil { confirmCancel(); return }
        window?.orderOut(nil)
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        if session != nil { confirmCancel(); return false }
        return true
    }
}

// ---------------------------------------------------------------- app delegate
final class AppDelegate: NSObject, NSApplicationDelegate {
    var settingsWindow: SettingsWindowController?
    var installWindow: InstallWindowController?
    var progress: NSWindow?

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        let s = LauncherSettings.load()
        let option = NSEvent.modifierFlags.contains(.option)
        AppLog.write("app \(appVersion) opened (settings file \(LauncherSettings.fileExists ? "present" : "missing"), option key \(option ? "held" : "not held"))")
        let freeReady: Bool = {
            guard s.runtime == "free" else { return true }
            let st = LaunchScript.freeStatus(); return st.runtime && st.prefix && st.game
        }()
        let env = ProcessInfo.processInfo.environment
        if env["MU_AUTOTEST_INSTALL"] == "1" {
            showSettings(nil); showInstaller()
            installWindow?.autotest(gameDir: env["MU_AUTOTEST_GAME_DIR"].flatMap { $0.isEmpty ? nil : $0 })
        } else if !freeReady {
            // First start with the free runtime: settings behind, the installer in front.
            showSettings(nil); showInstaller()
        } else if !LauncherSettings.fileExists || option || !s.startImmediately {
            showSettings(nil)
        } else {
            start(s)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { true }

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
        appMenu.addItem(withTitle: "About Mu The Matrix", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Settings…", action: #selector(showSettings(_:)), keyEquivalent: ",")
        appMenu.addItem(withTitle: "Open Log", action: #selector(openLogAction(_:)), keyEquivalent: "l")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Mu The Matrix", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        NSApp.mainMenu = main
    }

    @objc func openLogAction(_ sender: Any?) { openLog() }

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

    func showInstaller() {
        if installWindow == nil {
            let w = InstallWindowController()
            w.onFinished = { [weak self] _ in self?.settingsWindow?.reloadAfterInstall() }
            installWindow = w
        }
        installWindow?.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func showProgress(_ bottle: String) {
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 360, height: 90), styleMask: [.titled], backing: .buffered, defer: false)
        w.title = "Mu The Matrix"
        let spin = NSProgressIndicator(); spin.style = .spinning; spin.startAnimation(nil)
        let text = label(bottle.isEmpty ? "Starting the launcher…" : "Starting the launcher in bottle \(bottle)…")
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
        let free = LauncherSettings.load().runtime == "free"
        let alert = NSAlert()
        alert.alertStyle = err.code == 14 ? .informational : .warning
        alert.messageText = errorTitle(err.code, free: free)
        alert.informativeText = err.message + "\n\nLog: \(AppLog.url.path)"
        alert.addButton(withTitle: "Settings…")
        alert.addButton(withTitle: "Open Log")
        alert.addButton(withTitle: "Quit")
        let needsInstall = [30, 31].contains(err.code) || (err.code == 13 && free)
        if err.code == 10 { alert.addButton(withTitle: "Get CrossOver") }
        if needsInstall { alert.addButton(withTitle: "Install…") }
        NSApp.activate(ignoringOtherApps: true)
        let response = alert.runModal()
        if needsInstall && response == NSApplication.ModalResponse(rawValue: NSApplication.ModalResponse.alertThirdButtonReturn.rawValue + 1) {
            showSettings(nil); showInstaller(); return
        }
        switch response {
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
