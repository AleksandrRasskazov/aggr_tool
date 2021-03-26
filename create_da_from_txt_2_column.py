import glob
from datetime import datetime
import json
import time
import os


def add_braces(cis: str) -> str:
    return '(' + cis[0:2] + ')' + cis[2:16] + '(' + cis[16:18] + ')' + cis[18:25]


def make_block(cis):
    if cis.startswith("01") and len(cis) == 25 and is_gtin(cis[2:16]):
        return add_braces(cis)
    elif cis.startswith("01") and len(cis) >= 35 and is_gtin(cis[2:16]) \
            and cis[25:35].startswith("8005") and cis[25:35].isdigit():
        return add_braces(cis)
    else:
        return cis


def is_gtin(gtin: str) -> bool:
    if len(gtin) == 14:
        checkdigit = int(gtin[-1])
        d = list(map(int, list(gtin[:-1])))
        n = [3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3]
        checksum = 0
        for a1, a2 in zip(d, n):
            checksum += a1 * a2
        calculated_check_gigit = int(abs(checksum % - 10))
        return calculated_check_gigit == checkdigit
    else:
        return False


def is_block(cis: str) -> bool:
    if cis.startswith("01") and len(cis) == 25 and is_gtin(cis[2:16]):
        return True
    elif cis.startswith("01") and len(cis) >= 35 and is_gtin(cis[2:16]) \
            and cis[25:35].startswith("8005") and cis[25:35].isdigit():
        return True
    else:
        return False


def batch(iterable, n=1000):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def create_cis(cis: str):
    if len(cis) == 21 and not is_block(cis):
        return cis
    elif len(cis) == 25 and not is_block(cis):
        return cis[:-4]
    else:
        return make_block(cis)


def make_cislist_forcheck(cislist) -> list:
    cislist = set(set([c for cis in cislist for c in cis]))
    return [create_cis(c) for c in cislist if len(c) in (21, 25)]


def extract_cis(txt):
    with open(txt) as f:
        data = f.readlines()
        data = [d.replace("\n", '').replace("\t", ' ').split(" ") for d in data]

        cis_list = make_cislist_forcheck(data)
        len_pack_or_block = 30
        # data = set([s for d in data for s in d if len(s) <= len_pack_or_block])
        # data = set([d for d in data if len(d) <= len_pack_or_block])
        data = set([create_cis(s) for d in data for s in d])
        if len(data) == len(cis_list):
            mc = f.name.split("/")[-1][:-4]
            return {"mc": mc, "cis_list": cis_list}
        else:
            print("Не смог распаковать коды из файла ", txt)
            invalid_files.append(txt)
            return {"error": 'не смог распаковать коды из файла'}


def make_agg(mc, txt):
    """
    тут магия. работает если только формат файла правильный.
    :param mc:
    :param txt:
    :return:
    """
    with open(txt) as f:
        aggregationUnits = []
        all = f.read().rsplit("\n")

        if (len(all) - 1) % 10 == 0:
            blocks_list = []
            lines = all[:-1]
            for line in batch(lines, n=10):
                unitSerialNumber = make_block(line[0].split("\t")[0])
                blocks_list.append(unitSerialNumber)
                sntins = []

                for l in line:
                    sntins.append(l.split("\t")[1])
                packs = {
                    "aggregatedItemsCount": len(sntins),
                    "aggregationType": "AGGREGATION",
                    "aggregationUnitCapacity": 10,
                    "sntins": sntins,
                    "unitSerialNumber": unitSerialNumber
                }
                aggregationUnits.append(packs)
            # blocks = {
            #     "aggregatedItemsCount": len(blocks_list),
            #     "aggregationType": "AGGREGATION",
            #     "aggregationUnitCapacity": 50,
            #     "sntins": blocks_list,
            #     "unitSerialNumber": mc
            # }
            # aggregationUnits.append(blocks)

    finished_da = {
        "aggregationUnits": aggregationUnits,
        "dateDoc": int(time.time()) * 1000, # дата проставляется текущая, но надо указывать дату создания которая пришлет фабрика
        "participantId": inn,
        "productionLineId": "CR99"
    }

    pwd = os.path.dirname(txt)
    filename = f"{pwd}/created_da/{mc}.json"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(finished_da, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    invalid_files = []
    inn = '7809008119'  # в зависимости от фабрики надо указывать ИНН.

    income = '/private/tmp/00/bat/SR01320175/блочка/test/' # путь к папке с txt- файлами
    start = datetime.now()
    print("-" * 10)
    print(start)
    txt_files = glob.glob(f"{income}*.txt")

    for txt in txt_files:
        data = extract_cis(txt)
        if data.get('cis_list'):
            make_agg(data['mc'], txt)
