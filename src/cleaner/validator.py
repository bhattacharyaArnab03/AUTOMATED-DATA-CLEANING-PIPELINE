import pandas as pd


class Validator:

    def validate_numeric(self, s):
        s = pd.to_numeric(s, errors="coerce")

        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        return s.clip(lower, upper), lower, upper