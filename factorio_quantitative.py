import os, re, json, code, ctypes
from fractions import Fraction
from heapq import heapify, heappush, heappop
from configparser import ConfigParser

from pyparsing import (
    Suppress,
    CharsNotIn,
    Word,
    Literal,
    alphanums,
    nums,
    Forward,
    delimitedList,
    Dict,
    Group,
    ZeroOrMore,
    Optional,
)
import yaml


def file_cache(func):
    def f():
        s = "./pycache_" + func.__name__ + ".json"
        if os.path.exists(s):
            return json.load(open(s))
        else:
            t = func()
            json.dump(t, open(s, "w"))
            return t

    return f


@file_cache
def get_recipe():
    recipe = {}
    recipe_path = r"data\base\prototypes\recipe/"
    recipe_files = [
        "recipe",
        "inserter",
        "module",
        "fluid-recipe",
        "demo-furnace-recipe",
        "demo-recipe",
    ]

    def Syntax():
        delimitedList = (
            lambda x: x + ZeroOrMore(Suppress(",") + x) + Optional(Suppress(","))
        )
        dbl_quoted = Suppress('"') + Optional(CharsNotIn('"')) + Suppress('"')
        lelem = Word(alphanums + "-_")
        relem = Literal("true") | Literal("false") | Word(nums + ".") | dbl_quoted
        dict_ = Forward()
        assignment = lelem + Suppress("=") + (relem | (dict_))
        dict_ << Suppress("{") + Group(
            Dict(delimitedList(Group(assignment)))
            | (dbl_quoted + Suppress(",") + Word(nums + "."))
            | delimitedList(dict_)
        ) + Suppress("}")
        return Dict(delimitedList(Group(assignment)))

    def flatten(t: dict):
        result = []
        for k in t:
            if type(k) is list:
                k[1] = int(k[1])
                result.append(k)
            else:
                result.append([k["name"], int(k["amount"])])
        return result

    recipe_parser = Syntax()
    for f in recipe_files:
        s = open(FACTORIO_PATH + recipe_path + f + ".lua").read()
        s = re.sub(r"data:extend\(\s*\{\s*\{", "", s, count=1)
        s = re.sub(r"--.*?\n", "", s)
        d = re.split(r"\n  \},\s+  \{", s)
        for t in d:
            t = recipe_parser.parseString(t)
            # print(t.dump())
            t = t.asDict()
            if "normal" in t:
                t.update(t["normal"])
            if "result" not in t:
                t["result"] = t["results"]
            if type(t["result"]) is str:
                t["result"] = [[t["result"], 1]]
            if "result_count" in t:
                t["result"][0][1] = t["result_count"]
            name = t["name"]
            time = t.get("energy_required", "0.5")
            category = t.get("category", "")
            if category not in set(
                [
                    "chemistry",
                    "smelting",
                    "oil-processing",
                    "centrifuging",
                    "rocket-building",
                ]
            ):
                category = "crafting"
            input_ = flatten(t["ingredients"])
            output = flatten(t["result"])
            recipe[name] = [input_, output, time, category]
    recipe.update(
        {
            "space-science-pack": [
                [["rocket-part", 100], ["satellite", 1]],
                [["space-science-pack", 1000]],
                "42.5",
                "other",
            ],
            "7sp": [
                [
                    ["automation-science-pack", 1],
                    ["logistic-science-pack", 1],
                    ["chemical-science-pack", 1],
                    ["production-science-pack", 1],
                    ["military-science-pack", 1],
                    ["utility-science-pack", 1],
                    ["space-science-pack", 1],
                ],
                [["7sp", 1]],
                "60",
                "lab",
            ],
        }
    )
    return recipe


def get_single_product_dict():
    banned_names = {
        "light-oil-cracking",
        "heavy-oil-cracking",
        "solid-fuel-from-petroleum-gas",
        "solid-fuel-from-heavy-oil",
        "nuclear-fuel-reprocessing",
        "basic-oil-processing",
    }
    single_product_dict = {}
    for name, [input_, output, time, category] in recipe_dict.items():
        time = Fraction(time)
        if len(output) == 1 and name not in banned_names:
            if output[0][0] in single_product_dict:
                raise Exception("duplicated recipe!")
            elif output[0][1] == 1:
                single_product_dict[output[0][0]] = [
                    [[i, a] for i, a in input_],
                    time,
                    category,
                    name,
                ]
            else:
                single_product_dict[output[0][0]] = [
                    [[i, Fraction(a, output[0][1])] for i, a in input_],
                    time / output[0][1],
                    category,
                    name,
                ]
    return single_product_dict


