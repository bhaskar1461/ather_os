import Foundation

/// API error types returned by the backend or network layer
public enum APIError: Error, LocalizedError {
    case invalidURL
    case networkError(Error)
    case httpError(statusCode: Int, message: String)
    case decodingError(Error)
    case unauthorized
    case serverError(String)
    
    public var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The request URL is invalid."
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .httpError(let code, let msg):
            return "HTTP \(code): \(msg)"
        case .decodingError(let error):
            return "Failed to parse response: \(error.localizedDescription)"
        case .unauthorized:
            return "Session expired or unauthorized. Please log in again."
        case .serverError(let msg):
            return "Server error: \(msg)"
        }
    }
}

/// Token response returned on authentication
public struct TokenResponse: Codable, Sendable {
    public let accessToken: String
    public let refreshToken: String
    public let tokenType: String
    public let expiresIn: Int
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
    }
}

/// User model matching backend response
public struct User: Codable, Identifiable, Sendable {
    public let id: UUID
    public let email: String
    public let name: String?
    public let avatarUrl: String?
    public let role: String
    public let isVerified: Bool
    public let createdAt: Date
    public let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id
        case email
        case name
        case avatarUrl = "avatar_url"
        case role
        case isVerified = "is_verified"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

/// Workspace response
public struct Workspace: Codable, Identifiable, Sendable {
    public let id: UUID
    public let name: String
    public let description: String?
    public let ownerId: UUID
    public let createdAt: Date
    public let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id
        case name
        case description
        case ownerId = "owner_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

/// Project response
public struct Project: Codable, Identifiable, Sendable {
    public let id: UUID
    public let workspaceId: UUID
    public let name: String
    public let description: String?
    public let createdAt: Date
    public let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id
        case workspaceId = "workspace_id"
        case name
        case description
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

/// Chat session response
public struct ChatSession: Codable, Identifiable, Sendable {
    public let id: UUID
    public let projectId: UUID
    public let folderId: UUID?
    public let modelId: String
    public let agentId: UUID?
    public let title: String
    public let isPinned: Bool
    public let isArchived: Bool
    public let createdAt: Date
    public let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id
        case projectId = "project_id"
        case folderId = "folder_id"
        case modelId = "model_id"
        case agentId = "agent_id"
        case title
        case isPinned = "is_pinned"
        case isArchived = "is_archived"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

/// Chat message response
public struct ChatMessage: Codable, Identifiable, Sendable {
    public let id: UUID
    public let chatId: UUID
    public let role: String
    public let content: String
    public let promptTokens: Int?
    public let completionTokens: Int?
    public let totalTokens: Int?
    public let latencyMs: Int?
    public let createdAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id
        case chatId = "chat_id"
        case role
        case content
        case promptTokens = "prompt_tokens"
        case completionTokens = "completion_tokens"
        case totalTokens = "total_tokens"
        case latencyMs = "latency_ms"
        case createdAt = "created_at"
    }
}

/// System Health Response
public struct HealthResponse: Codable, Sendable {
    public let status: String
    public let version: String
    public let database: String
    public let redis: String
}
