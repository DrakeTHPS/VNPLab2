from joblib import load
import pandas as pd
import re
import json
import os


class FeatureCollector(object):

    def __init__(self, file_path):
        self.file_path = file_path
        self.file_bytes = open(file_path, 'rb').read()
        self.features = []

    def parse(self, parse_fun):
        return parse_fun(self.file_bytes)

    def add_feature(self, feature):
        self.features.append(feature)

    def add_feature_if_match(self, patterns):
        for p in patterns:
            if re.search(p, self.file_bytes):
                self.add_feature(1)
                return
        self.add_feature(0)

    def default_analyze(self):
        # 1 for (i = 0; i < n; i++)
        # (самый дефолтный цикл)
        self.add_feature_if_match([b'[\xc7\xEB].{0,20}\xeb.{0,20}\x8b.{0,20}\x83\xc0.{0,40}[\x7d\x7F]'])

        # 2 sum += A[i]
        # (сложение инта с элементом массива)
        self.add_feature_if_match(
            [b'\x8b\x45\xe0\x8b\x4d\xf8\x8b\x55\xec\x03\x14\x81\x89\x55\xec', b'\x8b\x85.{0,20}\xff\xff\x8b\x8d.{0,20}\xff\xff\x03\x8c\x85.{0,20}\xff\xff\x89\x8d.{0,20}\xff\xff'])

        # 3 min > A[i]
        # (сравнение инта с элементом массива)
        self.add_feature_if_match(
            [b'\x8b\x45\xe0\x8b\x4d\xf8\x8b.{0,20}\x3b', b'\x8b\x85.{0,20}\xff\xff\x8b\x8d.{0,20}\xff\xff\x3b\x8c\x85.{0,20}\xff\xff\x7e\x13'])

        # 4 min = A[i]
        # (присвоение инту элемента массива)
        self.add_feature_if_match(
            [b'\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x14\x81\x89\x55', b'\x8b\x85.{0,20}\xfe\xff\xff\x8b\x8c\x85\x68\xfe\xff\xff\x89\x8d.{0,20}\xfe\xff\xff'])

        # 5 temp = A[j];
        # A[j] = A[j + 1];
        # A[j + 1] = temp;
        # (свап элементов, часто при сортировках)
        self.add_feature_if_match(
            [b'\x8b\x45\xd4\x8b\x4d\xf8\x8b\x14\x81\x89\x55.{0,20}\x8b\x45\xd4\x8b\x4d\xf8\x8b\x55.{0,20}\x8b\x75\xf8\x8b.{0,20}\x96.{0,20}\x89\x14\x81\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x55.{0,20}\x89.{0,20}\x81',
        b'\x8B\x85.{0,20}\xFE\xFF\xFF\x8B\x8C\x85\x68\xFE\xFF\xFF\x89\x8D.{0,20}\xFE\xFF\xFF\x8B\x85.{0,20}\xFE\xFF\xFF\x8B\x8D.{0,20}\xFE\xFF\xFF\x8B\x94\x8D\x6C\xFE\xFF\xFF\x89\x94\x85\x68\xFE\xFF\xFF\x8B\x85.{0,20}\xFE\xFF\xFF\x8B\x8D.{0,20}\xFE\xFF\xFF\x89\x8C\x85\x6C\xFE\xFF\xFF'])

        # 6 A[j] < A[min]
        # (сравнение элементов массива)
        self.add_feature_if_match(
            [b'\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x55.{0,20}\x8b\x75\xf8\x8b\x04\x81\x3b.{0,20}\x96',
        b'\x8b\x85.{0,20}\xff\xff\x8b\x8d.{0,20}\xff\xff\x8b\x94\x85.{0,20}\xff\xff\x3b\x94\x8d.{0,20}\xff\xff.{0,20}\x40'])

        # 7 A[i] = A[min]
        # (присвоение элемента массива элементу массива)
        self.add_feature_if_match(
            [b'\x8b\x45\xd4\x8b\x4d\xf8\x8b\x55.{0,20}\x8b\x75\xf8\x8b.{0,20}\x96.{0,20}\x89\x14\x81',
        b'\x8b\x85.{0,20}\xff\xff\x8b\x8d.{0,20}\xff\xff\x8b\x94\x8d.{0,20}\xff\xff\x89\x94\x85.{0,20}\xff\xff'])

        # 8 sum += i (сложение инта с интом; i++ не считается)
        self.add_feature_if_match([b'\x8b\x45.{0,20}\x89\x45', b'\x8B\x45.{0,20}\x03\x45.{0,20}\x89\x45'])

        # 9 sum = 0
        # (присвоение переменной константы)
        self.add_feature_if_match([b'\xc7\x45\xec', b'\xc7\x45.{0,20}\x00\x00\x00'])

        # 10 Присваивание элементу массива инта A[i] =x
        self.add_feature_if_match([b'\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x55.{0,20}\x89.{0,20}\x81', b'\x8b\x8d.{0,20}\xfe\xff\xff\x89\x8c.{0,20}\xfe\xff\xff'])

    def get_features_dict(self):
        print(f'Список критериев: {self.features} для файла: {self.file_path}')
        names = ['f' + str(ordinal) for ordinal in range(len(self.features))]
        for_json = dict(zip(names, self.features))
        return for_json

    @staticmethod
    def analyze_folder(folder, model):
        result_dict = []
        result = {}
        arr = os.listdir(folder)
        for somedir in arr:
            filename = folder+'/'+somedir
            if os.path.isfile(filename):
                collector = FeatureCollector(filename)
                collector.default_analyze()
                res = collector.get_features_dict()
                test = [res]
                testing = pd.read_json(json.dumps(test))
                if model.predict(testing)[0] == 1:
                    print('Массив найден!')
                    result[filename] = 1
                else:
                    print('0')
                    result[filename] = 0
            else:
                FeatureCollector.analyze_folder(filename)
        return result


if __name__ == "__main__":
    model = load('trained/GradientBoostingClassifier.joblib')
    result = FeatureCollector.analyze_folder("progs", model)
    print('Массивы найдены в следующих файлах')
    for res in result:
        if result[res] == 1:
            print(res)
