echo "checking value.txt"
grep -qx good value.txt || { echo "FAIL: value is not good"; exit 1; }
