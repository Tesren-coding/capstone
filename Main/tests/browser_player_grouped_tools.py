"""Validate the video controls and builder tool grouping structurally."""
from pathlib import Path
from bs4 import BeautifulSoup
root=Path(__file__).resolve().parents[1]
sim=BeautifulSoup((root/'templates/simulate.html').read_text(),'html.parser')
builder=BeautifulSoup((root/'templates/builder.html').read_text(),'html.parser')
canvas=sim.select_one('#sim-canvas')
timeline=sim.select_one('#timeline')
player=sim.select_one('.simulation-video-controls')
assert canvas and timeline and player
assert canvas.find_parent(class_='simulation-canvas-and-timeline') == timeline.find_parent(class_='simulation-canvas-and-timeline')
assert player.find_parent(class_='simulation-playback-timeline')
for id_ in ('start-btn','stop-btn','restart-btn','speed-dial','speed-label'):
    assert player.select_one('#'+id_),id_
assert builder.select_one('#line-tool-panel #toolbar')
assert builder.select_one('#line-tool-handle strong').get_text(strip=True)=='Line Tool'
for name, selector in [('Line Settings','line-settings-heading'),('Scenario Files','scenario-files-heading')]:
    assert builder.select_one('#'+selector).get_text(strip=True)==name
assert builder.select_one('#builder-under-canvas #line-settings-heading')
# Run Simulation belongs in the combined Line Settings row, not its own heading.
assert builder.select_one('#builder-under-canvas #run-scenario-btn')
assert builder.select_one('#import-scenario-btn').has_attr('hidden')
for id_ in ('new-line-btn','save-scenario-btn','load-scenario-btn','run-scenario-btn','choose-local-folder-btn','dimension-tool-btn','reorder-operators-btn'):
    assert len(builder.select('#'+id_))==1,id_
print('Playback controls and dockable Line Tool verified; control IDs preserved.')
