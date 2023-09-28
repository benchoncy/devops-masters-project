# System metrics

import psutil
import cpuinfo


kb = float(1024)
mb = float(kb ** 2)
gb = float(kb ** 3)


class ComponentInfo:
    """Base class for component information and metrics."""
    class Data:
        pass

    def data(self):
        return self.Data()


class CPU(ComponentInfo):
    """CPU information and metrics."""

    def __init__(self):
        self.cpu_info = cpuinfo.get_cpu_info()['brand_raw']
        self.cpu_count = psutil.cpu_count()

    class Data:
        def __init__(self):
            self.cpu_percent = psutil.cpu_percent(interval=1)
            self.avg_load_1_percent, \
                self.avg_load_5_percent, \
                self.avg_load_15_percent  \
                = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]

    def __str__(self):
        data = self.data()
        return f"""
        ------ CPU Info: ------\n
        Brand: {self.cpu_info}\n
        Cores: {self.cpu_count}\n
        CPU Percent: {data.cpu_percent}%\n
        Avg Load 1: {data.avg_load_1_percent}%\n
        Avg Load 5: {data.avg_load_5_percent}%\n
        Avg Load 15: {data.avg_load_15_percent}%\n
        """


class Memory(ComponentInfo):
    """Memory information and metrics."""

    def __init__(self):
        self.total_memory = psutil.virtual_memory().total / gb

    class Data:
        def __init__(self):
            memory = psutil.virtual_memory()
            self.available = memory.available / gb
            self.percent = memory.percent
            self.used = memory.used / gb
            self.free = memory.free / gb

    def __str__(self):
        data = self.data()
        return f"""
        ------ Memory Info: ------\n
        Total Memory: {self.total_memory} GB\n
        Available Memory: {data.available} GB\n
        Percent Memory: {data.percent}%\n
        Used Memory: {data.used} GB\n
        Free Memory: {data.free} GB\n
        """

class Disk(ComponentInfo):
    """Disk information and metrics."""

    def __init__(self):
        self.disk_size = psutil.disk_usage('/').total / gb

    class Data:
        def __init__(self):
            disk = psutil.disk_usage('/')
            self.used = disk.used / gb
            self.free = disk.free / gb
            self.percent = disk.percent
            io = psutil.disk_io_counters()
            self.read_bytes = io.read_bytes / mb
            self.write_bytes = io.write_bytes / mb
            self.iops = io.read_count + io.write_count

    def __str__(self):
        data = self.data()
        return f"""
        ------ Disk Info: ------\n
        Disk Size: {self.disk_size} GB\n
        Used Disk: {data.used} GB\n
        Free Disk: {data.free} GB\n
        Percent Disk: {data.percent}%\n
        Read Bytes: {data.read_bytes} MB\n
        Write Bytes: {data.write_bytes} MB\n
        IOPS: {data.iops} IO/s\n
        """


class Network(ComponentInfo):
    """Network information and metrics."""
    class Data:
        def __init__(self):
            net_io = psutil.net_io_counters()
            self.bytes_sent = net_io.bytes_sent / mb
            self.bytes_recv = net_io.bytes_recv / mb
            self.iops = net_io.packets_sent + net_io.packets_recv

    def __str__(self):
        data = self.data()
        return f"""
        ------ Network Info: ------\n
        Bytes Sent: {data.bytes_sent} MB\n
        Bytes Recv: {data.bytes_recv} MB\n
        IOPS: {data.iops} IO/s\n
        """


class SystemInfo:
    def __init__(self):
        self.cpu = CPU()
        self.memory = Memory()
        self.disk = Disk()
        self.network = Network()

    def __str__(self):
        return f'{self.cpu}\n{self.memory}\n{self.disk}\n{self.network}\n'


if __name__ == '__main__':
    sys_info = SystemInfo()
    print(sys_info)
