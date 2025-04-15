#!/bin/bash

for (( year=2023; year>=2015; year-- ))
do
    echo "Running for year $year"
    start_date="${year}0101"
    end_date="${year}1231"
    ./run.sh "$start_date" "$end_date"
done