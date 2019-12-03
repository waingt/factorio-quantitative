"""
在 python 3 中运行
需要配方数据缓存文件，或者pyparsing模块，才能运行
(你可以通过 "pip install pyparsing" 命令来安装pyparsing模块)
"""
FACTORIO_PATH = r"D:\Program Files (x86)\Steam\steamapps\common\Factorio/"

import os, re, json, code, ctypes
from fractions import Fraction
from heapq import heapify, heappush, heappop
from configparser import ConfigParser


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
    banned_names = set(
        [
            "light-oil-cracking",
            "heavy-oil-cracking",
            "solid-fuel-from-petroleum-gas",
            "solid-fuel-from-heavy-oil",
            "nuclear-fuel-reprocessing",
            "basic-oil-processing",
        ]
    )
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
    ctypes.windll.kernel32.SetConsoleTextAttribute(STD_OUT_HANDLE, COLOR_DICT[color])


SEPARATOR = "-" * 40
FLUIDS = {
    "water",
    "petroleum-gas",
    "crude-oil",
    "steam",
    "light-oil",
    "heavy-oil",
    "lubricant",
    "sulfuric-acid",
}


def record(count: Fraction, name: str, output, input_):
    s = "{0:>7} {1:<5}: {2} <= {3}".format(fraction_format(count), name, output, input_)
    print(s)


def estimate_belts(d: dict):
    for k, v in d.items():
        if k in FLUIDS:
            b = ""
        elif v <= Fraction(15, 2):
            b = ": 半条黄带"
        elif v <= 15:
            b = ": 半条红带 或 1红带"
        elif v <= Fraction(45, 2):
            b = ": 半条蓝带 或 1红带"
        else:
            b = ": " + str((v / 45).__ceil__()) + "蓝带"
        s = "{0:>7} {1:<5}{2}".format(fraction_format(v), locale_dict[k], b)
        print(s)


def oil_solve(item: dict, scheme=None, beautify_output=True):
    if scheme is None:
        scheme = normal
    X_ORDER = ["advanced-oil-processing", "heavy-oil-cracking", "light-oil-cracking"]
    Y_ORDER = ["petroleum-gas", "light-oil", "heavy-oil"]
    oil_recipe = []
    x = []
    for t in X_ORDER:
        input_, output, time, category = recipe_dict[t]
        time = Fraction(time)
        speed, prod = scheme[category]
        time /= speed
        result = {}
        for i in input_:
            result[i[0]] = result.get(i[0], 0) + i[1] / time
        for i in output:
            result[i[0]] = result.get(i[0], 0) - i[1] / time * prod
        for k in Y_ORDER:
            x.append(result.get(k, 0))
        oil_recipe.append(result)
    output_ = {k: v for k, v in item.items() if k in Y_ORDER}
    y = [-item.get(t, 0) for t in Y_ORDER]
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
                if v < 0:
                    output += fraction_format(-v) + " " + locale_dict[k] + ", "
                else:
                    input_ += fraction_format(v) + " " + locale_dict[k] + ", "
            record(x[i], locale_dict[X_ORDER[i]], output, input_)
    for k in Y_ORDER:
        del item[k]
    if beautify_output:
        print("输入:")
        estimate_belts({k: v for k, v in item.items() if k in FLUIDS})
        print("输出:")
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
            output = fraction_format(a) + " " + locale_dict[i]
            time /= speed
            a = a / prod
            count = a * time
            input_ = ""
            for ii, aa in input_item:
                aa = aa * a
                input_ += fraction_format(aa) + " " + locale_dict[ii] + ", "
                if ii in item_dict:
                    item_dict[ii] += aa
                else:
                    item_dict[ii] = aa
                    heappush(item_heap, (complexity_dict[ii], ii))
            record(count, locale_dict[category], output, input_)
    if beautify_output:
        print("输入:")
        estimate_belts(item_dict)
        print("输出:")
        estimate_belts(advanced)
        print(SEPARATOR)
    return item_dict


def quantitative_factory():
    global result_dict
    for block in factory:
        if block[0] == "result":
            print(block[1] + ":")
            print()
            estimate_belts(result_dict)
            print(SEPARATOR)
        elif block[0] == "炼油区":
            print(block[0].upper())
            print()
            oil_solve(result_dict, block[1], beautify_output=True)
        elif block[0] == "科技区":
            print(block[0].upper())
            print()
            output = {**result_dict}
            result_dict = {}
            reduce(output, science_packs, block[1], beautify_output=False)
            print(SEPARATOR)
        else:
            block_name, output, input_, scheme, color = block
            output = {k: result_dict.pop(k) for k in output}
            set_color(color)
            print(block_name.upper())
            print()
            t = reduce(output, input_, scheme, beautify_output=True)
            set_color("white")
        print()


