# ============================================================
# scenario_simulation.py
# Phase 9 — Builder-driven simulation engine
# Validates a user-built scenario, then runs it in SimPy.
# Fails fast: any broken rule raises immediately with details.
# ============================================================

import simpy


class ScenarioValidationError(Exception):
    """Raised when a scenario fails one or more validation rules."""
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Scenario validation failed:\n" + "\n".join(errors))


class ScenarioRuntimeError(Exception):
    """Raised when the simulation itself hits an unrecoverable state
    (e.g. picking from an empty IN box, exceeding OUT capacity)."""
    pass


# ============================================================
# VALIDATION
# ============================================================
def validate_scenario(scenario):
    errors = []

    takt_time  = scenario.get("takt_time")
    stations   = scenario.get("stations", {})
    operators  = scenario.get("operators", {})
    boxes      = scenario.get("boxes", {})

    # ---- 1. takt_time ----
    if not isinstance(takt_time, int) or takt_time <= 0:
        errors.append("takt_time must be a positive integer.")

    # ---- 2. at least 1 station and 1 operator ----
    if len(stations) == 0:
        errors.append("Scenario must contain at least one station.")
    if len(operators) == 0:
        errors.append("Scenario must contain at least one operator.")

    all_loc_ids = set(stations.keys()) | set(boxes.keys())

    # ---- 8. station cycle_time ----
    for sid, s in stations.items():
        ct = s.get("cycle_time")
        if not isinstance(ct, int) or ct <= 0:
            errors.append(f"Station {sid} ('{s.get('name', sid)}') has invalid cycle_time: {ct}")

    # ---- 9/10. box value sanity ----
    for bid, b in boxes.items():
        btype = b.get("type")
        if btype == "in":
            sc = b.get("start_count")
            if not isinstance(sc, int) or sc < 0:
                errors.append(f"IN box {bid} has invalid start_count: {sc}")
        elif btype == "out":
            cap = b.get("capacity")
            if not isinstance(cap, int) or cap <= 0:
                errors.append(f"OUT box {bid} has invalid capacity: {cap}")

    # ---- 3/4/5/6/7/11/12. operator sequence rules ----
    for op_name, op in operators.items():
        sequence = op.get("sequence", [])

        if len(sequence) == 0:
            errors.append(f"Operator '{op_name}' has an empty sequence.")
            continue

        holding_part = False
        first_pick_seen = False

        for i, step in enumerate(sequence):
            action = step.get("action")
            loc    = step.get("loc")

            # ---- 4. loc must be filled ----
            if loc is None or loc == "":
                errors.append(f"Operator '{op_name}' step {i+1}: no location selected.")
                continue

            # ---- 5. loc must exist ----
            if loc not in all_loc_ids:
                errors.append(f"Operator '{op_name}' step {i+1}: location '{loc}' does not exist.")
                continue

            # ---- 6. work must target a station ----
            if action == "work" and loc not in stations:
                errors.append(f"Operator '{op_name}' step {i+1}: 'work' action must target a station, not box '{loc}'.")

            # ---- 7. pick/drop must target station or box (always true given all_loc_ids check) ----

            # ---- 11/12. pick/drop ordering sanity ----
            if action == "pick":
                if holding_part:
                    errors.append(f"Operator '{op_name}' step {i+1}: cannot 'pick' — already holding a part (missing 'drop').")
                else:
                    # is this the very first pick, and does it rely on has_part being true?
                    if not first_pick_seen:
                        first_pick_seen = True
                        target = stations.get(loc) or boxes.get(loc)
                        starts_with_part = bool(target.get("has_part")) if target else False
                        # Rule 11: fine either way — if starts_with_part is True, operator
                        # is assumed to already be holding it (handled at runtime).
                    holding_part = True

            elif action == "drop":
                if not holding_part:
                    errors.append(f"Operator '{op_name}' step {i+1}: cannot 'drop' — not holding a part (missing 'pick').")
                else:
                    holding_part = False

    if errors:
        raise ScenarioValidationError(errors)


