import pandas as pd

# Load the CSV files

#train_data
flow_table_1_bad = pd.read_csv('data/flow_table_1_bad.csv')
flow_table_1 = pd.read_csv('data/flow_table_1.csv')
flow_table_2_bad = pd.read_csv('data/flow_table_2_bad.csv')
flow_table_2 = pd.read_csv('data/flow_table_2.csv')

#test_data
flow_table_3_bad = pd.read_csv('data/flow_table_3_bad.csv')
flow_table_3 = pd.read_csv('data/flow_table_3.csv')

flow_table_4_bad = pd.read_csv('data/flow_table_4_bad.csv')
flow_table_4 = pd.read_csv('data/flow_table_4.csv')

# Add 'is_attack' column with appropriate values
flow_table_1_bad['is_attack'] = 1
flow_table_1['is_attack'] = 0
flow_table_2_bad['is_attack'] = 1
flow_table_2['is_attack'] = 0

flow_table_3_bad['is_attack'] = 1
flow_table_3['is_attack'] = 0

flow_table_4_bad['is_attack'] = 1
flow_table_4['is_attack'] = 0


# Combine all dataframes into one
combined_flow_table = pd.concat([flow_table_1_bad, flow_table_1, flow_table_2_bad, flow_table_2], ignore_index=True)
combined_flow_table_test = pd.concat([flow_table_3, flow_table_3_bad], ignore_index=True)
combined_flow_table_test_2 = pd.concat([flow_table_4, flow_table_4_bad], ignore_index=True)
combined_all = pd.concat([flow_table_1_bad, flow_table_1, flow_table_2_bad, flow_table_2, flow_table_3_bad, flow_table_3, flow_table_4_bad, flow_table_4], ignore_index=True)


# Save the combined dataframe to a new CSV file
combined_csv_path = 'data/train_flow_table.csv'
combined_flow_table.to_csv(combined_csv_path, index=False)

combined_csv_path_test = 'data/test_flow_table.csv'
combined_flow_table_test.to_csv(combined_csv_path_test, index=False)

combined_csv_path_test_2 = 'data/test_flow_table_2.csv'
combined_flow_table_test_2.to_csv(combined_csv_path_test_2, index=False)

combined_all_path = 'data/combined_all.csv'
combined_all.to_csv(combined_all_path, index=False)

combined_flow_table.head()
combined_flow_table_test.head()
combined_flow_table_test_2.head()
combined_all.head()
