import SwiftUI

struct AstrologyView: View {
    @State private var year: String = "2000"
    @State private var month: String = "1"
    @State private var day: String = "1"
    @State private var hour: String = "12"
    @State private var minute: String = "0"
    @State private var locationName: String = "Hyderabad, India"
    @State private var lat: Double = 17.3850
    @State private var lon: Double = 78.4867
    @State private var timezone: String = "Asia/Kolkata"
    
    @State private var isCalculating: Bool = false
    @State private var activeTab: Int = 0 // 0: Interpretation, 1: Longitudes, 2: Rules & Dashas
    @State private var chartResult: ChartCalculationResponse? = nil
    @State private var readingText: String = ""
    @State private var errorMessage: String? = nil
    
    // Follow-up chat state
    @State private var chatInput: String = ""
    @State private var chatMessages: [(role: String, content: String)] = []
    @State private var isStreamingChat: Bool = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Form Section
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Birth Coordinates & Time")
                            .font(.caption.bold())
                            .foregroundColor(.purple)
                            .textCase(.uppercase)
                        
                        HStack(spacing: 8) {
                            TextField("Day", text: $day)
                                .keyboardType(.numberPad)
                                .textFieldStyle(.roundedBorder)
                            TextField("Month", text: $month)
                                .keyboardType(.numberPad)
                                .textFieldStyle(.roundedBorder)
                            TextField("Year", text: $year)
                                .keyboardType(.numberPad)
                                .textFieldStyle(.roundedBorder)
                        }
                        
                        HStack(spacing: 8) {
                            TextField("Hour (0-23)", text: $hour)
                                .keyboardType(.numberPad)
                                .textFieldStyle(.roundedBorder)
                            TextField("Min (0-59)", text: $minute)
                                .keyboardType(.numberPad)
                                .textFieldStyle(.roundedBorder)
                        }
                        
                        TextField("City (e.g. Hyderabad, India)", text: $locationName)
                            .textFieldStyle(.roundedBorder)
                        
                        Button(action: calculateChart) {
                            HStack {
                                if isCalculating {
                                    ProgressView().tint(.white)
                                } else {
                                    Image(systemName: "sparkles")
                                    Text("Compute Birth Chart")
                                        .bold()
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(LinearGradient(colors: [.purple, .indigo], startPoint: .leading, endPoint: .trailing))
                            .foregroundColor(.white)
                            .cornerRadius(10)
                        }
                        .disabled(isCalculating)
                    }
                    .padding()
                    .background(Color.white.opacity(0.04))
                    .cornerRadius(14)
                    .padding(.horizontal)

                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                            .padding(.horizontal)
                    }