def get_locale_dict():
    locale_path = r"data\base\locale\zh-CN\base.cfg"
    locale_dict = {}
    cf = ConfigParser()
    cf.read(FACTORIO_PATH + locale_path, encoding="utf8")
    locale_dict.update(cf["entity-name"])
    locale_dict.update(cf["equipment-name"])
    locale_dict.update(cf["fluid-name"])
    locale_dict.update(cf["item-name"])
    locale_dict.update(cf["recipe-name"])
    locale_dict.update(
        {
            "7sp": "7色瓶研究",
            "crafting": "组装",
            "chemistry": "化工",
            "smelting": "熔练",
            "oil-processing": "炼油",
            "centrifuging": "离心机",
            "rocket-building": "发射井",
            "lab": "研究中心",
            "other": "其他",
        }
    )
    return locale_dict


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
    recipe_dict = get_recipe()
    single_product_dict = get_single_product_dict()
    complexity_dict = get_complexity_dict()
    locale_dict = get_locale_dict()
    result_dict = {}
    normal = {
        "crafting": (Fraction("1.25"), Fraction(1)),
        "chemistry": (Fraction(1), Fraction(1)),
        "smelting": (Fraction(2), Fraction(1)),
        "oil-processing": (Fraction(1), Fraction(1)),
        "centrifuging": (Fraction(1), Fraction(1)),
        "rocket-building": (Fraction(1), Fraction(1)),
        "lab": (Fraction(1), Fraction(1)),
        "other": (Fraction(1), Fraction(1)),
    }
    modularize = {
        "crafting": (Fraction("5.5"), Fraction("1.4")),
        "chemistry": (Fraction("4.55"), Fraction("1.3")),
        "smelting": (Fraction("9.4"), Fraction("1.2")),
        "oil-processing": (Fraction("5.55"), Fraction("1.3")),
        "centrifuging": (Fraction(1), Fraction(1)),
        "rocket-building": (Fraction("2"), Fraction("1.4")),
        "lab": (Fraction("10"), Fraction("1.2")),
        "other": (Fraction(1), Fraction(1)),
    }
    raw_items = {
        "copper-ore",
        "iron-ore",
        "stone",
        "coal",
        "water",
        "petroleum-gas",
        "light-oil",
        "heavy-oil",
    }
    smelted_items = {
        "copper-plate",
        "iron-plate",
        "steel-plate",
        "stone",
        "stone-brick",
        "coal",
    }
    chemistry_items = {"sulfuric-acid", "sulfur", "plastic-bar", "lubricant"}
    bus_items = {
        "copper-plate",
        "iron-plate",
        "steel-plate",
        "stone",
        "stone-brick",
        "coal",
        "water",
        "sulfuric-acid",
        "sulfur",
        "plastic-bar",
        "petroleum-gas",
        "light-oil",
        "lubricant",
        "electronic-circuit",
        "advanced-circuit",
        "processing-unit",
    }
    science_packs = {
        "automation-science-pack",
        "logistic-science-pack",
        "chemical-science-pack",
        "production-science-pack",
        "military-science-pack",
        "utility-science-pack",
        "space-science-pack",
    }
    factory = [
        ["科技区", normal],
        ["自动化科技包", {"automation-science-pack"}, bus_items, normal, "red"],
        ["物流科技包", {"logistic-science-pack"}, bus_items, normal, "green"],
        ["化工科技包", {"chemical-science-pack"}, bus_items, normal, "blue"],
        ["生产科技包", {"production-science-pack"}, bus_items, normal, "pink"],
        ["军工科技包", {"military-science-pack"}, bus_items, normal, "gray"],
        ["效能科技包", {"utility-science-pack"}, bus_items, normal, "yellow"],
        ["太空科技包", {"space-science-pack"}, bus_items, normal, "white"],
        ["result", "总线"],
        [
            "蓝板（CPU)区",
            {"processing-unit"},
            smelted_items ^ chemistry_items,
            normal,
            "blue",
        ],
        ["红板区", {"advanced-circuit"}, smelted_items ^ chemistry_items, normal, "red"],
        [
            "绿板区",
            {"electronic-circuit"},
            smelted_items ^ chemistry_items,
            normal,
            "green",
        ],
        ["result", "熔炼后物品或化工物品"],
        ["化工区", chemistry_items, raw_items ^ {"iron-plate"}, normal, "white"],
        ["冶炼区", smelted_items, raw_items, normal, "white"],
        ["炼油区", normal],
        ["result", "原始物品"],
    ]
    code.interact(
        banner="""
    这是一个简单的键入-计算-显示-循环

    试试下面的命令:
    spm(60)
    show()
    clear()
    reduce({'utility-science-pack':2}, bus_items, modularize)
    oil_solve({'petroleum-gas':130, 'light-oil':90, 'heavy-oil':10}, normal)

    键入 exit() 来退出
    """,
        local=locals(),
    )

