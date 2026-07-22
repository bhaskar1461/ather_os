import asyncio
import json
from app.astrology.guna_milan import calculate_guna_milan
from app.astrology.calculator import calculate_chart_data
from app.astrology.rules import evaluate_chart_rules

async def main():
    print("=== Testing Guna Milan calculations ===")
    score, breakdown = calculate_guna_milan(
        groom_nak_idx=0, groom_sign_idx=0,
        bride_nak_idx=1, bride_sign_idx=0
    )
    print(f"Total points: {score}/36")
    print(f"Breakdown: {json.dumps(breakdown, indent=2)}")

    print("\n=== Testing Transit Relative Placement calculations ===")
    natal = calculate_chart_data(1990, 5, 15, 10, 30, 19.076, 72.877, 5.5)
    transit = calculate_chart_data(2026, 7, 6, 22, 0, 19.076, 72.877, 5.5)

    natal_lagna = natal["ascendant"]["longitude"]
    print(f"Natal Lagna: {natal['ascendant']['sign']} at {natal_lagna:.2f}°")

    for name, p_data in transit["planets"].items():
        diff = (p_data["longitude"] - natal_lagna) % 360.0
        house = int(diff // 30.0) + 1
        print(f"Transit {name.capitalize()} in sign {p_data['sign']} -> lands in Natal House {house}")

if __name__ == "__main__":
    asyncio.run(main())