                    // Results Display
                    if let result = chartResult {
                        VStack(alignment: .leading, spacing: 16) {
                            Picker("View Mode", selection: $activeTab) {
                                Text("Interpretation").tag(0)
                                Text("Longitudes").tag(1)
                                Text("Dashas & Rules").tag(2)
                            }
                            .pickerStyle(.segmented)
                            .padding(.horizontal)

                            if activeTab == 0 {
                                // Interpretation Text & Follow-up Chat
                                VStack(alignment: .leading, spacing: 16) {
                                    Text(readingText.isEmpty ? "Calculating cosmic narration..." : readingText)
                                        .font(.subheadline)
                                        .foregroundColor(.white.opacity(0.9))
                                        .padding()
                                        .background(Color.purple.opacity(0.05))
                                        .cornerRadius(12)

                                    // Follow-up Chat Section
                                    VStack(alignment: .leading, spacing: 12) {
                                        Text("Ask Guruji — Follow-up Chat")
                                            .font(.caption.bold())
                                            .foregroundColor(.purple)
                                            .textCase(.uppercase)

                                        ForEach(chatMessages.indices, id: \.self) { idx in
                                            let msg = chatMessages[idx]
                                            HStack {
                                                if msg.role == "user" { Spacer() }
                                                Text(msg.content)
                                                    .font(.caption)
                                                    .padding(10)
                                                    .background(msg.role == "user" ? Color.purple : Color.white.opacity(0.1))
                                                    .foregroundColor(.white)
                                                    .cornerRadius(10)
                                                if msg.role == "assistant" { Spacer() }
                                            }
                                        }

                                        HStack {
                                            TextField("Ask a question about your chart...", text: $chatInput)
                                                .textFieldStyle(.roundedBorder)
                                            Button(action: sendChatMessage) {
                                                Image(systemName: "paperplane.fill")
                                                    .foregroundColor(.purple)
                                            }
                                            .disabled(chatInput.isEmpty || isStreamingChat)
                                        }
                                    }
                                    .padding()
                                    .background(Color.white.opacity(0.03))
                                    .cornerRadius(12)
                                }
                                .padding(.horizontal)

                            } else if activeTab == 1 {
                                // Planetary Longitudes Grid
                                VStack(alignment: .leading, spacing: 10) {
                                    Text("Lagna: \(result.chart.ascendant.sign) (\(String(format: "%.2f", result.chart.ascendant.degrees))°)")
                                        .font(.headline)
                                        .foregroundColor(.purple)

                                    ForEach(Array(result.chart.planets.keys.sorted()), id: \.self) { pName in
                                        if let pData = result.chart.planets[pName] {
                                            HStack {
                                                Text(pName).bold()
                                                if pData.isRetrograde {
                                                    Text("(R)").font(.caption).foregroundColor(.orange)
                                                }
                                                Spacer()
                                                Text("\(pData.sign) — \(String(format: "%.2f", pData.degrees))°")
                                                    .font(.footnote)
                                                    .foregroundColor(.gray)
                                                Text("House \(pData.house)")
                                                    .font(.caption.bold())
                                                    .padding(.horizontal, 6)
                                                    .padding(.vertical, 2)
                                                    .background(Color.purple.opacity(0.2))
                                                    .cornerRadius(4)
                                            }
                                            .padding(10)
                                            .background(Color.white.opacity(0.04))
                                            .cornerRadius(8)
                                        }
                                    }
                                }
                                .padding(.horizontal)

                            } else if activeTab == 2 {
                                // Dashas & Rules
                                VStack(alignment: .leading, spacing: 12) {
                                    Text("Vimshottari Dasha Periods")
                                        .font(.headline)
                                        .foregroundColor(.purple)

                                    ForEach(result.rules.dashas, id: \.lord) { dasha in
                                        HStack {
                                            Text("\(dasha.lord) Mahadasha").bold()
                                            Spacer()
                                            Text("\(dasha.start) – \(dasha.end)")
                                                .font(.caption)
                                                .foregroundColor(.gray)
                                        }
                                        .padding(10)
                                        .background(Color.white.opacity(0.04))
                                        .cornerRadius(8)
                                    }

                                    if !result.rules.yogas.isEmpty {
                                        Text("Detected Yogas")
                                            .font(.headline)
                                            .foregroundColor(.green)
                                            .padding(.top, 8)
                                        ForEach(result.rules.yogas, id: \.self) { yoga in
                                            Text("• \(yoga)")
                                                .font(.footnote)
                                                .foregroundColor(.green.opacity(0.9))
                                        }
                                    }
                                }
                                .padding(.horizontal)
                            }
                        }
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("Astrology Engine")
        }
    }

    private func calculateChart() {
        guard let y = Int(year), let m = Int(month), let d = Int(day),
              let h = Int(hour), let min = Int(minute) else {
            errorMessage = "Please enter valid numeric birth details."
            return
        }

        isCalculating = true
        errorMessage = nil
        
        Task {
            do {
                let req = AstrologyChartRequestV2(
                    year: y, month: m, day: d, hour: h, minute: min,
                    locationName: locationName, locationLat: lat, locationLon: lon,
                    locationTimezone: timezone, stream: false
                )
                let resp: ChartCalculationResponse = try await NetworkManager.shared.request(
                    path: "/astrology/chart/v2", method: "POST", body: req
                )
                chartResult = resp
                readingText = "Birth chart positions successfully calculated for \(locationName). Lagna in \(resp.chart.ascendant.sign)."
            } catch {
                errorMessage = "Calculation failed: \(error.localizedDescription)"
            }
            isCalculating = false
        }
    }

    private func sendChatMessage() {
        let text = chatInput
        chatInput = ""
        chatMessages.append((role: "user", content: text))
        isStreamingChat = true

        Task {
            // Simulate AI response stream
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            let aiReply = "Based on your \(chartResult?.chart.ascendant.sign ?? "Leo") Lagna placement, \(text) aligns with your active planetary period."
            chatMessages.append((role: "assistant", content: aiReply))
            isStreamingChat = false
        }
    }
}
