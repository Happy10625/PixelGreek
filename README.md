# Pixel Greek

**像素希腊字母拼接程序**: 接收输入古希腊文本, 输出像素方块字体的图片

从 `lib/alphabet.bmp` 和 `lib/vowel.bmp` 中提取像素希腊字母，输入文本后拼接输出像素图（BMP 格式）。普通字母来自 `alphabet.bmp`；多调元音、ῥ/Ῥ 和标点来自 `vowel.bmp`，其排列由 `lib/vowel.txt` 定义。

`vowel.txt` 中出现的字符总是优先于普通字母表中的同名字符。程序也会把分解形式的 Unicode（例如 `α` 加组合换气符）规范化为对应的预组字符后再匹配。

`vowel.bmp` 的小写字母和标点以 12 像素为横向切割步长，大写字母以 18 像素为横向切割步长；两部分的首字符都从 `x=4` 开始。

标点 ``, . · ; ᾿ ῾ ´ ` !`` 宽 4 像素，抑扬符 `῀` 宽 7 像素。无法识别的字符使用同一感叹号字形，并在右侧补白为 7 像素宽；正常输入的 `!` 仍为 4 像素宽。

布局:

 Row 1 (y=3-21):  小写 α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ  (17个)

 Row 2 (y=25-43): 小写 σ ς τ υ φ χ ψ ω             (8个, ς在σ后)

 Row 3 (y=52-70): 大写 Α Β Γ Δ Ε Ζ Η Θ Ι Κ Λ Μ Ν Ξ Ο Π   (16个, Ι在x=103-109)

 Row 4 (y=78-96): 大写 Ρ Σ Τ Υ Φ Χ Ψ Ω             (8个, 从Ρ开始)

用法:

```bash
python pixel_greek.py ΑΘΗΝΑ           # 输出 输出.bmp

python pixel_greek.py -o result.bmp αβγδ    # 指定输出文件

python pixel_greek.py --scale 3 ΑΘΗΝΑ      # 3倍缩放

python pixel_greek.py --max-width 400 ΑΘΗΝΑ # 指定自动换行宽度

python pixel_greek.py --chart          # 生成字符表图片
# 读取txt, 输出同名bmp
python pixel_greek.py input.txt              # →input.bmp
# 多行txt, 每行独立渲染后垂直拼接
python pixel_greek.py --scale 4 text.txt     # →text.bmp
# 用 -o 覆盖输出文件名
python pixel_greek.py input.txt -o out.bmp   # →out.bmp
# 也支持 --file 方式
python pixel_greek.py --file input.txt       # →input.bmp
```

  新增参数：`--line-gap N` 控制多行文本的行间距（默认2像素）

  默认布局：成品图片左右各有 3 像素白边；空格渲染为7像素宽空白；文本超过400像素时自动换行，单个字母不会被拆在换行位置。

  行首空格后若是大写字母，该行首空格按 `lib/元音字母说明.txt` 缩为 5 像素宽。

运行测试使用下面的方法, 并查看lib/文件夹是否生成了满足要求的正确识别切割的字符库.

```bash
python pixel_greek.py lib/testall.txt
```

## 个性化改造

推荐使用graphics gale程序编辑像素字符库模板(.gal)文件, 或者熟悉画图与其他像素制图方法的开发者也可以直接改动或导出bmp文件. 多调元音的字符库制作晚于基本希腊字母, 因而字符宽度和切割方法都较规范便于重用. 基本希腊字母的字符则没有采取规律的图像切割方法, 因而如果要调整字符宽度还需额外改动代码. 制作水平较拙劣, 望见谅!

祝各位希腊字母和像素字体爱好者使用愉快!
