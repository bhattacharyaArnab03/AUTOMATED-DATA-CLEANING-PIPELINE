import yaml


class DomainRules:

    def __init__(self, config_path=None):
        self.rules = {}

        if config_path:
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    self.rules = config.get("domain_rules", {})
            except Exception:
                self.rules = {}

    def get_rule(self, column_name):
        return self.rules.get(column_name.lower())