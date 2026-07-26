import SwiftUI

@main
struct AetherOSApp: App {
    @StateObject private var authViewModel = AuthViewModel()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authViewModel)
                .preferredColorScheme(.dark)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    
    var body: some View {
        Group {
            if authViewModel.isAuthenticated {
                MainTabView()
            } else {
                AuthenticationView()
            }
        }
        .animation(.easeInOut, value: authViewModel.isAuthenticated)
    }
}

// MARK: - Auth View Model
@MainActor
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated: Bool = false
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil
    
    init() {
        checkSession()
    }
    
    func checkSession() {
        if KeychainManager.shared.readString(key: "access_token") != nil {
            self.isAuthenticated = true
        }
    }

    func register(name: String, email: String, password: String) async {
        isLoading = true
        errorMessage = nil
        do {
            _ = try await NetworkManager.shared.register(name: name, email: email, password: password)
            // Log in immediately after registering
            _ = try await NetworkManager.shared.login(email: email, password: password)
            isAuthenticated = true
        } catch {
            errorMessage = formatError(error)
        }
        isLoading = false
    }
    
    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil
        do {
            _ = try await NetworkManager.shared.login(email: email, password: password)
            isAuthenticated = true
        } catch {
            errorMessage = formatError(error)
        }
        isLoading = false
    }
    
    func verifyOTP(email: String, code: String) async {
        isLoading = true
        errorMessage = nil
        do {
            _ = try await NetworkManager.shared.verifyOTP(email: email, code: code)
            isAuthenticated = true
        } catch {
            errorMessage = formatError(error)
        }
        isLoading = false
    }

    private func formatError(_ error: Error) -> String {
        let msg = error.localizedDescription
        if msg.contains("401") || msg.contains("Invalid email or password") {
            return "Invalid email or password. Please check your credentials or create a new account."
        }
        if msg.contains("400") || msg.contains("already exists") {
            return "An account with this email already exists. Please sign in instead."
        }
        return msg
    }
    
    func logout() {
        KeychainManager.shared.clearAll()
        isAuthenticated = false
    }
}

// MARK: - Navigation & Main Views
struct MainTabView: View {
    var body: some View {
        TabView {
            CosmicHubView()
                .tabItem {
                    Label("My Chart", systemImage: "sparkles")
                }

            AstrologyView()
                .tabItem {
                    Label("Astrology", systemImage: "orbit")
                }

            CompatibilityView()
                .tabItem {
                    Label("Match", systemImage: "heart.fill")
                }

            TimelineView()
                .tabItem {
                    Label("Timeline", systemImage: "clock.fill")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
        }
        .accentColor(Color(red: 0.39, green: 0.40, blue: 0.95))
    }
}

struct AuthenticationView: View {
    @State private var name = ""
    @State private var email = ""
    @State private var password = ""
    @State private var otpCode = ""
    @State private var isRegisterMode = false
    @State private var isOTPMode = false
    @State private var otpSent = false
    @EnvironmentObject var authViewModel: AuthViewModel
    
    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            
            VStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.system(size: 54))
                    .foregroundStyle(.linearGradient(colors: [Color(red: 0.39, green: 0.40, blue: 0.95), .purple], startPoint: .topLeading, endPoint: .bottomTrailing))
                
                Text("AetherOS")
                    .font(.largeTitle.bold())
                    .foregroundColor(.white)
                
                Text(isRegisterMode ? "Create Your Cosmic Profile" : "Luxury Personal AI Operating System")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }
            
            VStack(spacing: 14) {
                if isRegisterMode {
                    TextField("Full Name", text: $name)
                        .textFieldStyle(.roundedBorder)
                }

                TextField("Email Address", text: $email)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.emailAddress)
                
                if !isOTPMode {
                    SecureField("Password (min. 8 chars)", text: $password)
                        .textFieldStyle(.roundedBorder)
                } else if otpSent {
                    TextField("6-Digit OTP Code", text: $otpCode)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.numberPad)
                }
                
                if let error = authViewModel.errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 8)
                }
                
                Button(action: {
                    Task {
                        HapticManager.shared.impact(.medium)
                        if isRegisterMode {
                            await authViewModel.register(name: name, email: email, password: password)
                        } else if isOTPMode {
                            if !otpSent {
                                try? await NetworkManager.shared.requestOTP(email: email)
                                otpSent = true
                            } else {
                                await authViewModel.verifyOTP(email: email, code: otpCode)
                            }
                        } else {
                            await authViewModel.login(email: email, password: password)
                        }
                    }
                }) {
                    HStack {
                        if authViewModel.isLoading {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text(isRegisterMode ? "Create Account" : (isOTPMode ? (otpSent ? "Verify Code" : "Send OTP Email") : "Sign In"))
                                .bold()
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(LinearGradient(colors: [Color(red: 0.39, green: 0.40, blue: 0.95), Color.purple], startPoint: .leading, endPoint: .trailing))
                    .foregroundColor(.white)
                    .cornerRadius(12)
                    .shadow(color: Color(red: 0.39, green: 0.40, blue: 0.95).opacity(0.3), radius: 8, x: 0, y: 4)
                }
                
                HStack(spacing: 16) {
                    Button(action: {
                        withAnimation {
                            isRegisterMode.toggle()
                            isOTPMode = false
                            authViewModel.errorMessage = nil
                        }
                    }) {
                        Text(isRegisterMode ? "Already have an account? Sign In" : "Need an account? Register")
                            .font(.footnote)
                            .foregroundColor(Color(red: 0.39, green: 0.40, blue: 0.95))
                    }
                }
                .padding(.top, 4)
            }
            .padding(.horizontal, 32)
            
            Spacer()
        }
        .background(Color.black.ignoresSafeArea())
    }
}

struct DashboardView: View {
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Welcome to AetherOS")
                        .font(.title2.bold())
                        .padding(.horizontal)
                    
                    RoundedRectangle(cornerRadius: 16)
                        .fill(LinearGradient(colors: [.purple.opacity(0.6), .blue.opacity(0.6)], startPoint: .topLeading, endPoint: .bottomTrailing))
                        .frame(height: 140)
                        .overlay(
                            VStack(alignment: .leading) {
                                Text("System Operational")
                                    .font(.headline)
                                    .foregroundColor(.white)
                                Text("PostgreSQL & Redis Online")
                                    .font(.subheadline)
                                    .foregroundColor(.white.opacity(0.8))
                            }
                            .padding()
                        )
                        .padding(.horizontal)
                }
            }
            .navigationTitle("Dashboard")
        }
    }
}

struct WorkspacesView: View {
    var body: some View {
        NavigationView {
            List {
                Text("Default Workspace")
                Text("Astrology & Research Workspace")
            }
            .navigationTitle("Workspaces")
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    
    var body: some View {
        NavigationView {
            List {
                Section(header: Text("Account")) {
                    Button(action: {
                        authViewModel.logout()
                    }) {
                        Text("Sign Out")
                            .foregroundColor(.red)
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}
