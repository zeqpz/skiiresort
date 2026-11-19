// Falcos.app - the game in its own window, no browser (owner, 2026-11-17: "send me the game not in a browser",
// "send me it like a file"). It starts the local stand-in RGS (rgs/mock_rgs.py, play money) if it is not running
// already, waits for it, and shows the game in a native WebKit window. Quitting stops the server it started.
//
//   tools/highpeaks/app/build.sh   ->   dist/Falcos.app
import Cocoa
import WebKit

let projectRoot = "/Users/drewabbott/Documents/Falcos"
let gameURL = URL(string: "http://localhost:8733/index.html?sessionID=test&rgs_url=http://localhost:8733&lang=en&device=desktop")!
let pingURL = URL(string: "http://localhost:8733/index.html")!

final class AppDelegate: NSObject, NSApplicationDelegate, WKUIDelegate {
    var window: NSWindow!
    var web: WKWebView!
    var server: Process?
    var status: NSTextField!

    func applicationDidFinishLaunching(_ note: Notification) {
        let frame = NSRect(x: 0, y: 0, width: 1280, height: 800)
        window = NSWindow(contentRect: frame, styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Falcos"
        window.backgroundColor = .black
        window.center()
        window.setFrameAutosaveName("FalcosWindow")

        let cfg = WKWebViewConfiguration()
        cfg.mediaTypesRequiringUserActionForPlayback = []   // the game's sounds play without a click first
        web = WKWebView(frame: frame, configuration: cfg)
        web.uiDelegate = self
        web.autoresizingMask = [.width, .height]
        web.setValue(false, forKey: "drawsBackground")
        window.contentView = web

        status = NSTextField(labelWithString: "Starting Falcos...")
        status.textColor = .white
        status.font = .systemFont(ofSize: 18, weight: .medium)
        status.sizeToFit()
        status.frame.origin = NSPoint(x: (frame.width - status.frame.width) / 2, y: frame.height / 2)
        status.autoresizingMask = [.minXMargin, .maxXMargin, .minYMargin, .maxYMargin]
        web.addSubview(status)

        buildMenu()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        serverUp { up in
            if up { self.open() } else { self.startServer() }
        }
    }

    func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem(); main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Reload Falcos", action: #selector(reload), keyEquivalent: "r")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Falcos", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        let viewItem = NSMenuItem(); main.addItem(viewItem)
        let viewMenu = NSMenu(title: "View")
        viewMenu.addItem(withTitle: "Enter Full Screen", action: #selector(NSWindow.toggleFullScreen(_:)), keyEquivalent: "f")
        viewItem.submenu = viewMenu
        NSApp.mainMenu = main
    }

    @objc func reload() { web.reload() }

    func serverUp(_ done: @escaping (Bool) -> Void) {
        var req = URLRequest(url: pingURL); req.timeoutInterval = 1.5
        URLSession.shared.dataTask(with: req) { _, resp, _ in
            let ok = (resp as? HTTPURLResponse)?.statusCode == 200
            DispatchQueue.main.async { done(ok) }
        }.resume()
    }

    func startServer() {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: projectRoot + "/.venv/bin/python")
        p.arguments = [projectRoot + "/rgs/mock_rgs.py"]
        p.currentDirectoryURL = URL(fileURLWithPath: projectRoot)
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        do { try p.run(); server = p } catch {
            status.stringValue = "Could not start the game server: \(error.localizedDescription)"
            status.sizeToFit()
            return
        }
        status.stringValue = "Loading the game's rounds..."
        status.sizeToFit()
        waitForServer(tries: 0)
    }

    func waitForServer(tries: Int) {
        serverUp { up in
            if up { self.open(); return }
            if tries > 240 {   // two minutes: a first start can be decompressing the books
                self.status.stringValue = "The game server did not start."
                self.status.sizeToFit()
                return
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { self.waitForServer(tries: tries + 1) }
        }
    }

    func open() {
        status.removeFromSuperview()
        let args = CommandLine.arguments
        // QA: `--url <address>` opens another page of the local game (a replay); `--js <code>` runs once it loads
        var url = gameURL
        if let i = args.firstIndex(of: "--url"), i + 1 < args.count, let u = URL(string: args[i + 1]) { url = u }
        web.load(URLRequest(url: url))
        if let i = args.firstIndex(of: "--js"), i + 1 < args.count {
            let code = args[i + 1]
            DispatchQueue.main.asyncAfter(deadline: .now() + 6) { self.web.evaluateJavaScript(code, completionHandler: nil) }
        }
        // QA: `Falcos --snapshot <file.png> [seconds]` saves what the window shows, then quits
        if let i = args.firstIndex(of: "--snapshot"), i + 1 < args.count {
            let out = args[i + 1], wait = i + 2 < args.count ? Double(args[i + 2]) ?? 10 : 10
            DispatchQueue.main.asyncAfter(deadline: .now() + wait) {
                self.web.takeSnapshot(with: nil) { img, _ in
                    if let img = img, let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
                       let png = rep.representation(using: .png, properties: [:]) {
                        try? png.write(to: URL(fileURLWithPath: out))
                    }
                    NSApp.terminate(nil)
                }
            }
        }
    }

    // the game's own confirm() prompts (autoplay) as native alerts
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = message
        a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        completionHandler(a.runModal() == .alertFirstButtonReturn)
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let a = NSAlert(); a.messageText = message; a.runModal(); completionHandler()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { true }

    func applicationWillTerminate(_ note: Notification) { server?.terminate() }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
