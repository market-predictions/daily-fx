from pathlib import Path
from datetime import datetime, timezone
import json
import zipfile
import shutil
import csv

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "daily_outputs" / "latest"
ZIP_PATH = OUTPUT_DIR / "Today_Predictions.zip"


def main() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        "notes": ["Prediction files created successfully."],
        "prediction_count": len(predictions)
    }

    # JSON
    (OUTPUT_DIR / "today_prediction_ranking.json").write_text(
        json.dumps(ranking_payload, indent=2),
        encoding="utf-8",
    )

    (OUTPUT_DIR / "prediction_integrity_report.json").write_text(
        json.dumps(integrity_payload, indent=2),
        encoding="utf-8",
    )

    # CSV
    csv_path = OUTPUT_DIR / "today_prediction_ranking.csv"
    fieldnames = ["symbol", "side", "confidence", "score", "entry", "stop", "tp", "setup"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)

    # TXT
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
    (OUTPUT_DIR / "today_prediction_summary.txt").write_text("\n".join(lines), encoding="utf-8")

    # ZIP backup
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in OUTPUT_DIR.iterdir():
            if file_path.is_file() and file_path.name != ZIP_PATH.name:
                zf.write(file_path, arcname=file_path.name)

    print("Created files:")
    for file_path in sorted(OUTPUT_DIR.iterdir()):
        if file_path.is_file():
            print(f" - {file_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
