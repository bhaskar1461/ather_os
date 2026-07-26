import Foundation

// MARK: - Astrology Chart Request & Response
public struct AstrologyChartRequestV2: Codable, Sendable {
    public let year: Int
    public let month: Int
    public let day: Int
    public let hour: Int
    public let minute: Int
    public let locationName: String
    public let locationLat: Double
    public let locationLon: Double
    public let locationTimezone: String
    public let question: String?
    public let reportType: String?
    public let forceRefresh: Bool
    public let stream: Bool

    enum CodingKeys: String, CodingKey {
        case year, month, day, hour, minute, question, stream
        case locationName = "location_name"
        case locationLat = "location_lat"
        case locationLon = "location_lon"
        case locationTimezone = "location_timezone"
        case reportType = "report_type"
        case forceRefresh = "force_refresh"
    }

    public init(
        year: Int,
        month: Int,
        day: Int,
        hour: Int,
        minute: Int,
        locationName: String,
        locationLat: Double,
        locationLon: Double,
        locationTimezone: String,
        question: String? = nil,
        reportType: String? = nil,
        forceRefresh: Bool = false,
        stream: Bool = true
    ) {
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.locationName = locationName
        self.locationLat = locationLat
        self.locationLon = locationLon
        self.locationTimezone = locationTimezone
        self.question = question
        self.reportType = reportType
        self.forceRefresh = forceRefresh
        self.stream = stream
    }
}

public struct AscendantDetails: Codable, Sendable {
    public let sign: String
    public let degrees: Double
}

public struct PlanetData: Codable, Sendable {
    public let sign: String
    public let degrees: Double
    public let house: Int
    public let isRetrograde: Bool

    enum CodingKeys: String, CodingKey {
        case sign, degrees, house
        case isRetrograde = "is_retrograde"
    }
}

public struct NakshatraDetail: Codable, Sendable {
    public let name: String
    public let pada: Int
    public let lord: String
}

public struct DashaPeriod: Codable, Sendable {
    public let lord: String
    public let start: String
    public let end: String
}

public struct ChartRulesData: Codable, Sendable {
    public let strengths: [String: String]
    public let nakshatras: [String: NakshatraDetail]
    public let yogas: [String]
    public let doshas: [String]
    public let dashas: [DashaPeriod]
}

public struct ChartDataContainer: Codable, Sendable {
    public let ascendant: AscendantDetails
    public let planets: [String: PlanetData]
}

public struct ChartCalculationResponse: Codable, Sendable {
    public let chart: ChartDataContainer
    public let rules: ChartRulesData
}

// MARK: - Compatibility Models
public struct PartnerBirthDetails: Codable, Sendable {
    public let year: Int
    public let month: Int
    public let day: Int
    public let hour: Int
    public let minute: Int
    public let locationName: String
    public let locationLat: Double
    public let locationLon: Double
    public let locationTimezone: String

    enum CodingKeys: String, CodingKey {
        case year, month, day, hour, minute
        case locationName = "location_name"
        case locationLat = "location_lat"
        case locationLon = "location_lon"
        case locationTimezone = "location_timezone"
    }
}

public struct CompatibilityRequest: Codable, Sendable {
    public let partnerA: PartnerBirthDetails
    public let partnerB: PartnerBirthDetails
    public let partnerAName: String
    public let partnerBName: String

    enum CodingKeys: String, CodingKey {
        case partnerA = "partner_a"
        case partnerB = "partner_b"
        case partnerAName = "partner_a_name"
        case partnerBName = "partner_b_name"
    }
}

public struct KutaScore: Codable, Sendable {
    public let name: String
    public let obtained: Double
    public let max: Double
}

public struct CompatibilityResponse: Codable, Sendable {
    public let score: Double
    public let suitability: String
    public let kutas: [KutaScore]
    public let analysis: String
}

// MARK: - Location Search Model
public struct LocationSearchResult: Codable, Identifiable, Sendable {
    public var id: String { geoId }
    public let city: String
    public let state: String
    public let country: String
    public let latitude: Double
    public let longitude: Double
    public let timezone: String
    public let displayName: String
    public let geoId: String

    enum CodingKeys: String, CodingKey {
        case city, state, country, latitude, longitude, timezone
        case displayName = "display_name"
        case geoId = "geo_id"
    }
}

// MARK: - User Profile Model
public struct UserProfile: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let relation: String
    public let birthDate: String
    public let birthTime: String
    public let birthPlace: String
    public let latitude: Double
    public let longitude: Double
    public let timezone: String
    public let isDefault: Bool

    enum CodingKeys: String, CodingKey {
        case id, name, relation, latitude, longitude, timezone
        case birthDate = "birth_date"
        case birthTime = "birth_time"
        case birthPlace = "birth_place"
        case isDefault = "is_default"
    }
}
