import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, mean_squared_error
# import xgboost as xgb
from enum import Enum
import pickle

class ML_Model(Enum):
    KNN = 1
    RANDOM_FOREST = 2
    SVM = 3
    XGBOOST = 4

def preprocessing_batches(data):
    # Drop non-numeric columns
    # if is_attack column exists in the data_test, drop it
    label_train = data['is_attack']
    data = data.drop(columns=['timestamp', 'flow_table_stats', 'removed_table_stats', 'flow_table_stats_durations', 'removed_table_stats_durations', 'is_attack'])
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data)
    return data_train, label_train


def preprocessing_stats(train, test):
    # Preprocessing
    data_train = train.drop(columns=['is_attack'])
    label_train = train['is_attack']
    
    feature_names = data_train.columns

    data_test = test.drop(columns=['is_attack'])
    label_test = test['is_attack']

    # Standardizing the data
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data_train)
    data_test = scaler.transform(data_test)

    return data_train, data_test, label_train, label_test, feature_names


def get_model(model_type, test_data, is_batch):
    model = None
    model_filename = ""
    if (is_batch):
        model_filename = f"history_batches_ml_models/{model_type.name.lower()}_model.pkl"
    else:
        model_filename = f"flow_rules_ml_models/{model_type.name.lower()}_model.pkl"
    # Check if the model file exists, if not, train and save the model
    try:
        with open(model_filename, 'rb') as file:
            model = pickle.load(file)
        print(f"Loaded {model_type.name} model from {model_filename}")
        # TODO call it if it is labeled
        ## if is_attack column exists in the data_test, drop it
        return model
        #data_test = StandardScaler().transform(data_test)
    # if file does not exists, train the model and save it under the ml_models folder
    except FileNotFoundError:
        if model_type == ML_Model.KNN:
            model = KNeighborsClassifier(n_neighbors=5)
        elif model_type == ML_Model.RANDOM_FOREST:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
        elif model_type == ML_Model.SVM:
            model = SVC(kernel='linear', random_state=42)

        train_path = 'train_data/train_test_1.csv'
        train_data = pd.read_csv(train_path)
        data_train, label_train = None, None
        if (is_batch):
            #data_train, data_test_2, label_train, feature_names = preprocessing_batches_no_label(train_data, data_test)
            data_train, data_test, label_train, label_test, feature_names = preprocessing_batches(train_data, test_data)
        else:
            #TODO call the commented one if your data has no label
            # data_train, data_test, label_train, feature_names = preprocessing_stats_no_label(train_data, data_test)
            data_train, data_test, label_train, label_test, feature_names = preprocessing_stats(train_data, test_data)

        model.fit(data_train, label_train)
        print('model hazir')
        with open(model_filename, 'wb') as file:
            pickle.dump(model, file)
        print(f"Saved {model_type.name} model to {model_filename}")
        return model
    



def predict_test_data_individually(model, test_data, test_label, feature_names):
    predictions = []
    test_data_df = pd.DataFrame(test_data, columns=feature_names)
    for index, row in test_data_df.iterrows():
        # Reshape the row to match the model's expected input shape
        
        row_data = row.values.reshape(1, -1)
        # Predict the result for the current entry
        prediction = model.predict(row_data)
        # Append the prediction to the list
        predictions.append(prediction[0])
        print(prediction, index, prediction[0],  test_label[index])

    # Add predictions to the test data
    print("LABEL")
    print(test_label)
    print("TEK TEK")
    print(predictions)
    
    return predictions



# Example usage
train_path = 'train_data/train_test_1.csv'
test_path = 'test_data/test_train_1.csv'
test_data = pd.read_csv(test_path)
train_data = pd.read_csv(train_path)
model_type = ML_Model.SVM
model = get_model(model_type, test_data, False)

data_train, data_test, label_train, label_test, feature_names = preprocessing_stats(train_data, test_data)
predicted_data = predict_test_data_individually(model, data_test, label_test, feature_names)

# Predict results
prediction = model.predict(data_test)
print("prediction real:")
print(prediction)
print(model_type.name + " Accuracy:", accuracy_score(label_test, predicted_data))
f1 = f1_score(label_test, predicted_data, average='weighted')  # You can change 'weighted' to 'macro' or 'micro' as needed
print(model_type.name + " F1 Score:", f1)
rmse = np.sqrt(mean_squared_error(label_test, predicted_data))
print(model_type.name + " RMSE:", rmse)
