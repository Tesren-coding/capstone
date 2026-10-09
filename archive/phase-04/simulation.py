# ============================================================
# simulation.py
# SimPy simulation logic
# ============================================================

import simpy
from data import TAKT_TIME, STATIONS, OPERATORS, OP_SEQUENCES, OP_START_PART

def run_simulation():
    env    = simpy.Environment()
    events = []

    def operator(env, name):
        sequence  = OP_SEQUENCES[name]
        has_part  = OP_START_PART[name]
        first_cycle = True

        while True:
            takt_start = env.now

            for step in sequence:
                loc    = step["loc"]
                action = step["action"]

                # ---- PICK ----
                if action == "pick":
                    if not first_cycle or not has_part:
                        has_part = True
                        events.append({
                            "time":     env.now,
                            "operator": name,
                            "loc":      loc,
                            "status":   "pickup",
                            "part":     True,
                            "from":     loc,
                        })
                    # move to location
                    events.append({
                        "time":     env.now,
                        "operator": name,
                        "loc":      loc,
                        "status":   "moving",
                        "part":     has_part,
                    })

                # ---- DROP ----
                elif action == "drop":
                    if has_part:
                        events.append({
                            "time":     env.now,
                            "operator": name,
                            "loc":      loc,
                            "status":   "dropoff",
                            "part":     True,
                            "to":       loc,
                        })
                        has_part = False
                    events.append({
                        "time":     env.now,
                        "operator": name,
                        "loc":      loc,
                        "status":   "moving",
                        "part":     has_part,
                    })

                # ---- WORK ----
                elif action == "work":
                    events.append({
                        "time":     env.now,
                        "operator": name,
                        "loc":      loc,
                        "status":   "working",
                        "part":     has_part,
                    })
                    yield env.timeout(STATIONS[loc]["cycle_time"])

            first_cycle = False

            # idle for remaining takt time
            time_used = env.now - takt_start
            remaining = TAKT_TIME - time_used

            if remaining > 0:
                events.append({
                    "time":     env.now,
                    "operator": name,
                    "loc":      None,
                    "status":   "idle",
                    "part":     False,
                })
                yield env.timeout(remaining)

    for op_name in OPERATORS.keys():
        env.process(operator(env, op_name))

    env.run(until=TAKT_TIME * 100)
    return events, TAKT_TIME