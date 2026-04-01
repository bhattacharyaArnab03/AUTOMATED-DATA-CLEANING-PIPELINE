import re

PATTERNS = {
    "email": r'^[\w\.-]+@[\w\.-]+\.\w+$',
    "phone": r'^\+?\d{10,13}$',
    "zipcode": r'^\d{5,6}$',
    "numeric_string": r'^\d+$'
}

def detect_pattern(series):
    values = series.dropna().astype(str).head(100)

    if len(values) == 0:
        return "unknown"

    pattern_counts = {key: 0 for key in PATTERNS}

    for val in values:
        for name, pattern in PATTERNS.items():
            if re.match(pattern, val):
                pattern_counts[name] += 1

    best_pattern = max(pattern_counts, key=pattern_counts.get)

    if pattern_counts[best_pattern] / len(values) > 0.7:
        return best_pattern

    return "mixed"