from find_some_shit import FeatureCollector
from joblib import load
import pandas as pd
import os

models = []
for root, dirs, files in os.walk("trained"):
    for filename in files:
        models.append(root + '\\' + filename)

for model_file in models:
    testing = pd.read_json(FeatureCollector.analyze_folder("progs"))
    model = load(model_file)
    predicted = model.predict(testing)
    print(predicted)