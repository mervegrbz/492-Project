import pandas as pd
from scipy.stats import zscore
def feature_extractor(flow):
  duration = flow['duration_sec']
  packet = flow['packet_count']
  byte = flow['byte_count']
  pps = packet / duration if duration > 0 else 0
  bps = byte / duration if duration > 0 else 0
  bpp = byte / packet if packet > 0 else 0 
  interarrival_time = duration / packet if packet > 0 else 0 
  return {'cookie': flow['cookie'], 'duration': duration, 'packet': packet, 'byte': byte, 'pps': pps, 
          'bps': bps, 'bpp': bpp, 'interarrival_time': interarrival_time}
  

def create_groups(df):
    # Create the necessary groupings
    df['ip_proto'] = df['ip_proto'].astype(str)
    df['ipv4_src-ipv4_dst'] = df[ 'ipv4_src'] + '-' + df['ipv4_dst']
    df['ipv4_src-ip_proto'] = df['ipv4_src'] + '-' + df['ip_proto']
    groupings = ['ipv4_src', 'ipv4_dst', 'ipv4_src-ipv4_dst', 'ipv4_src-ip_proto']
    aggregated_data = {}

    for group in groupings:
        aggregated_data[group] = df.groupby(group).size().reset_index(name='count-{}'.format(group))
    
    return aggregated_data, df

## this statistics calculates the z score of the flows in terms of ['ipv4_src', 'ipv4_dst', 'ipv4_src-ipv4_dst', 'ipv4_src-ip_proto']
## if z score is exceeded then the flow is marked as malicious

def get_flow_rule_statistics(flow_table):
    data, df = create_groups(flow_table)
    
    for key in data.keys():
        data[key]['z_score-{}'.format(key)] = zscore(data[key]['count-{}'.format(key)])
        df = pd.merge(df, data[key], on=key, how='left')
    return df

def ml_flow(flow_table):
    if ( len(flow_table )<=0):
        return   
    ## get the flow_features for each flow
    flow_features = flow_table.apply(lambda x: feature_extractor(x), axis=1)
    print(flow_table)
    print(type(flow_features))
    
    ## flow features are in the form of dictionary, convert it to dataframe
    flow_features = pd.DataFrame(flow_features.tolist())
    print(flow_features)
    ## get flow_statistics
    flow_statistics = get_flow_rule_statistics(flow_table)
    ml_flow = pd.merge(flow_features, flow_statistics, on='cookie', how='left')
    ml_flow = ml_flow.drop(['ipv4_src', 'ipv4_dst', 'ipv4_src-ipv4_dst', 'ipv4_src-ip_proto', 'count-ipv4_src', 'count-ipv4_dst', 'count-ipv4_src-ipv4_dst', 'count-ipv4_src-ip_proto'], axis=1)
    ## create new dataframe with columns 'cookie', 'duration', 'packet_count', 'byte_count', 'pps', 'bps', 'bpp', 'interarrival_time', 'z_score- ipv4_src', 'z_score- ipv4_dst', 'z_score-ipv4_src-ipv4_dst', 'z_score-ipv4_src-ip_proto', 'label', 
    flow_features['label'] = 0
    return ml_flow
    

   
    
    