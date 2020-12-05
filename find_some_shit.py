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

    def add_feature_if_match(self, pattern):
        if re.search(pattern, self.file_bytes):
            self.add_feature(1)
        else:
            self.add_feature(0)

    def default_analyze(self):
        # 1 for (i = 0; i < n; i++)
        # (самый дефолтный цикл)
        self.add_feature_if_match(
            b'\xc7\x45.{0,20}\x00\x00\x00\x00\xeb\x09\x8b\x45.{0,20}\x83\xc0\x01\x89\x45.{0,20}\x83\x7d.{0,20}\x0a')

        # 2 sum += A[i]
        # (сложение инта с элементом массива)
        self.add_feature_if_match(
            b'\x8b\x45\xe0\x8b\x4d\xf8\x8b\x55\xec\x03\x14\x81\x89\x55\xec')

        # 3 min > A[i]
        # (сравнение инта с элементом массива)
        self.add_feature_if_match(
            b'\x8b\x45\xe0\x8b\x4d\xf8\x8b.{0,20}\x14\x81')

        # 4 min = A[i]
        # (присвоение инту элемента массива)
        self.add_feature_if_match(
            b'\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x14\x81\x89\x55')

        # 5 temp = A[j];
        # A[j] = A[j + 1];
        # A[j + 1] = temp;
        # (свап элементов, часто при сортировках)
        self.add_feature_if_match(
            b'\x8b\x45\xd4\x8b\x4d\xf8\x8b\x14\x81\x89\x55.{0,20}\x8b\x45\xd4\x8b\x4d\xf8\x8b\x55.{0,20}\x8b\x75\xf8\x8b.{0,20}\x96.{0,20}\x89\x14\x81\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x55.{0,20}\x89.{0,20}\x81')

        # 6 A[j] < A[min]
        # (сравнение элементов массива)
        self.add_feature_if_match(
            b'\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x55.{0,20}\x8b\x75\xf8\x8b\x04\x81\x3b.{0,20}\x96')

        # 7 A[i] = A[min]
        # (присвоение элемента массива элементу массива)
        self.add_feature_if_match(
            b'\x8b\x45\xd4\x8b\x4d\xf8\x8b\x55.{0,20}\x8b\x75\xf8\x8b.{0,20}\x96.{0,20}\x89\x14\x81')

        # 8 sum += i (сложение инта с интом; i++ не считается)
        self.add_feature_if_match(b'\x8b\x45.{0,20}\x89\x45')

        # 9 sum = 0
        # (присвоение переменной константы)
        self.add_feature_if_match(b'\xc7\x45\xec')

        # 10 Присваивание элементу массива инта A[i] =x
        self.add_feature_if_match(b'\x8b\x45.{0,20}\x8b\x4d\xf8\x8b\x55.{0,20}\x89.{0,20}\x81')

    def get_features_dict(self):
        print(f'Features list: {self.features} for file: {self.file_path}')
        names = ['f' + str(ordinal) for ordinal in range(len(self.features))]
        for_json = dict(zip(names, self.features))
        return for_json

    def get_features_json(self):
        return json.dumps(self.get_features_dict())

    @staticmethod
    def analyze_folder(folder, result_ds_path=None):
        file_list = []
        for root, dirs, files in os.walk(folder):
            for filename in files:
                file_list.append(root + '\\' + filename)

        result_dict = []
        for filename in file_list:
            collector = FeatureCollector(filename)
            collector.default_analyze()
            result_dict.append(collector.get_features_dict())
        json_string = json.dumps(result_dict)
        if result_ds_path:
            with open(result_ds_path, 'w') as export:
                export.write(json_string)
        return json_string


if __name__ == "__main__":
    json = FeatureCollector.analyze_folder("progs", 'result_ds.json')