def get_complexity_dict():
    BASIC_ITEMS = {
        "copper-ore",
        "iron-ore",
        "stone",
        "coal",
        "water",
        "petroleum-gas",
        "light-oil",
        "heavy-oil",
        "uranium-238",
        "uranium-235",
        "wood",
    }
    complexity_dict = {i: 0 for i in BASIC_ITEMS}
    complexity_dict.update({i: None for i in single_product_dict})

    def compute_complexity_recur(item):
        if complexity_dict[item] is None:
            input_list = single_product_dict[item][0]
            complexity_dict[item] = (
                min([compute_complexity_recur(i) for i, _ in input_list]) - 1
            )
        return complexity_dict[item]

    for k in single_product_dict:
        compute_complexity_recur(k)
    return complexity_dict


def preprocessing_schemes(config):
    if "FACTORIO_PATH" not in config:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"steam\Shell\Open\Command")
        game = winreg.QueryValue(key, "")
        game = game.translate({ord("\\"): "/"})
        game = game[1 : game.index('Steam.exe"')] + r"steamapps/common/Factorio/"
        config["FACTORIO_PATH"] = game
        open(CONFIG_PATH, "a", encoding="utf-8").write("\nFACTORIO_PATH: " + game)
    for s in config["SCHEMES"]:
        for k, v in config[s].items():
            f1, f2 = v
            config[s][k] = [Fraction(f1), Fraction(f2)]


