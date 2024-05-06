from dataclasses import dataclass
import time
import statistics


@dataclass
class OccupancyRate:
    occupancy_rate: float
    time: float

# Simulated list of occupancy rates for demonstration
occupancy_rates = [
    OccupancyRate(0.45, time.time() - 20),
    OccupancyRate(0.48, time.time() - 15),
    OccupancyRate(0.51, time.time() - 10),
    OccupancyRate(0.43, time.time() - 5),
    OccupancyRate(0.45, time.time()),
    OccupancyRate(0.49, time.time() + 5),
    OccupancyRate(0.52, time.time() + 10),
    OccupancyRate(0.56, time.time() + 15),
    OccupancyRate(0.61, time.time() + 20)
]

def check_for_attack(occupancy_rates):
    if len(occupancy_rates) < 4:
        return False  # Not enough data to compare
    
    # Calculate the differences between consecutive occupancy rates
    differences = []
    # do that for previous 4 occupancy rates
    for i in range(len(occupancy_rates) - 5, len(occupancy_rates) - 1):
        rate_difference = occupancy_rates[i+1].occupancy_rate - occupancy_rates[i].occupancy_rate
        differences.append(rate_difference)
    print("differences: ")
    print(differences)
    # Check for consistent or increasing trend in differences
    last_diff = 0.0
    for diff in differences:
        # if occupancy rate increased and last occupancy rate and currents are close
        if (diff > 0.01 and (diff - last_diff < 0.015 or diff - last_diff > 0.015)):
            last_diff = diff  # No consistent increase
        else:
            return False
        
    # If we reached here, there is a consistent or increasing trend
    return True

# Example usage
attack_detected = check_for_attack(occupancy_rates)
print("Attack detected:", attack_detected)


@dataclass
class RemovedCount:
    removed_count: int
    time: float

# Example list of removed flow counts
removed_flow_counts = [
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(9, time.time() - 60),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(9, time.time() - 60),
    RemovedCount(5, time.time() - 40),
    RemovedCount(6, time.time() - 20),
    RemovedCount(5, time.time()),
    RemovedCount(4, time.time() + 20),
    RemovedCount(2, time.time() + 40),
]

# compare the last 4 removed flow counts in the switch's mean and the last 20 counts of the switch
def check_removed_flows(removed_flow_counts):
    
    # Calculate the mean and standard deviation of all recorded removed flow counts
    all_counts = [rc.removed_count for rc in removed_flow_counts]
    mean_count = statistics.mean(all_counts)
    st_dev = statistics.stdev(all_counts)
    print(mean_count)
    print(st_dev)

    # Assume not enough data to perform robust statistical analysis
    analysis_index = 20
    last_indices = 5
    compare_for_lately = False
    if len(removed_flow_counts) > analysis_index:
        compare_for_last_20 = True  


    # Extract the last 4 removed flow counts
    last_counts = [rc.removed_count for rc in removed_flow_counts[-last_indices:]]
    print(last_counts)

    # Check if all of last four are significantly below the mean and within one standard deviation
    if all(x < mean_count - st_dev for x in last_counts):
        if (compare_for_last_20):
            lately_counts = all_counts[-analysis_index:-last_indices]
            print(lately_counts)
            lately_mean_count = statistics.mean(lately_counts)
            lately_st_dev = statistics.stdev(lately_counts)
            print(lately_mean_count)
            print(lately_st_dev)
            if (all(x < lately_mean_count - lately_st_dev for x in last_counts)):
                return True
            else:
                return False
        else:
            return True  # The last four counts are significantly lower than typical values
    
    return False

# Example usage
attack_detected = check_removed_flows(removed_flow_counts)
print("Potential issue detected:", attack_detected)