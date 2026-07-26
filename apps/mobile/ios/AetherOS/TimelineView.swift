import SwiftUI

/// Native SwiftUI Vimsottari Dasha Life Timeline View
struct TimelineView: View {
    struct DashaPeriod: Identifiable {
        let id = UUID()
        let planet: String
        let startDate: String
        let endDate: String
        let isCurrent: Bool
        let description: String
    }
    
    let dashaPeriods: [DashaPeriod] = [
        DashaPeriod(planet: "Rahu", startDate: "2020", endDate: "2038", isCurrent: true, description: "Major expansion, foreign connections, tech innovation, & ambition."),
        DashaPeriod(planet: "Jupiter", startDate: "2038", endDate: "2054", isCurrent: false, description: "Spiritual wisdom, teaching, mentorship, wealth, and family expansion."),
        DashaPeriod(planet: "Saturn", startDate: "2054", endDate: "2073", isCurrent: false, description: "Mastery, legacy building, discipline, executive responsibility, and endurance.")
    ]

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Vimsottari Dasha Timeline")
                        .font(.title3.bold())
                        .foregroundColor(.white)
                        .padding(.horizontal)

                    // Timeline Cards List
                    VStack(spacing: 16) {
                        ForEach(dashaPeriods) { period in
                            HStack(alignment: .top, spacing: 14) {
                                // Timeline Node Pillar
                                VStack(spacing: 4) {
                                    Circle()
                                        .fill(period.isCurrent ? Color.emerald : Color.indigo.opacity(0.6))
                                        .frame(width: 14, height: 14)
                                        .shadow(color: period.isCurrent ? Color.emerald.opacity(0.6) : Color.clear, radius: 6)

                                    Rectangle()
                                        .fill(Color.white.opacity(0.1))
                                        .frame(width: 2)
                                }
                                .padding(.top, 4)

                                // Card Content
                                VStack(alignment: .leading, spacing: 8) {
                                    HStack {
                                        Text("\(period.planet) Mahadasha")
                                            .font(.headline)
                                            .foregroundColor(.white)

                                        Spacer()

                                        if period.isCurrent {
                                            HStack(spacing: 4) {
                                                Circle()
                                                    .fill(Color.emerald)
                                                    .frame(width: 6, height: 6)
                                                Text("YOU ARE HERE")
                                                    .font(.system(size: 9, weight: .bold))
                                                    .foregroundColor(.emerald)
                                            }
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 3)
                                            .background(Color.emerald.opacity(0.15))
                                            .cornerRadius(6)
                                        }
                                    }

                                    Text("\(period.startDate) — \(period.endDate)")
                                        .font(.caption.monospaced())
                                        .foregroundColor(.indigo)

                                    Text(period.description)
                                        .font(.subheadline)
                                        .foregroundColor(.gray)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color(red: 0.05, green: 0.05, blue: 0.08))
                                .cornerRadius(16)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 16)
                                        .stroke(period.isCurrent ? Color.emerald.opacity(0.4) : Color.white.opacity(0.08), lineWidth: 1)
                                )
                            }
                            .padding(.horizontal)
                        }
                    }
                }
                .padding(.vertical)
            }
            .background(Color.black.ignoresSafeArea())
            .navigationTitle("Life Timeline")
        }
    }
}
