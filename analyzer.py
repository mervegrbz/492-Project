import re
import pandas as pd
import json
# read logs. txt file
clear_logs = []
def read_logs():
  log_arr = []
  with open('logs.txt', 'r') as file:
      # each line in the file is a dictionary, create a array of dict from the file
      for line in file:
          # split string with , 
          line = line.split(',')
          # create a dictionary from the string
          log = {}
          for item in line:
              item = re.sub('[\(\)\{\}\'\"<>]', '', item)
              item.strip()
              elems = item.split(':')          
              key,value = None, None
              key = elems[0]
              # print(key)
              if len(elems) < 2:
                  value = None
              elif len(elems) > 2:
                key = elems[0]
                value = ':'.join(elems[1:])
              else:
                key = elems[0]
                value = elems[1]

              if 'match' in key:
                continue

              log[key] = value

          log_arr.append(log)
  log_df = pd.DataFrame(log_arr)

  log_df.to_csv('your_dataframe.csv', index=False)
  return log_df


read_logs()