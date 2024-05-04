from apscheduler.schedulers.background import BackgroundScheduler
import time

# Define a class with a method to be scheduled
class StatScheduler:

    def start_scheduler(self, task):
        # Create a background scheduler
        self.scheduler = BackgroundScheduler()
        
        # Schedule my_task to run every 5 seconds
        self.scheduler.add_job(task, 'interval', seconds=5)
        
        # Start the scheduler
        self.scheduler.start()

    def stop_scheduler(self):
        # Shut down the scheduler
        self.scheduler.shutdown(wait=True)


# Usage example
cron = StatScheduler()  # Create an instance of the class
cron.start_scheduler()  # Start the scheduler

# Keep the script running to see the scheduled tasks
