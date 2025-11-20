import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def timed_function(func):
    """
    A decorator to measure and log the execution time of a function.
    """
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logging.info(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds.")
        return result
    return wrapper

# @timed_function
# def my_sample_function(duration):
#     """
#     A sample function to demonstrate time logging.
#     """
#     logging.info(f"Executing my_sample_function for {duration} seconds...")
#     time.sleep(duration)
#     logging.info("my_sample_function finished.")
#     return "Task Completed"
