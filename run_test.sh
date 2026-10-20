
cd "$(dirname "$0")" || exit 1

CONFIG = "configs/config_ci.yaml"

for dir in tests/bayesci_benchmark/case_*/;do
	[ -d "$dir/.git" ] || continue

	echo "========== $(basename "$dir") =========="


	sed -i "s|^	path:.*|	path: \$(realpath "$dir")\"|"	"$CONFIG"
	python3 main.py

	echo
done
