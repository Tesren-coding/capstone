# ============================================================
# state.py
# Operator and part tracking state
# ============================================================

from data import OPERATORS, OP_START_PART, SPECIAL_BOXES

def build_state(events, station_centers, box_centers, op_names):

    def get_start_center(op):
        from data import OP_SEQUENCES
        first_loc = OP_SEQUENCES[op][0]["loc"]
        if isinstance(first_loc, int):
            return list(station_centers[first_loc])
        elif first_loc in box_centers:
            return list(box_centers[first_loc])
        return [100, 100]

    op_positions       = {op: get_start_center(op) for op in op_names}
    op_targets         = {op: get_start_center(op) for op in op_names}
    op_event_index     = {op: 0 for op in op_names}
    op_has_part        = {op: OP_START_PART[op]    for op in op_names}
    op_dropoff_target  = {op: None for op in op_names}
    op_pending_dropoff = {op: None for op in op_names}

    op_events = {
        op: [e for e in events if e["operator"] == op]
        for op in op_names
    }

    op_cycle_length = {}
    for op in op_names:
        count = 0
        for e in op_events[op]:
            count += 1
            if e["status"] == "idle":
                break
        op_cycle_length[op] = count

    part_positions = {
        op: get_start_center(op) if OP_START_PART[op] else None
        for op in op_names
    }

    dropped_parts = {}

    counters = {
        "incoming": SPECIAL_BOXES["Incoming"]["start"],
        "packing":  0,
    }

    return {
        "op_positions":       op_positions,
        "op_targets":         op_targets,
        "op_event_index":     op_event_index,
        "op_has_part":        op_has_part,
        "op_dropoff_target":  op_dropoff_target,
        "op_pending_dropoff": op_pending_dropoff,
        "op_events":          op_events,
        "op_cycle_length":    op_cycle_length,
        "part_positions":     part_positions,
        "dropped_parts":      dropped_parts,
        "counters":           counters,
    }