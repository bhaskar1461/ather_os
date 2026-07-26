import Foundation
import LocalAuthentication

/// Native iOS Biometric Authentication Manager (Face ID / Touch ID)
@MainActor
final class BiometricManager: ObservableObject {
    static let shared = BiometricManager()
    
    @Published var isBiometricsAvailable: Bool = false
    @Published var biometricType: LABiometryType = .none
    
    private init() {
        canEvaluatePolicy()
    }
    
    func canEvaluatePolicy() -> Bool {
        let context = LAContext()
        var error: NSError?
        let canEvaluate = context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error)
        self.isBiometricsAvailable = canEvaluate
        self.biometricType = context.biometryType
        return canEvaluate
    }
    
    func authenticateWithBiometrics(reason: String = "Unlock AetherOS Cosmic Intelligence") async -> Bool {
        let context = LAContext()
        var error: NSError?
        
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            return false
        }
        
        do {
            let success = try await context.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: reason
            )
            if success {
                HapticManager.shared.notification(.success)
            } else {
                HapticManager.shared.notification(.error)
            }
            return success
        } catch {
            HapticManager.shared.notification(.error)
            return false
        }
    }
}
