#!/bin/bash
# headless Ghidra on the ManxTT project (copy of SonicR srrun.sh). usage: mxrun.sh <abs log> <args...>
log="$1"; shift
cd /c/Users/john/Documents/ManxTT/ghidra || exit 1
cmd //c "C:\Users\john\Documents\Tools\ghidra-headless.bat C:\Users\john\Documents\ManxTT\ghidra ManxTT $* -scriptPath ${SP:-C:\Users\john\Documents\ManxTT\ghidra\scripts}" < /dev/null > "$log" 2>&1
tail -2 "$log"
