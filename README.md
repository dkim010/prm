# Prepare
```bash
$ pip install psutil==5.9.4
```

# How to use
```bash
$ python prm.py -n slack
```

- Command usage
```bash
$ python prm.py --help
usage: prm.py [-h] -n NAME [-i INTERVAL] [-d DURATION] [-o OUTPUT_PATH] [-s]

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Target process name (default: None)
  -i INTERVAL, --interval INTERVAL
                        Collection interval (sec) (default: 1.0)
  -d DURATION, --duration DURATION
                        Total duration (min) (default: 1.0)
  -o OUTPUT_PATH, --output_path OUTPUT_PATH
                        The output CSV file path (default: 20230327_012350.csv)
  -s, --silent          No stdout (default: False)
```
