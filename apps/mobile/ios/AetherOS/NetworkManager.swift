import Foundation

struct ErrorDetailResponse: Decodable {
    let detail: String?
    let error: NestedError?
    
    struct NestedError: Decodable {
        let message: String?
    }
    
    var cleanMessage: String? {
        if let detail = detail { return detail }
        if let msg = error?.message { return msg }
        return nil
    }
}

/// Main Async HTTP Service for interacting with AetherOS Backend
public actor NetworkManager {
    public static let shared = NetworkManager()
    
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    
    public init(baseURLString: String = "https://ather-os.de5.net") {
        guard let url = URL(string: baseURLString) else {
            fatalError("Invalid base URL string")
        }
        self.baseURL = url
        
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30.0
        config.timeoutIntervalForResource = 300.0
        self.session = URLSession(configuration: config)
        
        self.decoder = JSONDecoder()
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        self.decoder.dateDecodingStrategy = .custom({ decoder in
            let container = try decoder.singleValueContainer()
            let dateStr = try container.decode(String.self)
            if let date = formatter.date(from: dateStr) { return date }
            let isoFormatter = ISO8601DateFormatter()
            isoFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = isoFormatter.date(from: dateStr) { return date }
            let basicFormatter = ISO8601DateFormatter()
            if let date = basicFormatter.date(from: dateStr) { return date }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid date format: \(dateStr)")
        })
        
        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
    }
    
    // MARK: - Core Request Execution
    
    public func request<T: Decodable, B: Encodable>(
        path: String,
        method: String = "GET",
        body: B? = nil,
        requiresAuth: Bool = true
    ) async throws -> T {
        let url = baseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("true", forHTTPHeaderField: "bypass-tunnel-warning")
        
        if requiresAuth {
            if let token = KeychainManager.shared.readString(key: "access_token") {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            } else {
                throw APIError.unauthorized
            }
        }
        
        if let body = body {
            request.httpBody = try encoder.encode(body)
        }
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.networkError(NSError(domain: "InvalidResponse", code: 0))
        }
        
        // Handle 401 Unauthorized -> Refresh token flow
        if httpResponse.statusCode == 401 && requiresAuth {
            let refreshed = try await refreshToken()
            if refreshed {
                return try await self.request(path: path, method: method, body: body, requiresAuth: true)
            } else {
                KeychainManager.shared.clearAll()
                throw APIError.unauthorized
            }
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            if let decodedError = try? JSONDecoder().decode(ErrorDetailResponse.self, from: data),
               let cleanMsg = decodedError.cleanMessage {
                throw APIError.httpError(statusCode: httpResponse.statusCode, message: cleanMsg)
            }
            let message = String(data: data, encoding: .utf8) ?? "Unknown server error"
            throw APIError.httpError(statusCode: httpResponse.statusCode, message: message)
        }
        
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    public func request<T: Decodable>(
        path: String,
        method: String = "GET",
        requiresAuth: Bool = true
    ) async throws -> T {
        let emptyBody: String? = nil
        return try await request(path: path, method: method, body: emptyBody, requiresAuth: requiresAuth)
    }
    
    // MARK: - Authentication Methods

    public func register(name: String, email: String, password: String) async throws -> User {
        struct RegisterPayload: Encodable {
            let name: String
            let email: String
            let password: String
        }
        let payload = RegisterPayload(name: name, email: email, password: password)
        return try await request(path: "/auth/register", method: "POST", body: payload, requiresAuth: false)
    }
    
    public func login(email: String, password: String) async throws -> TokenResponse {
        struct LoginPayload: Encodable {
            let email: String
            let password: String
        }
        let payload = LoginPayload(email: email, password: password)
        let response: TokenResponse = try await request(path: "/auth/login", method: "POST", body: payload, requiresAuth: false)
        _ = KeychainManager.shared.save(key: "access_token", string: response.accessToken)
        _ = KeychainManager.shared.save(key: "refresh_token", string: response.refreshToken)
        _ = KeychainManager.shared.save(key: "user_email", string: email)
        return response
    }
    
    public func requestOTP(email: String) async throws {
        struct OTPPayload: Encodable {
            let email: String
        }
        struct MessageDetail: Decodable { let message: String }
        let _: MessageDetail = try await request(path: "/auth/otp/request", method: "POST", body: OTPPayload(email: email), requiresAuth: false)
    }
    
    public func verifyOTP(email: String, code: String) async throws -> TokenResponse {
        struct OTPVerifyPayload: Encodable {
            let email: String
            let code: String
        }
        let payload = OTPVerifyPayload(email: email, code: code)
        let response: TokenResponse = try await request(path: "/auth/otp/verify", method: "POST", body: payload, requiresAuth: false)
        _ = KeychainManager.shared.save(key: "access_token", string: response.accessToken)
        _ = KeychainManager.shared.save(key: "refresh_token", string: response.refreshToken)
        _ = KeychainManager.shared.save(key: "user_email", string: email)
        return response
    }
    
    public func googleLogin(credential: String) async throws -> TokenResponse {
        struct GoogleLoginPayload: Encodable {
            let credential: String
        }
        let response: TokenResponse = try await request(path: "/auth/google", method: "POST", body: GoogleLoginPayload(credential: credential), requiresAuth: false)
        _ = KeychainManager.shared.save(key: "access_token", string: response.accessToken)
        _ = KeychainManager.shared.save(key: "refresh_token", string: response.refreshToken)
        return response
    }
    
    private func refreshToken() async throws -> Bool {
        guard let refreshToken = KeychainManager.shared.readString(key: "refresh_token") else {
            return false
        }
        struct RefreshPayload: Encodable {
            let refresh_token: String
        }
        let url = baseURL.appendingPathComponent("/auth/refresh")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(RefreshPayload(refresh_token: refreshToken))
        
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            return false
        }
        let tokenResponse = try decoder.decode(TokenResponse.self, from: data)
        _ = KeychainManager.shared.save(key: "access_token", string: tokenResponse.accessToken)
        _ = KeychainManager.shared.save(key: "refresh_token", string: tokenResponse.refreshToken)
        return true
    }
}
