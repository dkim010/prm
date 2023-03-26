# Prepare
```bash
$ pip install psutil==5.9.4
```

# How to use
```bash
# monitor reousrce usage every 1 sec in 1 mininute
$ python prm.py -n slack
# monitor resource usage every 10 secs in 5 minutes
$ python prm.py -n slack -i 10 -d 5
# monitor resource usage every 10 secs in 5 minutes silently
$ python prm.py -n slack -i 10 -d 5 -s
```
- If `PermissionError: [Errno 13]` exception occurs, use `sudo`.
  - e.g., `sudo python prm.py ...`

- Command usage
```bash
$ python prm.py --help
usage: prm.py [-h] -n NAME [-i INTERVAL] [-d DURATION] [-o OUTPUT_PATH] [-s]

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Target process name (case insensitive) (default: None)
  -i INTERVAL, --interval INTERVAL
                        Collection interval (sec) (default: 1.0)
  -d DURATION, --duration DURATION
                        Total duration (min) (default: 1.0)
  -o OUTPUT_PATH, --output_path OUTPUT_PATH
                        The output CSV file path (default: 20230327_012916.csv)
  -s, --silent          No stdout (default: False)
```
