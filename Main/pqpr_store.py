"""PQPR storage reuses the version-safe JSON/revision engine used by scenarios."""
from scenario_store import ScenarioStore
from pqpr_schema import validate_pqpr


class PQPRStore(ScenarioStore):
    def __init__(self, directory):
        super().__init__(directory, normalizer=validate_pqpr)

    def load(self, name):
        result = super().load(name)
        result['project'] = result.pop('scenario')
        return result
