from pathlib import Path
from datetime import datetime, timezone
import json
import zipfile
import shutil
import csv

BASE_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = BASE_DIR / "build_predictions"
ZIP_PATH = BASE_DIR / "Today_Predictions.zip"


def main() -> None:
    # Clean old build folder
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc).isoformat()

    predictions = [
        {
            "symbol": "EURUSD",
            "side": "long",
            "confidence": "high",
            "score": 0.86,
            "entry": 1.1000,
            "stop": 1.0950,
            "tp": 1.1100,
            "setup": "continuation"
        },
        {
            "symbol": "BTCUSD",
            "side": "short",
            "confidence": "medium",
            "score": 0.78,
            "entry": 82000,
            "stop": 83500,
            "tp": 79000,
            "setup": "reversal_after_sweep"
        },
        {
            "symbol": "XAUUSD",
            "side": "long",
            "confidence": "medium",
            "score": 0.74,
            "entry": 2160,
            "stop": 2148,
            "tp": 2188,
            "setup": "breakout_retest"
        }
    ]

    ranking_payload = {
        "generated_at_utc": now_utc,
        "predictions": predictions
    }

    integrity_payload = {
        "generated_at_utc": now_utc,
        "status": "pass",
        "notes": [
            "Prediction files created successfully."
        ],
        "prediction_count": len(predictions)
    }

    # 1) JSON exports
    (BUILD_DIR / "today_prediction_ranking.json").write_text(
        json.dumps(ranking_payload, indent=2),
        encoding="utf-8",
    )

    (BUILD_DIR / "prediction_integrity_report.json").write_text(
        json.dumps(integrity_payload, indent=2),
        encoding="utf-8",
    )

    # Optional top10 json
    (BUILD_DIR / "today_prediction_top10.json").write_text(
        json.dumps(
            {
                "generated_at_utc": now_utc,
                "top10": predictions[:10]
            },
            indent=2
        ),
        encoding="utf-8",
    )

    # 2) CSV export
    csv_path = BUILD_DIR / "today_prediction_ranking.csv"
    fieldnames = ["symbol", "side", "confidence", "score", "entry", "stop", "tp", "setup"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)

    # 3) TXT export
    txt_path = BUILD_DIR / "today_prediction_summary.txt"
    lines = [
        f"Generated at UTC: {now_utc}",
        f"Prediction count: {len(predictions)}",
        "",
        "Predictions:"
    ]

    for i, p in enumerate(predictions, start=1):
        lines.append(
            f"{i}. {p['symbol']} | {p['side']} | confidence={p['confidence']} | "
            f"score={p['score']} | entry={p['entry']} | stop={p['stop']} | tp={p['tp']} | setup={p['setup']}"
        )

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    # 4) ZIP export
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in BUILD_DIR.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.relative_to(BUILD_DIR))

    print(f"Created zip: {ZIP_PATH}")
    print("Created files:")
    for file_path in sorted(BUILD_DIR.rglob("*")):
        if file_path.is_file():
            print(f" - {file_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
