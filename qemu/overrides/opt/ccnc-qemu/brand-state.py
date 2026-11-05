#!/usr/bin/python3
"""Apply the emulator's saved brand before the original variant service starts."""
import json
from pathlib import Path

BRANDS = {"hyundai": "HYUNDAI", "kia": "KIA"}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=4) + "\n")
    temporary.replace(path)


def apply_brand(root, requested=None):
    """Only change the brand field; leave other software feature defaults intact."""
    state = root / "ccos/data/ccnc-qemu/brand.json"
    saved = json.loads(state.read_text())["brand"] if state.exists() else None
    brand = requested if requested is not None else saved
    if brand is None:
        return None  # An ordinary boot keeps the supplied firmware's coding.
    if brand not in BRANDS:
        raise ValueError("Unsupported ccNC brand: " + str(brand))
    path = root / "etc/sw_feature/sw_feature.json"
    config = json.loads(path.read_text())
    value = BRANDS[brand]
    changed = config["SW.CAR_BRAND"]["elected"] != value
    if changed:
        config["SW.CAR_BRAND"]["elected"] = value
        write_json(path, config)
    if changed or saved != brand:
        # The vendor service rebuilds its derived SW variant block when this
        # version marker is absent. Do not edit its binary variant partition.
        (root / "esp/variant_version").unlink(missing_ok=True)
    write_json(state, {"brand": brand})
    print("CCNC_BRAND_READY: " + value, flush=True)
    return value


def main():
    requested = None
    for argument in Path("/proc/cmdline").read_text().split():
        if argument.startswith("ccnc.brand="):
            requested = argument.split("=", 1)[1]
    apply_brand(Path("/"), requested)


if __name__ == "__main__":
    main()
