"""Export a team statistics payload to the existing Streamlit data folder."""
import argparse
import json
from pathlib import Path

from tax_pricing.team_market import adapt_team_reference


def export_snapshot(input_path: Path, output_dir: Path) -> Path:
    """Validate and save one observed reference for the configured UI loader.

    Parameters
    ----------
    input_path : pathlib.Path
        JSON containing reference, per_network_brl and source.
    output_dir : pathlib.Path
        Dedicated export folder; not the original price dataset.

    Returns
    -------
    pathlib.Path
        Generated exact-SKU JSON, consumed via TAX_PRICING_MARKET_DIR.
    """
    payload = json.loads(input_path.read_text())
    snapshot = adapt_team_reference(
        payload['reference'], payload['per_network_brl'],
        source=payload['source'])
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{snapshot['ean']}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    return path


def main() -> None:
    """Export an explicit team input without contacting the RTC service."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(export_snapshot(args.input, args.output_dir))


if __name__ == '__main__':
    main()
