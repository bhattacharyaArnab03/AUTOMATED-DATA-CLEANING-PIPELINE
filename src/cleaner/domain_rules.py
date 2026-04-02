class DomainRules:

    def __init__(self, config_path=None):
        self.missing_tokens = {"", "na", "null", "none", "no info"}

    def get_missing_tokens(self):
        return self.missing_tokens