def fraction_format(f: Fraction) -> str:
    t = -(-f.numerator * 10 // f.denominator)
    t = str(t)
    if len(t) <= 1 or t[0] == "-":
        t = t[:-1] + "0." + t[-1:]
    else:
        t = t[:-1] + "." + t[-1:]
    return t


COLOR_DICT = {
    "black": 0x00,
    "darkblue": 0x01,
    "darkgreen": 0x02,
    "darkskyblue": 0x03,
    "darkred": 0x04,
    "darkpink": 0x05,
    "darkyellow": 0x06,
    "darkwhite": 0x07,
    "gray": 0x08,
    "blue": 0x09,
    "green": 0x0A,
    "skyblue": 0x0B,
    "red": 0x0C,
    "pink": 0x0D,
    "yellow": 0x0E,
    "white": 0x0F,
}

STD_OUT_HANDLE = ctypes.windll.kernel32.GetStdHandle(-11)


def set_color(color):
    if color not in COLOR_DICT:
        print("available colors:")
        print(*COLOR_DICT.keys(), sep="\n")
        raise ValueError("wrong color: %s" % color)
    ctypes.windll.kernel32.SetConsoleTextAttribute(STD_OUT_HANDLE, COLOR_DICT[color])


def record(count: Fraction, name: str, output, input_):
    s = "{0:>7} {1:<5}: {2} <= {3}".format(fraction_format(count), name, output, input_)
    print(s)


def estimate_belts(d: dict):
    for k, v in d.items():
        if k in FLUIDS:
            b = ""
        elif v <= Fraction(15, 2):
            b = ": " + translater["half belt"]
        elif v <= 15:
            b = ": " + translater["half fast belt or 1 belt"]
        elif v <= Fraction(45, 2):
            b = ": " + translater["half express belt or 1 fast belt"]
        elif v <= 30:
            b = ": " + translater["1 fast belt"]
        else:
            b = ": " + str((v / 45).__ceil__()) + " " + translater["express belt"]
        s = "{0:>7} {1:<5}{2}".format(fraction_format(v), translater[k], b)
        print(s)


def oil_solve(item: dict, scheme=None, beautify_output=True):
    if scheme is None:
        scheme = normal
    oil_recipe = []
    x = []
    for t in OIL_RECIPES:
        input_, output, time, category = recipe_dict[t]
        time = Fraction(time)
        speed, prod = scheme[category]
        time /= speed
        result = {}
        for i in input_:
            result[i[0]] = result.get(i[0], 0) + i[1] / time
        for i in output:
            result[i[0]] = result.get(i[0], 0) - i[1] / time
        for k, v in result.items():
            if v < 0:
                result[k] = v * prod
        for k in OIL_KINDS:
            x.append(result.get(k, 0))
        oil_recipe.append(result)
    output_ = {**item}
    y = [-item.get(t, 0) for t in OIL_KINDS]
    d = (
        (-x[2]) * x[4] * x[6]
        + x[1] * x[5] * x[6]
        + x[2] * x[3] * x[7]
        - x[0] * x[5] * x[7]
        - x[1] * x[3] * x[8]
        + x[0] * x[4] * x[8]
    )  # determinant of matrix
    t = [
        (
            ((-x[5]) * x[7] + x[4] * x[8]) * y[0]
            + (x[5] * x[6] - x[3] * x[8]) * y[1]
            + ((-x[4]) * x[6] + x[3] * x[7]) * y[2]
        )
        / d,
        (
            (x[2] * x[7] - x[1] * x[8]) * y[0]
            + ((-x[2]) * x[6] + x[0] * x[8]) * y[1]
            + (x[1] * x[6] - x[0] * x[7]) * y[2]
        )
        / d,
        (
            ((-x[2]) * x[4] + x[1] * x[5]) * y[0]
            + (x[2] * x[3] - x[0] * x[5]) * y[1]
            + ((-x[1]) * x[3] + x[0] * x[4]) * y[2]
        )
        / d,
    ]
    x = t
    assert x[0] >= 0 and x[1] >= 0 and x[2] >= 0
    for i, t in enumerate(oil_recipe):
        if x[i] != 0:
            output = ""
            input_ = ""
            for k, v in t.items():
                v = v * x[i]
                item[k] = item.get(k, 0) + v
                temp = result_dict.get(k, 0) + v
                if temp == 0:
                    del result_dict[k]
                else:
                    result_dict[k] = temp
                if v < 0:
                    output += fraction_format(-v) + " " + translater[k] + ", "
                else:
                    input_ += fraction_format(v) + " " + translater[k] + ", "
            record(x[i], translater[OIL_RECIPES[i]], output, input_)
    for k in OIL_KINDS:
        assert item.pop(k, 0) == 0
    if beautify_output:
        print(translater["Input:"])
        estimate_belts({k: v for k, v in item.items()})
        print(translater["Output:"])
        estimate_belts(output_)
        print(SEPARATOR)
    return item


def reduce(advanced, basic, scheme=None, beautify_output=True):
    if scheme is None:
        scheme = normal
    item_dict = {**advanced}
    item_heap = [(complexity_dict[k], k) for k in advanced]
    heapify(item_heap)
    while len(item_heap):
        _, i = heappop(item_heap)
        if i in basic:
            result_dict[i] = result_dict.get(i, 0) + item_dict[i]
        else:
            a = item_dict.pop(i)
            input_item, time, category, name = single_product_dict[i]
            speed, prod = scheme[category]
            output = fraction_format(a) + " " + translater[i]
            time /= speed
            a = a / prod
            count = a * time
            input_ = ""
            for ii, aa in input_item:
                aa = aa * a
                input_ += fraction_format(aa) + " " + translater[ii] + ", "
                if ii in item_dict:
                    item_dict[ii] += aa
                else:
                    item_dict[ii] = aa
                    heappush(item_heap, (complexity_dict[ii], ii))
            record(count, translater[category], output, input_)
    if beautify_output:
        print(translater["Input:"])
        estimate_belts(item_dict)
        print(translater["Output:"])
        estimate_belts(advanced)
        print(SEPARATOR)
    return item_dict


def quantitative_factory():
    global result_dict
    for block in factory:
        if block[1] == "show":
            print(block[0] + ":\n")
            estimate_belts(result_dict)
            print(SEPARATOR)
        elif block[1] == "solve_oil":
            print(block[0].upper() + "\n")
            output = {k: result_dict[k] for k in OIL_KINDS}
            oil_solve(output, block[2], beautify_output=True)
        elif block[1] == "science":
            print(block[0].upper() + "\n")
            output = {k: result_dict.pop(k) for k in ["7sp"]}
            reduce(output, science_packs, block[2], beautify_output=False)
            print(SEPARATOR)
        else:
            block_name, output, input_, scheme, color = block
            output = {k: result_dict.pop(k) for k in output}
            set_color(color)
            print(block_name.upper() + "\n")
            t = reduce(output, input_, scheme, beautify_output=True)
            set_color("white")
        print()


class Translater:
    def __init__(self, locale: str):
        self.locale = locale
        self.locale_dict = LOCALE_DICT.get(locale, {})
        if locale == "en":
            return
        cf = ConfigParser()
        locale_file_path = FACTORIO_PATH + "data/base/locale/" + locale + "/base.cfg"
        if not os.path.exists(locale_file_path):
            raise FileNotFoundError("cannot find locale file in:\n" + locale_file_path)
        cf.read(locale_file_path, encoding="utf8")
        self.locale_dict.update(cf["entity-name"])
        self.locale_dict.update(cf["equipment-name"])
        self.locale_dict.update(cf["fluid-name"])
        self.locale_dict.update(cf["item-name"])
        self.locale_dict.update(cf["recipe-name"])

    def __getitem__(self, word: str):
        return self.locale_dict[word] if word in self.locale_dict else word

    def get_term_list(self, out_path="terms.txt"):
        if self.locale == "en":
            return
        with open(out_path, "w") as f:
            for k, v in self.locale_dict.items():
                if k not in {"script_help"}:
                    f.write("{0} : {1}\n".format(v, k))
        os.startfile(out_path)


def spm(i):
    global result_dict
    result_dict = {"7sp": Fraction(i, 60)}
    quantitative_factory()


def clear():
    global result_dict
    result_dict = {}


def show(d=None):
    if d is None:
        d = result_dict
    estimate_belts(d)


if __name__ == "__main__":
    CONFIG_PATH = "config.yaml"
    config = yaml.full_load(open(CONFIG_PATH, encoding="utf-8"))
    preprocessing_schemes(config)
    globals().update(config)
    recipe_dict = get_recipe()
    single_product_dict = get_single_product_dict()
    complexity_dict = get_complexity_dict()
    translater = Translater(LOCALE)
    result_dict = {}
    code.interact(banner=translater["script_help"], local=locals())
