import SwiftUI

/// Native SwiftUI Kundli Chart Wheel Renderer
struct KundliChartView: View {
    let ascendantSign: String
    let ascendantIndex: Int
    let planets: [String: PlanetPlacementInfo]
    var style: ChartStyle = .north
    
    enum ChartStyle {
        case north
        case south
    }

    struct PlanetPlacementInfo {
        let symbol: String
        let name: String
        let house: Int
        let degrees: Double
    }

    var body: some View {
        VStack(spacing: 12) {
            ZStack {
                // Background Outer Glow
                RoundedRectangle(cornerRadius: 24)
                    .fill(Color(red: 0.05, green: 0.05, blue: 0.08))
                    .overlay(
                        RoundedRectangle(cornerRadius: 24)
                            .stroke(Color.indigo.opacity(0.3), lineWidth: 1.5)
                    )
                    .shadow(color: Color.indigo.opacity(0.15), radius: 12, x: 0, y: 4)

                if style == .north {
                    NorthIndianChartCanvas(ascendantIndex: ascendantIndex, planets: planets)
                } else {
                    SouthIndianChartCanvas(ascendantIndex: ascendantIndex, planets: planets)
                }
            }
            .aspectRatio(1.0, contentMode: .fit)
            .padding(.horizontal)

            // Planet Chips Legend
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(planets.keys.sorted(), id: \.self) { planetKey in
                        if let info = planets[planetKey] {
                            HStack(spacing: 4) {
                                Text(info.symbol)
                                    .font(.caption.bold())
                                    .foregroundColor(.indigo)
                                Text("H\(info.house)")
                                    .font(.caption2.monospaced())
                                    .foregroundColor(.secondary)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.white.opacity(0.05))
                            .cornerRadius(8)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
                            )
                        }
                    }
                }
                .padding(.horizontal)
            }
        }
    }
}

/// North Indian Diamond Grid Canvas Component
struct NorthIndianChartCanvas: View {
    let ascendantIndex: Int
    let planets: [String: KundliChartView.PlanetPlacementInfo]

    var body: some View {
        Canvas { context, size in
            let w = size.width
            let h = size.height

            var gridPath = Path()
            // Outer Square
            gridPath.addRect(CGRect(x: 10, y: 10, width: w - 20, height: h - 20))
            
            // Diagonals (X)
            gridPath.move(to: CGPoint(x: 10, y: 10))
            gridPath.addLine(to: CGPoint(x: w - 10, y: h - 10))
            gridPath.move(to: CGPoint(x: w - 10, y: 10))
            gridPath.addLine(to: CGPoint(x: 10, y: h - 10))

            // Inner Diamond
            gridPath.move(to: CGPoint(x: w / 2, y: 10))
            gridPath.addLine(to: CGPoint(x: w - 10, y: h / 2))
            gridPath.addLine(to: CGPoint(x: w / 2, y: h - 10))
            gridPath.addLine(to: CGPoint(x: 10, y: h / 2))
            gridPath.closeSubpath()

            context.stroke(gridPath, with: .color(Color.indigo.opacity(0.5)), lineWidth: 1.5)

            // Draw House 1 (Top Center Diamond) Label
            let lagnaSignNum = ascendantIndex + 1
            let text = Text("\(lagnaSignNum)")
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(Color.amber)
            
            context.draw(text, at: CGPoint(x: w / 2, y: h * 0.3))
        }
    }
}

/// South Indian Box Grid Canvas Component
struct SouthIndianChartCanvas: View {
    let ascendantIndex: Int
    let planets: [String: KundliChartView.PlanetPlacementInfo]

    var body: some View {
        Canvas { context, size in
            let w = size.width
            let h = size.height

            var gridPath = Path()
            // Outer Square
            gridPath.addRect(CGRect(x: 10, y: 10, width: w - 20, height: h - 20))

            // 3x3 Internal Grid Lines
            let cellW = (w - 20) / 4
            let cellH = (h - 20) / 4

            for i in 1...3 {
                let x = 10 + cellW * CGFloat(i)
                gridPath.move(to: CGPoint(x: x, y: 10))
                gridPath.addLine(to: CGPoint(x: x, y: h - 10))

                let y = 10 + cellH * CGFloat(i)
                gridPath.move(to: CGPoint(x: 10, y: y))
                gridPath.addLine(to: CGPoint(x: w - 10, y: y))
            }

            context.stroke(gridPath, with: .color(Color.indigo.opacity(0.4)), lineWidth: 1.5)
        }
    }
}

extension Color {
    static let amber = Color(red: 0.96, green: 0.62, blue: 0.22)
}
