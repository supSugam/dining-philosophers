import os
import time
import random
from celery import Celery
from celery.signals import worker_ready

REDIS_HOST = "redis"
app = Celery('philosopher.tasks', broker=f'redis://{REDIS_HOST}:6379/0', backend=f'redis://{REDIS_HOST}:6379/0')

PHILOSOPHER_ID = int(os.environ.get('PHILOSOPHER_ID', 1))
app.conf.task_routes = {
    f'philosopher.tasks.dine_{PHILOSOPHER_ID}': {'queue': f'philosopher{PHILOSOPHER_ID}'}
}

NUM_PHILOSOPHERS = 5

def get_forks(philosopher_id):
    """Get the left and right fork numbers for a philosopher"""
    return (philosopher_id % NUM_PHILOSOPHERS), ((philosopher_id + 1) % NUM_PHILOSOPHERS)

@app.task(name=f'philosopher.tasks.dine_{PHILOSOPHER_ID}')
def dine():
    left_fork, right_fork = get_forks(PHILOSOPHER_ID)
    
    while True:
        # Think for a while
        thinking_time = random.uniform(1, 3)
        print(f"Philosopher {PHILOSOPHER_ID} is thinking for {thinking_time:.1f} seconds")
        time.sleep(thinking_time)
        
        # Try to acquire forks
        print(f"Philosopher {PHILOSOPHER_ID} is trying to acquire forks {left_fork} and {right_fork}")
        
        redis = app.backend.client
        
        acquired = False
        while not acquired:
            # Try to acquire left fork
            if redis.setnx(f'fork_{left_fork}', PHILOSOPHER_ID):
                # Try to acquire right fork
                if redis.setnx(f'fork_{right_fork}', PHILOSOPHER_ID):
                    acquired = True
                else:
                    # Releasing left fork as the philospher couldn't acquire right one
                    redis.delete(f'fork_{left_fork}')
                    time.sleep(random.uniform(0.1, 0.5))  # Random backoff
            time.sleep(random.uniform(0.1, 0.5))  # Random backoff
        
        # Eating
        eating_time = random.uniform(1, 3)
        print(f"Philosopher {PHILOSOPHER_ID} is eating for {eating_time:.1f} seconds")
        time.sleep(eating_time)
        
        # Deleting forks ie. releasing them
        redis.delete(f'fork_{left_fork}')
        redis.delete(f'fork_{right_fork}')
        print(f"Philosopher {PHILOSOPHER_ID} has finished eating and released the forks")

@worker_ready.connect
def at_start():
    dine.delay()

if __name__ == '__main__':
    app.start()