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
  ip_src_zscore = zscore(flow_table['ipv4_src'])
  ip_dst_zscore = zscore(flow_table['ipv4_dst'])
  ip_proto_zscore = zscore(flow_table['ip_proto'])
  ip_src_dst_zscore = zscore(flow_table['ipv4_src-ipv4_dst'])


# removed flowlar ve gelen flowlari ayri ayri mi incelemeliyim
# bir flow geldigi zaman gelis saati elimde var 
# flowların saglıklı olup olmadıgını anlamam gerekıyor
# flowları swıtchlerden bagımsız dusunmek mantıklı mı
# ıkı cesıt flowum var bırı her bılgısıne sahıp oldugum flowlar dıgerı ıse sadece flow table da bulunan her seyını bılmedıgım flowlar
# removed flowları bır csv ye kaydetıp onları labellayabılırım
# removed flowları kullanarak bır model olusturabılırım 
# flow tabledaki flowları removed flowlarla kıyaslayabılırım 
# bunu yapmak ıcın stat almam gerekir
# ılk yapmam gereken sey elımdekı flow table ın entropısını ıncelemek
