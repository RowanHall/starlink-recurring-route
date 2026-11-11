run following command in /data directory to sync w/ new data:

rclone copy R2ReadOnly:jasper-school-bus/pacheedaht ../pacheedaht/ --progress

run following command in given data ex 2026-mm-dd/:

docker command:

docker run --rm --mount type=bind,source=.,target=/data clarkzjw/leoviz:20260730 process identify /data
