from metaflow import FlowSpec, step, resources, pypi


class ExperimentFlow(FlowSpec):

    @pypi(python='3.10.11', packages={'psutil': '5.9.8'})
    @resources(cpu=2, memory=8000)
    @step
    def start(self):
        import psutil
        print("CPU count: ", psutil.cpu_count())
        print("Memory: ", psutil.virtual_memory())
        self.next(self.end)

    @step
    def end(self):
        print("End of the flow")


if __name__ == "__main__":
    ExperimentFlow()
