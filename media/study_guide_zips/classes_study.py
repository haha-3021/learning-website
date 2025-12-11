"""
[Python] クラスとオブジェクト（基礎） 学習用スクリプト

使い方：
- クラスとオブジェクトの教材を、小さなデモ関数（demo_XXX）に分けてあります。
- 実行するとメニューが出るので、番号を選んで動きを確認できます。
- 自分の練習用コードは practice_XXX 関数の中に書いていくと整理しやすいです。

"""

# ============================================================
# 1. クラスとオブジェクトって何？（辞書との比較）
# ============================================================

def demo_1_dict_vs_class_image():
    """
    「クラス = 設計図」「オブジェクト = 実物」というイメージと、
    辞書で書いた場合の問題点を軽く体験するデモ。
    """
    print("=== demo_1_dict_vs_class_image: クラスとオブジェクトのイメージ ===")

    print("\n--- 辞書で書いた場合 ---")
    item1 = {"name": "ノートPC", "price": 120000, "category": "家電"}
    item2 = {"name": "教科書", "price": 3000, "category": "本"}

    print("item1:", item1)
    print("item2:", item2)
    print("item1['name'] ->", item1["name"])

    print("\n※ 辞書だとキー名のtypoに気づきにくい例：")
    try:
        print("item1['prcie'] をアクセスしてみます...")
        print(item1["prcie"])  # 綴りを間違えている
    except KeyError as e:
        print("KeyError が発生しました:", e)
        print("→ 'price' のつもりが 'prcie' と書いてしまった、などに気づきにくい。")

    print("\nここからクラスを使うと、構造と処理を1か所にまとめやすくなります。")


# ============================================================
# 2. 一番シンプルなクラス & __init__ と self
# ============================================================

class SimpleItem:
    """最初は中身なしのクラスからスタートしてみるためのサンプル。"""
    pass


class Item:
    """
    教材で出てきた Item クラス。
    name, price, category を属性として持ちます。
    """
    def __init__(self, name, price, category):
        # self は「これから作るこのオブジェクト自身」
        self.name = name
        self.price = price
        self.category = category


def demo_2_basic_class_and_init():
    """
    - class Item: の基本形
    - __init__ と self の役割
    - オブジェクト（インスタンス）を作って属性にアクセスする
    """
    print("=== demo_2_basic_class_and_init: 一番シンプルなクラスと __init__ ===")

    print("\n--- SimpleItem クラス（中身なし）---")
    s = SimpleItem()
    print("SimpleItem のインスタンスを作りました:", s)

    print("\n--- Item クラスでオブジェクトを作る ---")
    item1 = Item("ノートPC", 120000, "家電")
    item2 = Item("教科書", 3000, "本")

    print("item1.name     ->", item1.name)
    print("item1.price    ->", item1.price)
    print("item1.category ->", item1.category)

    print("item2.name     ->", item2.name)
    print("item2.price    ->", item2.price)
    print("item2.category ->", item2.category)

    print("\n※ Item(\"ノートPC\", 120000, \"家電\") と書いたときに __init__ が呼ばれ、")
    print("   self.name / self.price / self.category が設定されます。")


# ============================================================
# 3. メソッド（クラスの中の関数）と __str__
# ============================================================

class ItemWithMethods:
    """
    税込み価格を計算するメソッドと、__str__ を持った Item クラス。
    """
    def __init__(self, name, price, category):
        self.name = name
        self.price = price
        self.category = category

    def get_tax_included_price(self, tax_rate=0.1):
        total = int(self.price * (1 + tax_rate))
        return total

    def __str__(self):
        return f"{self.name} ({self.category}) - {self.price}円"


def demo_3_methods_and_str():
    """
    - メソッド（第1引数 self）
    - メソッド呼び出し
    - __str__ を使って print() の表示を分かりやすくする
    """
    print("=== demo_3_methods_and_str: メソッドと __str__ ===")

    item = ItemWithMethods("ノートPC", 120000, "家電")

    print("\n--- オブジェクトの属性にアクセス ---")
    print("item.name     ->", item.name)
    print("item.price    ->", item.price)
    print("item.category ->", item.category)

    print("\n--- メソッドで税込価格を計算 ---")
    print("デフォルト税率 (0.1):", item.get_tax_included_price())
    print("税率 0.08:", item.get_tax_included_price(0.08))

    print("\n--- __str__ による表示 ---")
    print("print(item) ->", item)
    print("※ __str__ を定義していないクラスだと、メモリアドレスみたいな表示になることが多いです。")


# ============================================================
# 4. クラスと辞書の違いをもう一度比較
# ============================================================

def demo_4_class_vs_dict_again():
    """
    辞書版とクラス版の違いを、短く比較するデモ。
    """
    print("=== demo_4_class_vs_dict_again: クラスと辞書の違い ===")

    print("\n--- 辞書版 ---")
    dict_item = {"name": "ノートPC", "price": 120000, "category": "家電"}
    print("dict_item:", dict_item)
    print("dict_item['name'] ->", dict_item["name"])

    print("\n--- クラス版 ---")
    class_item = ItemWithMethods("ノートPC", 120000, "家電")
    print("class_item.name ->", class_item.name)
    print("class_item.get_tax_included_price() ->", class_item.get_tax_included_price())
    print("print(class_item) ->", class_item)

    print("\nポイント：")
    print("- 辞書はシンプルで短いけれど、キー名のtypoなどに弱い。")
    print("- クラスは『構造』と『振る舞い（メソッド）』を1か所にまとめられる。")
    print("- Django の Model も、この『クラス版』の発展形だと思うと分かりやすい。")


# ============================================================
# 5. クラス変数とインスタンス変数（tax_rate の例）
# ============================================================

