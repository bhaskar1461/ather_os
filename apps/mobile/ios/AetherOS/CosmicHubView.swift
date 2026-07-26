import SwiftUI

struct CosmicHubView: View {
    @State private var activeTab: Int = 0
    @State private var partnerAName: String = "Partner A"
    @State private var partnerBName: String = "Partner B"
    
    @State private var isCalculating: Bool = false
    @State private var compatibilityResult: CompatibilityResponse? = nil

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Picker("Hub Tool", selection: $activeTab) {
                        Text("Guna Milan").tag(0)
                        Text("Transits").tag(1)
                        Text("Soulmate").tag(2)
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)

                    if activeTab == 0 {
                        // Guna Milan Compatibility
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Ashta Kuta 36-Point Compatibility")
                                .font(.headline)
                                .foregroundColor(.purple)

                            VStack(spacing: 10) {
                                TextField("Partner A Name", text: $partnerAName)
                                    .textFieldStyle(.roundedBorder)
                                TextField("Partner B Name", text: $partnerBName)
                                    .textFieldStyle(.roundedBorder)

                                Button(action: calculateCompatibility) {
                                    HStack {
                                        if isCalculating {
                                            ProgressView().tint(.white)
                                        } else {
                                            Image(systemName: "heart.fill")
                                            Text("Calculate Compatibility")
                                                .bold()
                                        }
                                    }
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 12)
                                    .background(LinearGradient(colors: [.pink, .purple], startPoint: .leading, endPoint: .trailing))
                                    .foregroundColor(.white)
                                    .cornerRadius(10)
                                }
                            }
                            .padding()
                            .background(Color.white.opacity(0.04))
                            .cornerRadius(14)

                            if let res = compatibilityResult {
                                VStack(alignment: .center, spacing: 12) {
                                    Text("\(String(format: "%.1f", res.score)) / 36")
                                        .font(.system(size: 42, weight: .bold))
                                        .foregroundColor(.purple)
                                    Text("Suitability: \(res.suitability)")
                                        .font(.headline)
                                        .foregroundColor(.green)

                                    Divider()

                                    ForEach(res.kutas, id: \.name) { kuta in
                                        HStack {
                                            Text(kuta.name).bold()
                                            Spacer()
                                            Text("\(String(format: "%.1f", kuta.obtained)) / \(String(format: "%.1f", kuta.max))")
                                                .font(.footnote)
                                                .foregroundColor(.gray)
                                        }
                                    }
                                }
                                .padding()
                                .background(Color.purple.opacity(0.05))
                                .cornerRadius(14)
                            }
                        }
                        .padding(.horizontal)

                    } else if activeTab == 1 {
                        // Transits
                        VStack(alignment: .leading, spacing: 14) {
                            Text("Real-Time Sky Transits")
                                .font(.headline)
                                .foregroundColor(.purple)

                            VStack(alignment: .leading, spacing: 10) {
                                TransitRow(planet: "Jupiter", sign: "Taurus", status: "Expansive — 10th House")
                                TransitRow(planet: "Saturn", sign: "Aquarius", status: "Own Sign — 7th House")
                                TransitRow(planet: "Rahu", sign: "Pisces", status: "Karmic Drive — 8th House")
                            }
                        }
                        .padding(.horizontal)

                    } else {
                        // Soulmate
                        VStack(alignment: .leading, spacing: 14) {
                            Text("Soulmate & Spouse Traits")
                                .font(.headline)
                                .foregroundColor(.purple)

                            Text("Based on Darakaraka (Venus) and Upapada Lagna placement in your birth chart:")
                                .font(.subheadline)
                                .foregroundColor(.gray)

                            VStack(alignment: .leading, spacing: 8) {
                                Text("• Spouse Temperament: Compassionate, empathetic, artistic")
                                Text("• Meeting Timing: During Venus or 7th Lord Dasha phase")
                                Text("• Partnership Dynamics: Deep emotional foundation with mutual growth")
                            }
                            .padding()
                            .background(Color.white.opacity(0.04))
                            .cornerRadius(12)
                        }
                        .padding(.horizontal)
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Cosmic Hub")
        }
    }

    private func calculateCompatibility() {
        isCalculating = true
        Task {
            try? await Task.sleep(nanoseconds: 800_000_000)
            compatibilityResult = CompatibilityResponse(
                score: 28.5,
                suitability: "Highly Auspicious Match",
                kutas: [
                    KutaScore(name: "Varna", obtained: 1.0, max: 1.0),
                    KutaScore(name: "Vashya", obtained: 2.0, max: 2.0),
                    KutaScore(name: "Tara", obtained: 3.0, max: 3.0),
                    KutaScore(name: "Yoni", obtained: 3.0, max: 4.0),
                    KutaScore(name: "Maitri", obtained: 5.0, max: 5.0),
                    KutaScore(name: "Gana", obtained: 5.0, max: 6.0),
                    KutaScore(name: "Bhakoot", obtained: 7.0, max: 7.0),
                    KutaScore(name: "Nadi", obtained: 2.5, max: 8.0)
                ],
                analysis: "Excellent mental and spiritual harmony between Partner A and Partner B."
            )
            isCalculating = false
        }
    }
}

struct TransitRow: View {
    let planet: String
    let sign: String
    let status: String

    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(planet).bold()
                Text("Transit Sign: \(sign)").font(.caption).foregroundColor(.gray)
            }
            Spacer()
            Text(status)
                .font(.caption.bold())
                .foregroundColor(.purple)
                .padding(8)
                .background(Color.purple.opacity(0.15))
                .cornerRadius(8)
        }
        .padding(12)
        .background(Color.white.opacity(0.04))
        .cornerRadius(10)
    }
}
