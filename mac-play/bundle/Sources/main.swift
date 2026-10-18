// Mu The Matrix.app (MAC-BUNDLE-001): entry point, command-line modes and the AppKit UI.
//
// Double-click: start the launcher (free Wine runtime by default, or a CrossOver bottle) and quit. The settings window opens instead on
// the first run (no settings file), when Option is held, when "Start right away" is off, or after an error.
// Command line (no window): --dry-run, --check, --status, --install, --install-dry-run, --print-settings, --settings-path,
// --version, --help.
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
        let gameDir = cliArgs.dropFirst().first
        let sem = DispatchSemaphore(value: 0); var status: Int32 = 0
        AppLog.write("cli \(arg) source=\(gameDir ?? "official installer")")
        Installer.start(gameDir: gameDir, dryRun: arg == "--install-dry-run", line: { print($0); fflush(stdout) }, done: { status = $0; sem.signal() })
        while sem.wait(timeout: .now()) == .timedOut { RunLoop.main.run(until: Date().addingTimeInterval(0.05)) }
        exit(status)
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
          --print-settings  show the effective settings and file locations
          --settings-path   print the settings plist path
          --version
        Environment: MU_SETTINGS_FILE, MU_LOG_DIR, MU_LAUNCH_SCRIPT, MU_SETUP_SCRIPT, MUKIT_FREE_HOME, CX_ROOT, MUKIT_BOTTLES_DIR.
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
                : "Not installed yet. Press Install… (downloads Wine, .NET 4.8 and the game; about 20 minutes)."
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
        status.stringValue = r.error.map { "Saved. Check: \(errorTitle($0.code)). \($0.message)" } ?? "Saved. Preflight check passed."
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
/// Runs the bundled installer with the free runtime: choose where the game comes from, then watch the steps.
final class InstallWindowController: NSWindowController {
    var onFinished: ((Bool) -> Void)?
    private let downloadRadio = NSButton(radioButtonWithTitle: "Download the game from the official site (about 2.2 GB)", target: nil, action: nil)
    private let folderRadio = NSButton(radioButtonWithTitle: "Use a Mu The Matrix folder I already have…", target: nil, action: nil)
    private let folderLabel = label("", small: true)
    private let step = label("Ready. Installing takes about 20 minutes (most of it downloads) and needs about 12 GB of free space.")
    private let bar = NSProgressIndicator()
    private let logView = NSTextView()
    private lazy var startButton = NSButton(title: "Install", target: self, action: #selector(startInstall))
    private lazy var closeButton = NSButton(title: "Cancel", target: self, action: #selector(closeOrCancel))
    private var folder: String?
    private var process: Process?
    private var steps = 0, total = 14

    init() {
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 460), styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
        w.title = "Install Mu The Matrix"
        super.init(window: w)
        build()
        w.center()
    }
    required init?(coder: NSCoder) { fatalError("not used") }

    private func build() {
        guard let content = window?.contentView else { return }
        let title = label("Install Mu The Matrix"); title.font = .boldSystemFont(ofSize: 15)
        let intro = label("This sets everything up in ~/Library/Application Support/MuTheMatrix: a free Wine runtime (no CrossOver), Microsoft .NET Framework 4.8 (downloaded from Microsoft) and the game. You can keep using the Mac while it runs.", small: true)
        intro.preferredMaxLayoutWidth = 600
        downloadRadio.target = self; downloadRadio.action = #selector(sourceChanged)
        folderRadio.target = self; folderRadio.action = #selector(chooseFolder)
        downloadRadio.state = .on
        bar.isIndeterminate = false; bar.minValue = 0; bar.maxValue = Double(total); bar.style = .bar
        logView.isEditable = false
        logView.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        let scroll = NSScrollView(); scroll.documentView = logView; scroll.hasVerticalScroller = true
        logView.autoresizingMask = [.width]
        scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 180).isActive = true
        startButton.keyEquivalent = "\r"
        let spacer = NSView(); spacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let logButton = NSButton(title: "Open Log Folder", target: self, action: #selector(openLogs))
        let buttons = NSStackView(views: [logButton, spacer, closeButton, startButton])
        let stack = NSStackView(views: [title, intro, downloadRadio, folderRadio, folderLabel, step, bar, scroll, buttons])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 10
        stack.edgeInsets = NSEdgeInsets(top: 18, left: 20, bottom: 18, right: 20)
        stack.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor), stack.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            stack.topAnchor.constraint(equalTo: content.topAnchor), stack.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            scroll.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
            bar.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -40),
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
    /// (MU_AUTOTEST_GAME_DIR). Same code path as the button; used for the recorded rehearsal.
    func autotest(gameDir: String?) {
        if let g = gameDir { folder = g; folderLabel.stringValue = g; folderRadio.state = .on; downloadRadio.state = .off }
        startInstall()
    }

