# ============================================================
# simulation.py
# SimPy simulation — accepts config from Flask
# ============================================================

import simpy
import data as default_data

def run_simulation(config=None):

    # use config values if provided, else use defaults
    TAKT_TIME  = int(config["takt_time"]) \
                 if config else default_data.TAKT_TIME

    STATIONS   = {}
    for sid, s_data in default_data.STATIONS.items():
        ct = s_data["cycle_time"]
        if config and str(sid) in config.get("cycle_times", {}):
            ct = int(config["cycle_times"][str(sid)])
        STATIONS[sid] = {**s_data, "cycle_time": ct}

    OP_SEQUENCES  = default_data.OP_SEQUENCES
    OP_START_PART = default_data.OP_START_PART

    env    = simpy.Environment()
    events = []

    def operator(env, name):
        sequence    = OP_SEQUENCES[name]
        has_part    = OP_START_PART[name]
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

    for op_name in default_data.OPERATORS.keys():
        env.process(operator(env, op_name))

    env.run(until=TAKT_TIME * 100)
    return events, TAKT_TIME