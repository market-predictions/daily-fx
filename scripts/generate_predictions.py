from pathlib import Path
from datetime import datetime, timezone
import json
import zipfile
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = BASE_DIR / "build_predictions"
ZIP_PATH = BASE_DIR / "Today_Predictions.zip"


def main() -> None:
    # clean old build folder
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # sample files - replace later with your real prediction generator
    ranking_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "predictions": [
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
    }

    integrity_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "notes": [
            "Sample integrity file created successfully."
        ]
    }

    (BUILD_DIR / "today_prediction_ranking.json").write_text(
        json.dumps(ranking_payload, indent=2),
        encoding="utf-8",
    )

    (BUILD_DIR / "prediction_integrity_report.json").write_text(
        json.dumps(integrity_payload, indent=2),
        encoding="utf-8",
    )

    # rebuild zip
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in BUILD_DIR.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.relative_to(BUILD_DIR))

    print(f"Created zip: {ZIP_PATH}")
    print("Contents:")
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        for name in zf.namelist():
            print(f" - {name}")


if __name__ == "__main__":
    main()
