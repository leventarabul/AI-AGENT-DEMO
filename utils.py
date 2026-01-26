
import logging

def process_data(items):
    logging.info("Processing started")
    results = []
    for item in items:
        if item is not None:
            results.append(item.upper())
    return results