class ItemWithClassVar:
    # クラス変数（全インスタンス共通）
    tax_rate = 0.1

    def __init__(self, name, price):
        # インスタンス変数（各オブジェクトごとに違う値を持つ）
        self.name = name
        self.price = price

    def get_tax_included_price(self):
        # ItemWithClassVar.tax_rate でクラス変数を参照
        return int(self.price * (1 + ItemWithClassVar.tax_rate))

    def __str__(self):
        return f"{self.name} - {self.price}円 (税率: {ItemWithClassVar.tax_rate})"


def demo_5_instance_and_class_variables():
    """
    - インスタンス変数（self.xxx）
    - クラス変数（クラス名.xxx）
    の違いを体験するデモ。
    """
    print("=== demo_5_instance_and_class_variables: クラス変数とインスタンス変数 ===")

    item1 = ItemWithClassVar("ノートPC", 120000)
    item2 = ItemWithClassVar("教科書", 3000)

    print("\n--- 初期状態（tax_rate = 0.1）---")
    print(item1, "税込み:", item1.get_tax_included_price())
    print(item2, "税込み:", item2.get_tax_included_price())

    print("\n--- クラス変数 tax_rate を 0.08 に変更 ---")
    ItemWithClassVar.tax_rate = 0.08

    print(item1, "税込み:", item1.get_tax_included_price())
    print(item2, "税込み:", item2.get_tax_included_price())

    print("\n※ クラス変数を変えると、すべてのインスタンスの振る舞いに影響します。")
    print("   Django の Model では、フィールド定義などにクラス変数が使われています。")


# ============================================================
# 6. Django の Model とクラスの関係（イメージ）
# ============================================================

def demo_6_django_model_image():
    """
    Django の Model がクラスであることをイメージとして確認する。
    実際に django を import するのではなく、コードを文字列として表示するだけ。
    """
    print("=== demo_6_django_model_image: Django の Model とクラスの関係 ===")
    print("Django でよく見るコード例：\n")
    print("from django.db import models\n")
    print("class Item(models.Model):")
    print("    name = models.CharField(max_length=200)")
    print("    price = models.IntegerField()")
    print("    category = models.CharField(max_length=100)\n")
    print("    def __str__(self):")
    print("        return f\"{self.name} - {self.price}円\"\n")
    print("ポイント：")
    print("- class Item(models.Model): → models.Model を継承したクラス")
    print("- name = models.CharField(...) → クラス変数（Django が特別に扱ってDBのカラムになる）")
    print("- def __str__(self): → さっき学んだ __str__ と同じ")
    print("\n→ Django の Model は『models.Model を土台にした、自分専用のデータクラス』と考えるとOK。")


# ============================================================
# 7. 練習スペース（Student クラスなどを書く）
# ============================================================

def practice_1_student_class():
    """
    練習1: シンプルな Student クラスを作る

    仕様：
    - クラス名：Student
    - 属性：
        - name（名前）
        - grade（学年：例 1, 2, 3）
    - メソッド：
        - introduce()
          → 「私は{name}です。{grade}年生です。」と表示する

    TODO:
    - 下の pass を消して、自分で Student クラスとテストコードを書いてみてください。
    """
    print("=== practice_1_student_class ===")
    print("※ ここに自分で Student クラスを定義して、インスタンスを作ってみてください。")

    # 例：こんな形になります（自分で一度書いてみるのがおすすめなのでコメントにしてあります）
    """
    class Student:
        def __init__(self, name, grade):
            self.name = name
            self.grade = grade

        def introduce(self):
            print(f\"私は{self.name}です。{self.grade}年生です。\")
    
    s1 = Student(\"山田\", 2)
    s2 = Student(\"李\", 3)
    s1.introduce()
    s2.introduce()
    """

    # ↑ 上の例を参考に、自分の書き方で実装してみてください。
    pass  # 自分のコードを書けたら、この pass を消します。


def demo_practice_area():
    """
    練習用エリア。
    上の practice_XXX 関数を呼び出して、自分の書いたクラスを試します。
    """
    print("=== demo_practice_area ===")
    print("※ まず practice_1_student_class の中身を書いてから、ここで呼び出してテストしてください。")

    # 書けたらコメントアウトを外して実行
    # practice_1_student_class()
    print("（今はまだサンプルのままなので、practice_1_student_class の pass を書き換えてから試してみてください。）")


# ============================================================
# メニュー & メイン処理
# ============================================================

def main_menu():
    while True:
        print("\n==============================")
        print("[Python] クラスとオブジェクト（基礎）デモメニュー")
        print("1: クラスとオブジェクトのイメージ & 辞書との比較")
        print("2: 一番シンプルなクラスと __init__ / self")
        print("3: メソッドと __str__")
        print("4: クラスと辞書の違いをもう一度比較")
        print("5: クラス変数とインスタンス変数（tax_rate の例）")
        print("6: Django の Model とクラスの関係（イメージ）")
        print("P: 練習問題エリア（Student クラスなどを自分で書く）")
        print("0: 終了")
        print("==============================")
        choice = input("番号を選んでください: ")

        if choice == "1":
            demo_1_dict_vs_class_image()
        elif choice == "2":
            demo_2_basic_class_and_init()
        elif choice == "3":
            demo_3_methods_and_str()
        elif choice == "4":
            demo_4_class_vs_dict_again()
        elif choice == "5":
            demo_5_instance_and_class_variables()
        elif choice == "6":
            demo_6_django_model_image()
        elif choice.upper() == "P":
            demo_practice_area()
        elif choice == "0":
            print("終了します。")
            break
        else:
            print("0〜6 または P を入力してください。")


if __name__ == "__main__":
    main_menu()
