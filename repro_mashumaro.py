from dataclasses import dataclass, field, fields
from typing import Any, Self

from mashumaro.mixins.dict import DataClassDictMixin

type BayesianOptions = dict[str, Any]


@dataclass(slots=True)
class EnvironmentConfig(DataClassDictMixin):
    temperature_sensor: str | None = None
    bayesian_options: BayesianOptions = field(default_factory=dict)

    @classmethod
    def _custom_from_dict(cls, data: dict[str, Any]) -> Self:
        known_keys = {f.name for f in fields(cls)}
        data = data.copy()
        extras = {k: v for k, v in data.items() if k not in known_keys}

        if extras:
            existing_opts = data.get("bayesian_options", {})
            if not isinstance(existing_opts, dict):
                existing_opts = {}
            existing_opts.update(extras)
            data["bayesian_options"] = existing_opts

            for k in extras:
                if k in data:
                    del data[k]  # Clean up for pure mashumaro consumption

        print(f"DEBUG: _custom_from_dict handling data: {data}")
        # Call the generated mashumaro deserializer
        return cls.__mashumaro_from_dict__(data)


# Monkey-patch to replace the generated from_dict
EnvironmentConfig.from_dict = EnvironmentConfig._custom_from_dict


data = {
    "temperature_sensor": "sensor.temp",
    "extra_option_1": "value1",
}
config = EnvironmentConfig.from_dict(data)
print(f"Config: {config}")
print(f"Bayesian Options: {config.bayesian_options}")
