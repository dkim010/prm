# pylint:disable=invalid-name
from __future__ import annotations

import argparse
from pathlib import Path
from pprint import pprint

import polars as pl
import pymysql

def string_to_bytes(size_str: str) -> int:
    if not size_str:
        return 0
    sizer = {
        'G': 1024*1024*1024,
        'M': 1024*1024,
        'K': 1024,
    }
    return int(size_str[:-1]) * sizer[size_str[-1]]


class Ingester:
    def __init__(
            self,
            log_file: Path,
            version: str,
            exp_name: str,
            log_name: str,
            mysql_host: str,
            mysql_port: int,
            mysql_user: str,
            mysql_database: str,
            mysql_table: str,
    ):
        self.log_file = log_file
        self.version = version
        self.exp_name = exp_name
        self.log_name = log_name
        # mysql
        self.mysql_host = mysql_host
        self.mysql_port = mysql_port
        self.mysql_user = mysql_user
        self.mysql_database = mysql_database
        self.mysql_table = mysql_table
        self.uri = f'mysql+pymysql://{mysql_user}@{mysql_host}:{mysql_port}/{mysql_database}'

    def _generate_dataframe(self) -> pl.DataFrame:
        df = pl.read_csv(self.log_file)
        df = df.select(
            pl.col('stamp').str.to_datetime('%Y-%m-%d %H:%M:%S')
                .dt.epoch(time_unit='ms').alias('time'),
            pl.lit(self.version).alias('version'),
            pl.lit(self.exp_name).alias('exp_name'),
            pl.lit(str(self.log_file)).alias('log_file'),
            pl.lit(self.log_name).alias('log_name'),
            pl.col('pid'),
            pl.col('name'),
            pl.col('cpu_percent'),
            pl.col('average_cpu_percent'),
            pl.col('mem_usage').map_elements(string_to_bytes, pl.Int64).alias('mem_usage'),
        )
        min_time = df['time'].min()
        df = df.with_columns(pl.col('time') - min_time)
        return df

    def _prepare(self):
        conn = pymysql.connect(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
        )
        cursor = conn.cursor()
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS {self.mysql_database}')
        cursor.close()
        conn.close()

    def _ingest_to_database(self, df: pl.DataFrame):
        df.write_database(
            connection=self.uri,
            table_name=self.mysql_table,
            if_table_exists='append',
        )

    def start(self):
        self._prepare()
        df = self._generate_dataframe()
        print(df)
        self._ingest_to_database(df)


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-f', '--log_file', type=Path, required=True,
                        help='Log file path (CSV)')
    parser.add_argument('-l', '--log_name', type=str, required=True,
                        help='Log name')
    parser.add_argument('-n', '--exp_name', type=str, required=True,
                        help='Experiment name')
    parser.add_argument('-V', '--version', type=str, required=True,
                        help='Version')
    parser.add_argument('-H', '--mysql_host', type=str, default='localhost')
    parser.add_argument('-p', '--mysql_port', type=int, default=3306)
    parser.add_argument('-u', '--mysql_user', type=str, default='root')
    parser.add_argument('-d', '--mysql_database', type=str, default='log_db')
    parser.add_argument('-t', '--mysql_table', type=str, default='log_table')

    args = parser.parse_args()
    pprint(args.__dict__)
    ingester = Ingester(**args.__dict__)
    ingester.start()


if __name__ == '__main__':
    main()
