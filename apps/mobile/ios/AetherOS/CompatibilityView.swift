import SwiftUI

/// Native SwiftUI Ashtakoota Compatibility Matching View
struct CompatibilityView: View {
    @State private var partner1Name: String = "Self"
    @State private var partner2Name: String = "Partner"
    @State private var totalScore: Double = 28.5
    @State private var maxScore: Double = 36.0
    @State private var isCalculating: Bool = false
    
    let gunaBreakdown = [
        ("Varna", 1.0, 1.0, "Spiritual compatibility & work disposition"),
        ("Vashya", 2.0, 2.0, "Mutual attraction & control balance"),
        ("Tara", 3.0, 3.0, "Destiny & longevity alignment"),
        ("Yoni", 3.5, 4.0, "Intimate compatibility & physical harmony"),
        ("Maitri", 4.0, 5.0, "Psychological friendship & communication"),
        ("Gana", 5.0, 6.0, "Temperament (Deva, Manushya, Rakshasa)"),
        ("Bhakoot", 7.0, 7.0, "Family prosperity, wealth & emotional bond"),
        ("Nadi", 3.0, 8.0, "Genetic health & progeny compatibility")
    ]

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Score Gauge Card
                    VStack(spacing: 12) {
                        ZStack {
                            Circle()
                                .stroke(Color.white.opacity(0.1), lineWidth: 14)
                                .frame(width: 140, height: 140)

                            Circle()
                                .trim(from: 0, to: CGFloat(totalScore / maxScore))
                                .stroke(
                                    LinearGradient(colors: [.indigo, .purple, .pink], startPoint: .topLeading, endPoint: .bottomTrailing),
                                    style: StrokeStyle(lineWidth: 14, lineCap: .round)
                                )
                                .frame(width: 140, height: 140)
                                .rotationEffect(.degrees(-90))
                                .animation(.easeOut(duration: 1.0), value: totalScore)

                            VStack(spacing: 2) {
                                Text(String(format: "%.1f", totalScore))
                                    .font(.system(size: 32, weight: .bold, design: .rounded))
                                    .foregroundColor(.white)
                                Text("out of 36")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }

                        Text("Excellent Match (79%)")
                            .font(.subheadline.bold())
                            .foregroundColor(.emerald)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 4)
                            .background(Color.emerald.opacity(0.15))
                            .cornerRadius(12)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color(red: 0.05, green: 0.05, blue: 0.08))
                    .cornerRadius(20)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(Color.white.opacity(0.08), lineWidth: 1)
                    )
                    .padding(.horizontal)

                    // Ashtakoota Guna Breakdown List
                    VStack(alignment: .leading, spacing: 14) {
                        Text("Ashtakoota Guna Breakdown")
                            .font(.headline)
                            .foregroundColor(.white)

                        ForEach(gunaBreakdown, id: \.0) { item in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(item.0)
                                        .font(.subheadline.bold())
                                        .foregroundColor(.white)
                                    Spacer()
                                    Text("\(String(format: "%.1f", item.1)) / \(String(format: "%.0f", item.2))")
                                        .font(.subheadline.monospaced())
                                        .foregroundColor(item.1 >= item.2 * 0.6 ? .indigo : .amber)
                                }
                                Text(item.3)
                                    .font(.caption)
                                    .foregroundColor(.gray)
                                
                                GeometryReader { geo in
                                    ZStack(alignment: .leading) {
                                        RoundedRectangle(cornerRadius: 4)
                                            .fill(Color.white.opacity(0.08))
                                            .frame(height: 6)
                                        RoundedRectangle(cornerRadius: 4)
                                            .fill(item.1 >= item.2 * 0.6 ? Color.indigo : Color.amber)
                                            .frame(width: geo.size.width * CGFloat(item.1 / item.2), height: 6)
                                    }
                                }
                                .frame(height: 6)
                            }
                            .padding(.bottom, 4)
                        }
                    }
                    .padding()
                    .background(Color(red: 0.05, green: 0.05, blue: 0.08))
                    .cornerRadius(20)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(Color.white.opacity(0.08), lineWidth: 1)
                    )
                    .padding(.horizontal)
                }
                .padding(.vertical)
            }
            .background(Color.black.ignoresSafeArea())
            .navigationTitle("Vedic Compatibility")
        }
    }
}

extension Color {
    static let emerald = Color(red: 0.2, green: 0.8, blue: 0.5)
}
