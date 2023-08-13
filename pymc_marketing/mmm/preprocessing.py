from typing import Any, Callable, List, Tuple, Union

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MaxAbsScaler, StandardScaler

__all__ = [
    "preprocessing_method_X",
    "preprocessing_method_y",
    "MaxAbsScaleTarget",
    "MaxAbsScaleChannels",
    "StandardizeControls",
]


def preprocessing_method_X(method: Callable) -> Callable:
    if not hasattr(method, "_tags"):
        method._tags = {}  # type: ignore
    method._tags["preprocessing_X"] = True  # type: ignore
    return method


def preprocessing_method_y(method: Callable) -> Callable:
    if not hasattr(method, "_tags"):
        method._tags = {}  # type: ignore
    method._tags["preprocessing_y"] = True  # type: ignore
    return method





class MaxAbsScaleChannels:
    channel_columns: Union[List[str], Tuple[str]]

    @preprocessing_method_X
    def max_abs_scale_channel_data(self, data: pd.DataFrame) -> pd.DataFrame:
        channel_data: Union[
            pd.DataFrame,
            pd.Series[Any],
        ] = data[self.channel_columns]
        transformers = [("scaler", MaxAbsScaler())]
        pipeline: Pipeline = Pipeline(steps=transformers)
        self.channel_transformer: Pipeline = pipeline.fit(X=channel_data.to_numpy())
        data[self.channel_columns] = self.channel_transformer.transform(
            channel_data.to_numpy()
        )
        return data


class StandardizeControls:
    control_columns: List[str]  # TODO: Handle Optional[List[str]]

    @preprocessing_method_X
    def standardize_control_data(self, data: pd.DataFrame) -> pd.DataFrame:
        control_data: pd.DataFrame = data[self.control_columns]
        transformers = [("scaler", StandardScaler())]
        pipeline: Pipeline = Pipeline(steps=transformers)
        self.control_transformer: Pipeline = pipeline.fit(X=control_data.to_numpy())
        data[self.control_columns] = self.control_transformer.transform(
            control_data.to_numpy()
        )
        return data
