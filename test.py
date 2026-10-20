from pathlib import Path
import subprocess
import yaml


config_path = Path("configs/config_ci.yaml")


for case in sorted(Path("tests/bayesci_benchmark").glob("case_*")):
    with open(config_path) as f:
        config = yaml.safe_load(f)

        config["project"]["path"] = str(case.resolve())

        with open(config_path,"w") as f:
            yaml.safe_dump(config,f,sort_keys=False)

        print(f"\n============{case.name} ===========",flush=True)

        subprocess.run(["python3","main.py"])
