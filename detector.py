from flow_inspector import ml_flow
# from ml_detector import create_model, load_model
import os

## this is the pre monitor function that labels the removed flows as malicious or not
## if removed flows has suspected flows then monitoring can work
def flow_labeller(flow_table):
    ml_flow_table = ml_flow(flow_table)
    model = []
    ## check if there is model file, if not create a new model
    if not os.path.exists('model.pkl'):
        print('Model file does not exist, creating a new model...')
        # model = create_model(ml_flow_table)
    else:
        print('Model file exists, loading the model...')
        # model = load_model()
    ## get the prediction for each flow
    ml_flow_table['label'] = model.predict(ml_flow_table.drop(columns=['cookie']))
    return ml_flow_table

  
    
    
    
    
    
    
    
  