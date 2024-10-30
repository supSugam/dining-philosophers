import os
import time
import random
from celery import Celery
from celery.signals import worker_ready

app = Celery('philosopher.tasks', broker=f'amqp://guest:guest@rabbitmq:5672//',backend=f'redis://redis:6379/0')

PHILOSOPHER_ID = int(os.environ.get('PHILOSOPHER_ID', 1))
app.conf.task_routes = {
    f'philosopher.tasks.dine_{PHILOSOPHER_ID}': {'queue': f'philosopher{PHILOSOPHER_ID}'}
}

NUM_PHILOSOPHERS = 5

def get_forks(philosopher_id):
    return (philosopher_id % NUM_PHILOSOPHERS), ((philosopher_id + 1) % NUM_PHILOSOPHERS)

def acquire_fork(fork_id):
    return app.backend.client.setnx(f'fork_{fork_id}', PHILOSOPHER_ID)

def release_fork(fork_id):
    """Release a fork"""
    app.backend.client.delete(f'fork_{fork_id}')

@app.task(name=f'philosopher.tasks.dine_{PHILOSOPHER_ID}')
def start_dining():
    left_fork, right_fork = get_forks(PHILOSOPHER_ID)
    
    while True:
        thinking_time = random.uniform(1, 3)
        print(f"Philosopher {PHILOSOPHER_ID} is thinking for {thinking_time:.1f} seconds")
        time.sleep(thinking_time)
        
        # Try to acquire forks
        print(f"Philosopher {PHILOSOPHER_ID} is trying to acquire forks {left_fork} and {right_fork}")
        
        acquired = False
        while not acquired:
            if acquire_fork(left_fork):
                if acquire_fork(right_fork):
                    acquired = True
                else:
                    print(f"Philosopher {PHILOSOPHER_ID} couldn't acquire right fork {right_fork}")
                    release_fork(left_fork) 
                    time.sleep(random.uniform(0.1, 0.5)) 
            else:
                print(f"Philosopher {PHILOSOPHER_ID} couldn't acquire left fork {left_fork}")
            time.sleep(random.uniform(0.1, 0.5)) 
        
        # Eating
        eating_time = random.uniform(1, 3)
        print(f"Philosopher {PHILOSOPHER_ID} is eating for {eating_time:.1f} seconds")
        time.sleep(eating_time)
        
        release_fork(left_fork)
        release_fork(right_fork)
        print(f"Philosopher {PHILOSOPHER_ID} has finished eating and released the forks")

@worker_ready.connect
def at_start(sender, **kwargs):
    start_dining.delay()

if __name__ == '__main__':
    print(PHILOSOPHER_ID,"Philosopher ID")
    app.start()