# ============================================================
# SIMULATION (Option B — live flow-controlled)
# ============================================================
def run_scenario_simulation(scenario):
    """
    Validates the scenario, then runs it through SimPy.
    Fails fast at runtime if:
      - an operator tries to 'pick' from an empty IN box
      - an operator tries to 'drop' into an OUT box that is already at capacity
    """
    validate_scenario(scenario)

    takt_time  = scenario["takt_time"]
    stations   = scenario["stations"]
    operators  = scenario["operators"]
    boxes      = scenario["boxes"]

    env    = simpy.Environment()
    events = []

    # ---- live state ----
    station_has_part = {sid: bool(s.get("has_part", False)) for sid, s in stations.items()}
    box_state = {}
    for bid, b in boxes.items():
        if b["type"] == "swip":
            box_state[bid] = {"has_part": bool(b.get("has_part", False))}
        elif b["type"] == "in":
            box_state[bid] = {"remaining": b.get("start_count", 0)}
        elif b["type"] == "out":
            box_state[bid] = {"count": 0, "capacity": b.get("capacity", 1)}

    def loc_has_part(loc):
        if loc in stations:
            return station_has_part.get(loc, False)
        b = box_state.get(loc)
        if b is None:
            return False
        if "has_part" in b:
            return b["has_part"]
        if "remaining" in b:
            return b["remaining"] > 0
        if "count" in b:
            return True  # OUT box always has "a part" conceptually once dropped
        return False

    def take_part_from(loc):
        """Remove a part from the location's live state (pick)."""
        if loc in stations:
            station_has_part[loc] = False
        else:
            b = box_state[loc]
            if "has_part" in b:
                b["has_part"] = False
            elif "remaining" in b:
                if b["remaining"] <= 0:
                    raise ScenarioRuntimeError(
                        f"IN box '{loc}' is empty — cannot pick a part (time={env.now})."
                    )
                b["remaining"] -= 1

    def deposit_part_to(loc):
        """Add a part to the location's live state (drop)."""
        if loc in stations:
            station_has_part[loc] = True
        else:
            b = box_state[loc]
            if "has_part" in b:
                b["has_part"] = True
            elif "count" in b:
                if b["count"] >= b["capacity"]:
                    raise ScenarioRuntimeError(
                        f"OUT box '{loc}' is at capacity ({b['capacity']}) — cannot drop part (time={env.now})."
                    )
                b["count"] += 1
            elif "remaining" in b:
                # dropping into an IN box doesn't really make sense, but handle gracefully
                b["remaining"] += 1

    def operator_process(env, op_name, op_data):
        sequence = op_data["sequence"]
        has_part = False

        # first pick may be pre-loaded if target already has_part == True
        first_cycle = True

        while True:
            takt_start = env.now

            for step in sequence:
                loc    = step["loc"]
                action = step["action"]

                if action == "pick":
                    if first_cycle and loc_has_part(loc) and not has_part:
                        # operator "starts" already holding this part (pre-loaded)
                        take_part_from(loc)
                        has_part = True
                    else:
                        take_part_from(loc)
                        has_part = True

                    events.append({
                        "time": env.now, "operator": op_name, "loc": loc,
                        "status": "pickup", "part": True, "from": loc,
                    })
                    events.append({
                        "time": env.now, "operator": op_name, "loc": loc,
                        "status": "moving", "part": has_part,
                    })

                elif action == "drop":
                    if has_part:
                        deposit_part_to(loc)
                        events.append({
                            "time": env.now, "operator": op_name, "loc": loc,
                            "status": "dropoff", "part": True, "to": loc,
                        })
                        has_part = False
                    events.append({
                        "time": env.now, "operator": op_name, "loc": loc,
                        "status": "moving", "part": has_part,
                    })

                elif action == "work":
                    events.append({
                        "time": env.now, "operator": op_name, "loc": loc,
                        "status": "working", "part": has_part,
                    })
                    yield env.timeout(stations[loc]["cycle_time"])

            first_cycle = False

            time_used = env.now - takt_start
            remaining = takt_time - time_used

            if remaining > 0:
                events.append({
                    "time": env.now, "operator": op_name, "loc": None,
                    "status": "idle", "part": False,
                })
                yield env.timeout(remaining)

    for op_name, op_data in operators.items():
        env.process(operator_process(env, op_name, op_data))

    env.run(until=takt_time * 100)

    return events, takt_time