    private func append(_ text: String) {
        logView.textStorage?.append(NSAttributedString(string: text + "\n", attributes: [.font: logView.font as Any, .foregroundColor: NSColor.textColor]))
        logView.scrollToEndOfDocument(nil)
    }

    @objc private func startInstall() {
        startButton.isEnabled = false; downloadRadio.isEnabled = false; folderRadio.isEnabled = false
        closeButton.title = "Cancel"
        steps = 0; bar.doubleValue = 0
        step.stringValue = "Starting…"
        AppLog.write("install start source=\(folder ?? "official installer")")
        process = Installer.start(gameDir: folder, line: { [weak self] l in self?.handle(l) }, done: { [weak self] st in self?.finished(st) })
    }

    private func handle(_ l: String) {
        AppLog.write("install: " + l)
        // "== 5/14 .NET Framework 4.8" -> progress; curl's "###   12.3%" lines only update the step text.
        if l.hasPrefix("== ") {
            let body = l.dropFirst(3)
            if let slash = body.firstIndex(of: "/"), let n = Int(body[body.startIndex..<slash].filter(\.isNumber)) {
                let rest = body[body.index(after: slash)...]
                if let sp = rest.firstIndex(of: " "), let t = Int(rest[rest.startIndex..<sp]) { total = t; bar.maxValue = Double(t) }
                steps = n; bar.doubleValue = Double(max(0, n - 1))
            }
            step.stringValue = "Step " + body
            append(l)
        } else if l.contains("%") && l.contains("#") {
            if let pct = l.split(separator: " ").last { step.stringValue = step.stringValue.components(separatedBy: " — ").first! + " — downloading \(pct)" }
        } else {
            append(l)
        }
    }

    private func finished(_ status: Int32) {
        process = nil
        let ok = status == 0
        AppLog.write("install finished status \(status)")
        bar.doubleValue = ok ? bar.maxValue : bar.doubleValue
        step.stringValue = ok ? "Done. Mu The Matrix is installed. Close this window and press Play."
            : "The installation stopped (status \(status)). The last lines above say why; fix it and press Install again: finished steps are skipped."
        closeButton.title = ok ? "Close" : "Close"
        startButton.title = ok ? "Done" : "Try Again"
        startButton.isEnabled = !ok
        if ok { startButton.isEnabled = false }
        onFinished?(ok)
    }

    @objc private func closeOrCancel() {
        if let p = process, p.isRunning {
            let a = NSAlert(); a.messageText = "Stop the installation?"
            a.informativeText = "You can start it again later; finished steps are skipped."
            a.addButton(withTitle: "Stop"); a.addButton(withTitle: "Continue")
            guard a.runModal() == .alertFirstButtonReturn else { return }
            p.terminate()
            return
        }
        window?.orderOut(nil)
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
        let alert = NSAlert()
        alert.alertStyle = err.code == 14 ? .informational : .warning
        alert.messageText = errorTitle(err.code)
        alert.informativeText = err.message + "\n\nLog: \(AppLog.url.path)"
        alert.addButton(withTitle: "Settings…")
        alert.addButton(withTitle: "Open Log")
        alert.addButton(withTitle: "Quit")
        let needsInstall = [30, 31].contains(err.code) || (err.code == 13 && LauncherSettings.load().runtime == "free")
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
            settingsWindow?.showStatus("Last start failed: \(errorTitle(err.code)). \(err.message)")
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
