import langgraph as lg


class HiveReaderConfig:
    def __init__(self):
        self.model = "gpt-4o-mini"
        self.prompt = """
        Y
        """

class HiveReader:
    def __init__(self):
        self.model = lg.Model(model="gpt-4o-mini")

    def read(self, text):
        return self.model.invoke(text)
