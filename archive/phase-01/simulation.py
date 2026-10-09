import simpy

def run_simulation():
    env = simpy.Environment()
    events = []

    station_names = ["Inspect", "Repair", "Test"]
    cycle_times = {"Inspect": 5, "Repair": 12, "Test": 8}
    takt_time = 36

    def operator(env, name, events):
        while True:
            # record start of takt cycle
            takt_start = env.now

            # go through each station
            for station in station_names:
                events.append({
                    "time": env.now,
                    "operator": name,
                    "station": station,
                    "status": "working"
                })
                yield env.timeout(cycle_times[station])

            # calculate remaining time in takt cycle
            time_used = env.now - takt_start
            remaining = takt_time - time_used

            # wait for remaining takt time before next cycle
            if remaining > 0:
                events.append({
                    "time": env.now,
                    "operator": name,
                    "station": "Idle",
                    "status": "idle"
                })
                yield env.timeout(remaining)

    env.process(operator(env, "Op1", events))
    env.run(until=takt_time * 3)
    return events, takt_time