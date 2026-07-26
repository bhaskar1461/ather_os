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
    
    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil
        do {
            _ = try await NetworkManager.shared.login(email: email, password: password)
            isAuthenticated = true
        } catch {
            errorMessage = error.localizedDescription
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
            errorMessage = error.localizedDescription
        }
        isLoading = false
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
    @State private var email = ""
    @State private var password = ""
    @State private var otpCode = ""
    @State private var isOTPMode = false
    @State private var otpSent = false
    @EnvironmentObject var authViewModel: AuthViewModel
    
    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            
            VStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.system(size: 54))
                    .foregroundStyle(.linearGradient(colors: [.purple, .blue], startPoint: .topLeading, endPoint: .bottomTrailing))
                
                Text("AetherOS")
                    .font(.largeTitle.bold())
                
                Text("Luxury Personal AI Operating System")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }
            
            VStack(spacing: 16) {
                TextField("Email Address", text: $email)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.emailAddress)
                
                if !isOTPMode {
                    SecureField("Password", text: $password)
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
                }
                
                Button(action: {
                    Task {
                        if isOTPMode {
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
                        } else {
                            Text(isOTPMode ? (otpSent ? "Verify Code" : "Send OTP Email") : "Sign In")
                                .bold()
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.purple)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                
                Button(action: {
                    isOTPMode.toggle()
                    otpSent = false
                }) {
                    Text(isOTPMode ? "Use Password Login" : "Login via Email OTP")
                        .font(.footnote)
                        .foregroundColor(.purple)
                }
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
