from scenario_store import ScenarioStore
from balancing_schema import validate_plan


class BalancingStore(ScenarioStore):
    def __init__(self, directory):
        super().__init__(directory, normalizer=validate_plan)

    def load(self, name):
        result = super().load(name)
        result['plan'] = result.pop('scenario')
        return result
