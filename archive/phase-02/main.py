from simulation import run_simulation
from visualization import run_visualization

events, takt_time = run_simulation()
run_visualization(events, takt_time)