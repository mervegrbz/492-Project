import pandas as pd
from sklearn.model_selection import train_test_split




# Load the CSV files by dropping index
def load_csv_data(file_path):
    df = pd.read_csv(file_path, index_col=False)
    # Drop any unnamed columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

# concating two flow tables
def combine_flow_tables(flow_table_1, flow_table_2):
    return pd.concat([flow_table_1, flow_table_2], ignore_index=True)

# labeling them when storing
def store_flow_table(flow_table, stored_path, is_attack):
    flow_table['is_attack'] = is_attack
    flow_table.to_csv(stored_path, index=False)
    flow_table.head()

# with no label
def store_flow_table(flow_table, stored_path):
    flow_table.to_csv(stored_path, index=False)
    flow_table.head()

# creating test set from training data
def create_test_set(train_data, new_train_path, test_path):
    # Split the data into training and test sets
    train_set, test_set = train_test_split(train_data, test_size=0.2, random_state=42)
    # Save the test set to a CSV file
    test_set.to_csv(test_path, index=False)
    # Optionally, save the new training set to a CSV file
    train_set.to_csv(new_train_path, index=False)

# shuffling the table
def shuffle_table(stored_path):
    flow_table = load_csv_data(stored_path)
    flow_table_shuffled = flow_table.sample(frac=1, random_state=42).reset_index(drop=True)
    # flow_table_shuffled['is_attack'] = is_attack
    flow_table_shuffled.to_csv(stored_path, index=False)

# drop column from data
def drop_col(col, path):
    flows = load_csv_data(path)
    flow_new = flows.drop(columns=[col])
    store_flow_table(flow_new, path)



""" Combine 2 flows
#shuffle_table('train_data/train_data_combined_3.csv')
drop_col('match','train_data/train_data_new3.csv')

f_1 = load_csv_data('train_data/train_data_atak.csv')
f_2 = load_csv_data('train_data/train_data_combined.csv')
c_all = combine_flow_tables(f_1, f_2)

store_flow_table(c_all, 'train_data/train_data_combined_2.csv', 1)
"""

""" Combine 4 flows
f_1 = load_csv_data('data/full-health/flow_table_1.csv')
f_2 = load_csv_data('data/full-health/flow_table_2.csv')
f_3 = load_csv_data('data/full-health/flow_table_3.csv')
f_4 = load_csv_data('data/full-health/flow_table_4.csv')

c_1 = combine_flow_tables(f_1, f_3)
c_2 = combine_flow_tables(f_2, f_4)
c_all = combine_flow_tables(c_1, c_2)

store_flow_table(c_all, 'train_data/train_data_new2.csv', 0)
"""

""" Test Set
train_data = load_csv_data('train_data/train_data_combined_3.csv')
new_train_path = 'train_data/train_test_1.csv' #test set from train
test_path = 'test_data/test_train_1.csv' #test set from train
create_test_set(train_data, new_train_path, test_path)
"""

"""
f_1 = load_csv_data('train_data/train_data_new3.csv')
f_2 = load_csv_data('train_data/train_data_combined_2.csv')
c_1 = combine_flow_tables(f_1, f_2)
store_flow_table(c_1, 'train_data/train_data_combined_3.csv')
"""


"""

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
"""