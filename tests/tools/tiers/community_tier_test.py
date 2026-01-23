import ast


class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process(self):
        # [20260102_BUGFIX] Avoid arbitrary code execution during test processing.
        ast.literal_eval(self.data)
        return self.data.upper()


def run_processor(input_data):
    processor = DataProcessor(input_data)
    return processor.process()
