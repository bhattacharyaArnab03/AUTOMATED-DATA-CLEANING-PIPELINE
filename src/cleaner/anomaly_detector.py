import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class EnsembleAnomalyDetector:
    def __init__(
        self,
        contamination=0.05,
        iqr_multiplier=1.5,
        mad_z_threshold=3.5,
        min_samples_iforest=20,
        vote_threshold=0.5,
        random_state=42,
    ):
        self.contamination = contamination
        self.iqr_multiplier = iqr_multiplier
        self.mad_z_threshold = mad_z_threshold
        self.min_samples_iforest = min_samples_iforest
        self.vote_threshold = vote_threshold
        self.random_state = random_state

    def _to_numeric(self, series):
        return pd.to_numeric(series, errors="coerce")

    def _iqr_flags(self, s: pd.Series):
        valid = s.dropna()
        if len(valid) < 4:
            return None

        q1 = valid.quantile(0.25)
        q3 = valid.quantile(0.75)
        iqr = q3 - q1

        if pd.isna(iqr) or iqr == 0:
            return pd.Series(False, index=s.index)

        lower = q1 - self.iqr_multiplier * iqr
        upper = q3 + self.iqr_multiplier * iqr

        return (s < lower) | (s > upper)

    def _mad_flags(self, s: pd.Series):
        valid = s.dropna()
        if len(valid) < 5:
            return None

        median = valid.median()
        mad = (valid - median).abs().median()

        if pd.isna(mad) or mad == 0:
            return pd.Series(False, index=s.index)

        modified_z = 0.6745 * (s - median) / mad
        return modified_z.abs() > self.mad_z_threshold

    def _iforest_flags(self, s: pd.Series):
        valid = s.dropna()
        if len(valid) < self.min_samples_iforest or valid.nunique() < 2:
            return None

        X = valid.values.reshape(-1, 1)
        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
        )

        preds = model.fit_predict(X)  # 1 normal, -1 anomaly
        mask = pd.Series(False, index=s.index)
        mask.loc[valid.index] = preds == -1
        return mask

    def detect(self, series):
        s = self._to_numeric(series)

        candidates = {
            "iqr": self._iqr_flags(s),
            "mad_z": self._mad_flags(s),
            "iforest": self._iforest_flags(s),
        }

        active = {name: mask for name, mask in candidates.items() if mask is not None}

        if not active:
            empty_mask = pd.Series(False, index=s.index)
            return {
                "mask": empty_mask,
                "scores": pd.Series(0.0, index=s.index),
                "count": 0,
                "rate": 0.0,
                "indices": [],
                "method_counts": {name: 0 for name in candidates},
                "active_methods": [],
            }

        aligned_masks = {}

        for name, mask in active.items():
            aligned = mask.reindex(s.index)

            aligned = aligned.fillna(False)

            aligned_masks[name] = aligned.astype(int)

        vote_frame = pd.DataFrame(aligned_masks)

        scores = vote_frame.mean(axis=1)
        anomaly_mask = scores >= self.vote_threshold

        return {
            "mask": anomaly_mask,
            "scores": scores,
            "count": int(anomaly_mask.sum()),
            "rate": float(anomaly_mask.mean()),
            "indices": anomaly_mask[anomaly_mask].index.tolist(),
            "method_counts": {
                name: int(mask.sum()) if mask is not None else 0
                for name, mask in candidates.items()
            },
            "active_methods": list(active.keys()),
        }