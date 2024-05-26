import pandas as pd
from scipy.stats import zscore
def feature_extractor(flow, flow_table):
  duration = flow['duration_sec']
  packet = flow['packet_count']
  byte = flow['byte_count']
  pps = packet / duration
  bps = byte / duration
  bpp = byte / packet
  interarrival_time = duration / packet
  return {'duration': duration, 'packet': packet, 'byte': byte, 'pps': pps, 
          'bps': bps, 'bpp': bpp, 'interarrival_time': interarrival_time}
  

def create_groups(df):
    # Create the necessary groupings
    df[' ip_proto'] = df[' ip_proto'].astype(str)
    df['ipv4_src-ipv4_dst'] = df[ ' ipv4_src'] + '-' + df[' ipv4_dst']
    df['ipv4_src-ip_proto'] = df[' ipv4_src'] + '-' + df[' ip_proto']
    groupings = [' ipv4_src', ' ipv4_dst', 'ipv4_src-ipv4_dst', 'ipv4_src-ip_proto']
    aggregated_data = {}

    for group in groupings:
        aggregated_data[group] = df.groupby(group).size().reset_index(name='count-{}'.format(group))
    
    return aggregated_data, df

## this statistics calculates the z score of the flows in terms of ['ipv4_src', 'ipv4_dst', 'ipv4_src-ipv4_dst', 'ipv4_src-ip_proto']
## if z score is exceeded then the flow is marked as malicious

def get_flow_rule_statistics(flow_table):
    data, df = create_groups(flow_table)
    
    for key in data.keys():
        print(key)
        data[key]['z_score-{}'.format(key)] = zscore(data[key]['count-{}'.format(key)])
        df = pd.merge(df, data[key], on=key, how='left')
    return df