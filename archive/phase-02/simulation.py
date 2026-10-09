import simpy
from data import TAKT_TIME, STATIONS, OPERATORS, PART_FLOW

def run_simulation():
    env    = simpy.Environment()
    events = []

    def operator(env, name, station_ids):
        flow        = PART_FLOW[name]
        has_part    = flow["start_part"]
        first_cycle = True

        while True:
            takt_start = env.now

            for sid in station_ids:
                s_flow  = flow["stations"][sid]
                dropoff = s_flow.get("dropoff", None)
                pickup  = s_flow.get("pickup",  None)
                carry   = s_flow.get("carry",   True)

                # ---- PICKUP LOGIC ----
                if first_cycle:
                    # first cycle: part already at station
                    # only pick up if explicitly defined AND no part yet
                    if pickup and not has_part:
                        has_part = True
                        events.append({
                            "time":     env.now,
                            "operator": name,
                            "station":  sid,
                            "status":   "pickup",
                            "part":     True,
                            "from":     pickup,
                        })

                else:
                    # subsequent cycles
                    if name == "Op1" and sid == station_ids[0]:
                        # Op1 always picks from Incoming at start
                        has_part = True
                        events.append({
                            "time":     env.now,
                            "operator": name,
                            "station":  sid,
                            "status":   "pickup",
                            "part":     True,
                            "from":     "Incoming",
                        })

                    elif pickup and not has_part:
                        # any other defined pickup
                        has_part = True
                        events.append({
                            "time":     env.now,
                            "operator": name,
                            "station":  sid,
                            "status":   "pickup",
                            "part":     True,
                            "from":     pickup,
                        })

                # ---- WORKING EVENT ----
                events.append({
                    "time":     env.now,
                    "operator": name,
                    "station":  sid,
                    "status":   "working",
                    "part":     has_part,
                })

                yield env.timeout(STATIONS[sid]["cycle_time"])

                # ---- DROPOFF LOGIC ----
                if dropoff and has_part:
                    events.append({
                        "time":     env.now,
                        "operator": name,
                        "station":  sid,
                        "status":   "dropoff",
                        "part":     True,
                        "to":       dropoff,
                        "from_sid": sid,
                    })
                    has_part = False

                # if carry is False, operator leaves without part
                elif not carry and has_part:
                    has_part = False

            # end of cycle
            first_cycle = False

            # idle for remaining takt time
            time_used = env.now - takt_start
            remaining = TAKT_TIME - time_used

            if remaining > 0:
                events.append({
                    "time":     env.now,
                    "operator": name,
                    "station":  None,
                    "status":   "idle",
                    "part":     False,
                })
                yield env.timeout(remaining)

    for op_name, op_data in OPERATORS.items():
        env.process(operator(env, op_name, op_data["stations"]))

    env.run(until=TAKT_TIME * 100)
    return events, TAKT_TIME