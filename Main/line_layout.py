"""C-shaped station geometry, shared contract with the browser preview."""
LEFT = 80
PITCH = 330
TOP = 220
BOTTOM = 620
WIDTH = 150
HEIGHT = 96


def break_count(ids, after_id=None):
    if len(ids) < 2: return len(ids)
    if after_id in ids[:-1]: return ids.index(after_id)+1
    return (len(ids)+1)//2


def c_layout(ids, after_id=None):
    count = break_count(ids, after_id)
    positions = {}
    for index, sid in enumerate(ids):
        positions[sid] = {'x': LEFT+(count-1-index)*PITCH if index<count else LEFT+(index-count)*PITCH,
                          'y': TOP if index<count else BOTTOM, 'w': WIDTH, 'h': HEIGHT}
    input_box = {'x': LEFT+max(1,count)*PITCH, 'y': TOP, 'w': WIDTH, 'h': HEIGHT}
    output_box = {'x': LEFT+max(1,len(ids)-count)*PITCH, 'y': BOTTOM, 'w': WIDTH, 'h': HEIGHT}
    return {'shape': 'c', 'positions': positions, 'input': input_box, 'output': output_box,
            'break_after_id': ids[count-1] if count else None, 'top_count': count,
            'width': max(input_box['x'],output_box['x'])+WIDTH+80, 'height': BOTTOM+HEIGHT+80}
