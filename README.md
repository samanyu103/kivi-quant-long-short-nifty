## Run code
```
./run.sh
```
To test on out-of-sample data update config. I removed the first line of NIFTY 50_minute_data which is "NIFTY 50_minute_data" so that the first line is the header/ column names

Parameter : "update minutes" is the time after which indicators are updated. To pass it as a command line argument, update ./run.sh (add the $1)
```
python3 Code/main.py "$1"
```
and then run using
```
./run.sh 60
```
To run for time gaps in [15, 20... 60] run ./run_loop.sh :
```
./run_loop.sh
```
To run for all years modify run.sh (add "$1" and "$2") as follows:
```
python3 Code/main.py "$1" "$2"
```
and then run 
```
./run_years.sh
```
Finally for plotting the pnls of 2020. I used
```
python3 analysis_2020.py
```
