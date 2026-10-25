// APP-LIVE-001 (sketch, signatures only): the app side of a live client.
//
// Changes to native/app/Sources/PreviewCore.swift:
//   - LaunchPlan.make no longer sets DYLD_INSERT_LIBRARIES (mu-nonet leaves the product build;
//     the transport allowlist in native/net replaces it) and no longer passes feature flags
//     (--combat --progress --items --npc --players --helper): the server decides what exists.
//   - No credentials on the command line or in the environment; logs record the plan with the
//     endpoint, never account data. The account is typed into the game's own account dialog
//     (GFx onLoginOkClick, GFX-ACCOUNT-001); "remember account" stores it in the Keychain and the
//     client asks the launcher for it over an inherited pipe at the dialog, not at launch.
//   - The service endpoint is configuration from the operator contract (NET-CONTRACT-001),
//     shipped in the signed bundle's Info.plist and overridable in Settings for fixture tests.

import Foundation

public struct ServiceEndpoint: Codable, Equatable {
    public var host: String
    public var port: UInt16
}

public struct LivePlan {
    public var executable: URL                 // Contents/MacOS/mu-client (no fixture code linked)
    public var arguments: [String]             // --root, --native-data, --endpoint host:port, --journal (opt-in)
    public var environment: [String: String]   // MU_LANG_DIR, MU_GFX_LIB, MU_EXIT_WITH_PARENT only
    public var credentialPipe: FileHandle?     // answers one account request from the client

    public static func make(settings: Settings, bundle: Bundle) throws -> LivePlan { fatalError("not implemented") }
}

public protocol CredentialStore {
    func account(for endpoint: ServiceEndpoint) throws -> (account: String, password: Data)?
    func remember(account: String, password: Data, for endpoint: ServiceEndpoint) throws
    func forget(for endpoint: ServiceEndpoint) throws
}

public struct KeychainCredentialStore: CredentialStore {
    public func account(for endpoint: ServiceEndpoint) throws -> (account: String, password: Data)? { fatalError("not implemented") }
    public func remember(account: String, password: Data, for endpoint: ServiceEndpoint) throws { fatalError("not implemented") }
    public func forget(for endpoint: ServiceEndpoint) throws { fatalError("not implemented") }
}

// APP-DIST-001: Developer ID + hardened runtime + notarization become possible once no dyld
// insertion is needed. Entitlements: network client only (com.apple.security.network.client
// under the App Sandbox if adopted; otherwise none beyond hardened runtime defaults).
public enum DistributionCheck {
    public static func verifySignedBundle(at url: URL) throws -> [String] { fatalError("not implemented") }
}
