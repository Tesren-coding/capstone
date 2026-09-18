import simpy

def simple_process(env, name, process_time):
    print(f"{name} starts at time {env.now}")
    yield env.timeout(process_time)
    print(f"{name} finishes at time {env.now}")

env = simpy.Environment()

env.process(simple_process(env, "Unit 1", 5))
env.process(simple_process(env, "Unit 2", 3))

env.run()
