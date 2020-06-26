# Standard Library
import os
import time
from datetime import datetime

# Third Party
import boto3

# First Party
from smdebug.profiler.algorithm_metrics_reader import S3AlgorithmMetricsReader
from smdebug.profiler.system_metrics_reader import S3SystemMetricsReader

MICROS = 1e6


def convert_us_since_epoch_to_datetime(us_since_epoch):
    secs = us_since_epoch / MICROS
    dt = datetime.fromtimestamp(secs)
    return dt


def us_since_epoch_to_human_readable_time(us_since_epoch):
    dt = convert_us_since_epoch_to_datetime(us_since_epoch)
    s = dt.strftime("%Y-%m-%dT%H:%M:%S")
    s += "." + str(int(us_since_epoch % MICROS)).zfill(6)
    return s


class TrainingJob:
    def __init__(self, training_job_name, region=None):
        self.name = training_job_name
        self.profiler_config = None
        self.profiler_s3_output_path = None
        if region is None:
            self.sm_client = boto3.client("sagemaker")
        else:
            self.sm_client = boto3.client("sagemaker", region_name=region)
        self.profiler_config, self.profiler_s3_output_path = (
            self.get_config_and_profiler_s3_output_path()
        )
        self.system_metrics_reader = None
        self.framework_metrics_reader = None

    def get_systems_metrics_reader(self):
        return self.system_metrics_reader

    def get_framework_metrics_reader(self):
        return self.framework_metrics_reader

    def get_sm_client(self):
        return self.sm_client

    def get_config_and_profiler_s3_output_path(self):
        if self.profiler_config is None:

            self.ds = self.get_sm_client().describe_training_job(TrainingJobName=self.name)
            attempt = 0
            while attempt < 60:
                if "ProfilerConfig" in self.ds:
                    pc = self.ds["ProfilerConfig"]
                    if "S3OutputPath" in pc:
                        self.profiler_config = pc
                        self.profiler_s3_output_path = os.path.join(
                            pc["S3OutputPath"], self.name, "profiler-output"
                        )
                        break
                    attempt += 1
            print(f"ProfilerConfig:{self.profiler_config}")
            print(f"s3 path:{self.profiler_s3_output_path}")
        return self.profiler_config, self.profiler_s3_output_path

    def wait_for_sys_profiling_data_to_be_available(self):
        self.system_metrics_reader = S3SystemMetricsReader(self.profiler_s3_output_path)
        last_job_status = ""
        last_secondary_status = ""
        while self.system_metrics_reader.get_timestamp_of_latest_available_file() == 0:
            self.system_metrics_reader.refresh_event_file_list()
            print("Profiler data from system not available yet")
            p = self.describe_training_job()

            if "TrainingJobStatus" in p:
                status = p["TrainingJobStatus"]
            if "SecondaryStatus" in p:
                secondary_status = p["SecondaryStatus"]
            if last_job_status != status or last_secondary_status != secondary_status:
                print(
                    f"time: {time.time()} TrainingJobStatus:{status} TrainingJobSecondaryStatus:{secondary_status}"
                )
                last_job_status = status
                last_secondary_status = secondary_status
            time.sleep(10)

        print("\n\nProfiler data from system is available")

    def wait_for_framework_profiling_data_to_be_available(self):
        self.framework_metrics_reader = S3AlgorithmMetricsReader(self.profiler_s3_output_path)

        events = []
        while (
            self.framework_metrics_reader.get_timestamp_of_latest_available_file() == 0
            or len(events) == 0
        ):
            self.framework_metrics_reader.refresh_event_file_list()
            last_timestamp = self.framework_metrics_reader.get_timestamp_of_latest_available_file()
            events = self.framework_metrics_reader.get_events(0, last_timestamp)
            print("Profiler data from framework not available yet")
            time.sleep(10)

        print("\n\n Profiler data from framework is available")
        print(
            f"Found {len(events)}, recorded framework annotations. Latest available timestamp microsseconds_since_epoch is:{last_timestamp} , human_readable_timestamp in utc:",
            us_since_epoch_to_human_readable_time(last_timestamp),
        )

    def describe_training_job(self):
        return self.get_sm_client().describe_training_job(TrainingJobName=self.name)
