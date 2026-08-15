#!/usr/bin/env python3

import struct
import sys
import os
import unicodedata

# 修复Windows终端GBK编码问题
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================
# 配置
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BMP_FILE = os.path.join(SCRIPT_DIR, 'lib/alphabet.bmp')
VOWEL_BMP_FILE = os.path.join(SCRIPT_DIR, 'lib/vowel.bmp')
VOWEL_MAP_FILE = os.path.join(SCRIPT_DIR, 'lib/vowel.txt')
SPACE_WIDTH = 7
LEADING_UPPER_SPACE_WIDTH = 5
HORIZONTAL_PADDING = 3
DEFAULT_MAX_WIDTH = 500

VOWEL_LOWER_ROWS = 16
VOWEL_TOTAL_ROWS = 27
VOWEL_ROW_HEIGHT = 19
VOWEL_LOWER_Y = 3
VOWEL_UPPER_Y = 307
VOWEL_X = 4
VOWEL_LOWER_X_STEP = 12
VOWEL_UPPER_X_STEP = 18
VOWEL_PUNCTUATION = frozenset(
    {',', '.', '·', ';', '᾿', '῾', '´', '`', '῀', '!'}
)
VOWEL_WIDE_PUNCTUATION = frozenset({'῀'})

ROWS = {
    'R1': (3, 21),
    'R2': (25, 43),
    'R3': (52, 70),
    'R4': (78, 96),
}

CHAR_REGIONS = {
    'R1': [  # 小写 α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ
        (7, 13), (19, 24), (30, 36), (42, 48), (54, 57),
        (63, 69), (75, 81), (87, 92), (98, 101), (107, 113),
        (119, 124), (130, 136), (142, 146), (152, 158), (164, 170),
        (176, 182), (188, 194),
    ],
    'R2': [  # 小写 σ τ υ φ χ ψ ω ς
        (7, 13), (19, 25), (31, 37), (43, 49),
        (55, 63), (69, 75), (81, 89), (95, 101),
    ],
    'R3': [  # 大写 Α Β Γ Δ Ε Ζ Η Θ Ι(103-109) Κ Λ Μ Ν Ξ Ο Π
        (7, 13), (19, 25), (31, 37), (43, 49), (55, 61),
        (67, 73), (79, 85), (91, 97),
        (103, 109),  # Ι (iota, 1像素宽竖线, 用户指定103-109)
        (115, 121), (127, 133), (139, 145), (151, 157),
        (163, 169), (175, 181), (187, 193),
    ],
    'R4': [  # 大写 Σ Τ Υ Φ Χ Ψ Ω
        (7, 13), (19, 25), (31, 37), (44, 50),
        (55, 61), (67, 73), (79, 85), (91, 97),
    ],
}

# 大写: Α(U+0391) ~ Ρ(U+03A1), then Σ(U+03A3) ~ Ω(U+03A9)
# 注意: U+03A2 不存在 (Unicode未分配)
UPPER = [chr(c) for c in range(0x0391, 0x03A2)] + [chr(c) for c in range(0x03A3, 0x03AA)]
# 小写: α(U+03B1) ~ ρ(U+03C1), then σ(U+03C3) ~ ω(U+03C9)
# 注意: U+03C2 = ς (final sigma), 不在标准序列中
LOWER = [chr(c) for c in range(0x03B1, 0x03C2)] + [chr(c) for c in range(0x03C3, 0x03CA)]
SIGMA_FINAL = 'ς'  # U+03C2


def build_char_mapping():
    mapping = {}
    # 小写 Row1: α(0)..ρ(16)
    for i in range(17):
        mapping[LOWER[i]] = ('R1', i)
    # 大写 Row3: Α(0)..Π(15) = 16个, Ι在position 8
    for i in range(16):
        mapping[UPPER[i]] = ('R3', i)
    # 大写 Row4: Ρ(16) Σ(17) Τ(18) Υ(19) Φ(20) Χ(21) Ψ(22) Ω(23) = 8个
    for i in range(8):
        mapping[UPPER[16 + i]] = ('R4', i)
    # 小写 Row2: σ ς τ υ φ χ ψ ω
    # (必须在R3/R4之后设置, 避免被大写σ/ς覆盖)
    mapping['σ'] = ('R2', 0)       # σ -> R2 position 0
    mapping[SIGMA_FINAL] = ('R2', 1)  # ς -> R2 position 1 (紧跟σ后)
    for i in range(6):               # τ υ φ χ ψ ω -> R2 positions 2-7
        mapping[LOWER[18 + i]] = ('R2', 2 + i)
    return mapping


def apply_final_sigma(text):
    result = []
    for i, ch in enumerate(text):
        if ch == 'σ':  # σ
            next_ch = text[i + 1] if i + 1 < len(text) else ''
            if not next_ch or not ('α' <= next_ch <= 'ω'):
                result.append(SIGMA_FINAL)
            else:
                result.append(ch)
        else:
            result.append(ch)
    return ''.join(result)


# ============================================================
# BMP 解析与生成
# ============================================================

class BMPPixelFont:
    def __init__(
        self,
        bmp_path,
        vowel_bmp_path=VOWEL_BMP_FILE,
        vowel_map_path=VOWEL_MAP_FILE,
    ):
        self.pixel_data = None
        self.height = 0
        self.row_bytes = 0
        self.char_images = {}
        self.glyph_sources = {}
        self.vowel_rows = []
        self._load(bmp_path)
        self._extract_all()
        if vowel_bmp_path and vowel_map_path:
            self._extract_vowels(vowel_bmp_path, vowel_map_path)

    def _load(self, path):
        with open(path, 'rb') as f:
            data = f.read()
        bf_off = struct.unpack_from('<I', data, 10)[0]
        w = struct.unpack_from('<i', data, 18)[0]
        self.height = struct.unpack_from('<i', data, 22)[0]
        self.row_bytes = ((w + 31) // 32) * 4
        self.pixel_data = data[bf_off:]

    def _get_pixel(self, x, y):
        real_y = self.height - 1 - y
        byte_idx = real_y * self.row_bytes + x // 8
        bit_idx = 7 - (x % 8)
        return (self.pixel_data[byte_idx] >> bit_idx) & 1

    def _extract_region(self, x1, y1, x2, y2):
        pixels = []
        for y in range(y1, y2 + 1):
            row = []
            for x in range(x1, x2 + 1):
                row.append(self._get_pixel(x, y))
            pixels.append(row)
        return pixels

    def _extract_all(self):
        mapping = build_char_mapping()
        for char, (row_name, idx) in mapping.items():
            regions = CHAR_REGIONS[row_name]
            if idx < len(regions):
                x1, x2 = regions[idx]
                y1, y2 = ROWS[row_name]
                self.char_images[char] = self._extract_region(x1, y1, x2, y2)
                self.glyph_sources[char] = 'alphabet'

    @staticmethod
    def _read_vowel_rows(path):
        with open(path, 'r', encoding='utf-8-sig') as f:
            rows = [line.split() for line in f if line.strip()]
        if len(rows) != VOWEL_TOTAL_ROWS:
            raise ValueError(
                f'vowel mapping must contain {VOWEL_TOTAL_ROWS} rows: {path}'
            )
        chars = [char for row in rows for char in row]
        if any(len(char) != 1 for char in chars):
            raise ValueError(f'each vowel mapping entry must be one Unicode character: {path}')
        if len(chars) != len(set(chars)):
            raise ValueError(f'vowel mapping contains duplicate characters: {path}')
        return rows

    @staticmethod
    def _vowel_glyph_width(char, is_upper):
        if char in VOWEL_WIDE_PUNCTUATION:
            return 7
        if char in VOWEL_PUNCTUATION:
            return 4
        base = unicodedata.normalize('NFD', char)[0]
        if is_upper:
            return 9 if base == 'Ι' else 13
        return 5 if base in {'ε', 'ι'} else 7

    def _extract_vowels(self, bmp_path, map_path):
        rows = self._read_vowel_rows(map_path)
        vowel_sheet = BMPPixelFont.__new__(BMPPixelFont)
        vowel_sheet.pixel_data = None
        vowel_sheet.height = 0
        vowel_sheet.row_bytes = 0
        vowel_sheet._load(bmp_path)

        self.vowel_rows = rows
        for row_index, chars in enumerate(rows):
            is_upper = row_index >= VOWEL_LOWER_ROWS
            if is_upper:
                y1 = VOWEL_UPPER_Y + (row_index - VOWEL_LOWER_ROWS) * VOWEL_ROW_HEIGHT
            else:
                y1 = VOWEL_LOWER_Y + row_index * VOWEL_ROW_HEIGHT
            y2 = y1 + VOWEL_ROW_HEIGHT - 1
            if y2 >= vowel_sheet.height:
                raise ValueError(f'vowel row {row_index + 1} exceeds bitmap height')

            for column, char in enumerate(chars):
                x_step = VOWEL_UPPER_X_STEP if is_upper else VOWEL_LOWER_X_STEP
                x1 = VOWEL_X + column * x_step
                width = self._vowel_glyph_width(char, is_upper)
                x2 = x1 + width - 1
                # vowel.bmp is deliberately loaded last: it wins every conflict
                # with the basic alphabet sheet.
                self.char_images[char] = vowel_sheet._extract_region(x1, y1, x2, y2)
                self.glyph_sources[char] = 'vowel'

    def get_char(self, char):
        if char == ' ':
            return [[1] * SPACE_WIDTH]
        if char in self.char_images:
            return self.char_images[char]
        # 未知字符: 使用样字中的感叹号，并在右侧补白到 7 像素。
        if '!' in self.char_images:
            exclamation = self.char_images['!']
            return [row + [1] * (7 - len(row)) for row in exclamation]
        # 字库损坏或未加载扩展字符时的保底感叹号。
        return [
            [1, 1, 1, 0, 1, 1, 1],
            [1, 1, 1, 0, 1, 1, 1],
            [1, 1, 1, 0, 1, 1, 1],
            [1, 1, 1, 0, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 0, 1, 1, 1],
        ]

    def _text_mats(self, text):
        """Resolve a string to glyphs, including the documented leading indent."""
        normalized = unicodedata.normalize('NFC', text)
        first_non_space = next((i for i, char in enumerate(normalized) if char != ' '), None)
        shorten_indent = (
            first_non_space is not None
            and unicodedata.category(normalized[first_non_space]) == 'Lu'
        )
        mats = []
        for index, char in enumerate(normalized):
            if char == ' ' and shorten_indent and index < first_non_space:
                mats.append([[1] * LEADING_UPPER_SPACE_WIDTH])
            else:
                mats.append(self.get_char(char))
        return mats

    @staticmethod
    def _render_line_mats(mats, gap):
        max_h = max(len(m) for m in mats)
        result = []
        for y in range(max_h):
            row = []
            for i, m in enumerate(mats):
                row.extend(m[y] if y < len(m) else [1] * len(m[0]))
                if i < len(mats) - 1:
                    row.extend([1] * gap)
            result.append(row)
        return result

    def _wrap_mats(self, mats, gap=1, max_width=DEFAULT_MAX_WIDTH):
        if not max_width or max_width <= 0:
            return [mats]

        lines = []
        current = []
        current_width = 0
        for m in mats:
            char_width = len(m[0])
            next_width = char_width if not current else current_width + gap + char_width
            if current and next_width > max_width:
                lines.append(current)
                current = [m]
                current_width = char_width
            else:
                current.append(m)
                current_width = next_width
        if current:
            lines.append(current)
        return lines

    def render_text(self, text, gap=1, max_width=DEFAULT_MAX_WIDTH, line_gap=2):
        if not text:
            return []
        mats = self._text_mats(text)
        wrapped = self._wrap_mats(mats, gap=gap, max_width=max_width)
        if len(wrapped) == 1:
            return self._render_line_mats(wrapped[0], gap)
        return self._join_rendered_lines(
            [self._render_line_mats(line, gap) for line in wrapped],
            line_gap=line_gap,
        )

    @staticmethod
    def _join_rendered_lines(rendered, line_gap=2):
        rendered = [block for block in rendered if block]
        if not rendered:
            return []
        # 统一宽度 (取最宽行)
        max_w = max(len(r[0]) for r in rendered)
        canvas = []
        for idx, block in enumerate(rendered):
            for row in block:
                canvas.append(row + [1] * (max_w - len(row)))  # 右侧补白
            if idx < len(rendered) - 1:
                for _ in range(line_gap):
                    canvas.append([1] * max_w)  # 行间距
        return canvas

    def render_multiline(self, lines, gap=1, line_gap=2, max_width=DEFAULT_MAX_WIDTH):
        """渲染多行文本, 每行独立渲染后垂直拼接"""
        if not lines:
            return []
        rendered = []
        for line in lines:
            if line.strip():
                pixels = self.render_text(line, gap=gap, max_width=max_width, line_gap=line_gap)
                if pixels:
                    rendered.append(pixels)
        return self._join_rendered_lines(rendered, line_gap=line_gap)

    @staticmethod
    def pixels_to_bmp(
        pixels,
        scale=1,
        bg=(255, 255, 255),
        fg=(0, 0, 0),
        horizontal_padding=0,
    ):
        """将像素矩阵转为24位BMP字节数据 (支持缩放和自定义颜色)"""
        if not pixels:
            return b''
        src_h = len(pixels)
        src_w = len(pixels[0])
        h = src_h * scale
        content_w = src_w * scale
        w = content_w + horizontal_padding * 2
        row_bytes = ((w * 3 + 3) // 4) * 4  # 24-bit: 3 bytes per pixel, padded to 4

        # BMP Header (14) + BITMAPINFOHEADER (40) = 54 bytes
        header = bytearray(54)
        header[0:2] = b'BM'
        file_size = 54 + row_bytes * h
        struct.pack_into('<I', header, 2, file_size)
        struct.pack_into('<I', header, 10, 54)
        struct.pack_into('<I', header, 14, 40)
        struct.pack_into('<i', header, 18, w)
        struct.pack_into('<i', header, 22, h)
        struct.pack_into('<H', header, 26, 1)
        struct.pack_into('<H', header, 28, 24)
        struct.pack_into('<I', header, 34, row_bytes * h)

        pixel_data = bytearray(row_bytes * h)
        for y in range(h):
            src_y = y // scale
            real_y = h - 1 - y
            for x in range(w):
                content_x = x - horizontal_padding
                src_x = content_x // scale
                if (
                    0 <= content_x < content_w
                    and src_y < src_h
                    and pixels[src_y][src_x] == 0
                ):
                    color = fg  # black pixel
                else:
                    color = bg  # white background
                byte_idx = real_y * row_bytes + x * 3
                pixel_data[byte_idx] = color[0]      # B
                pixel_data[byte_idx + 1] = color[1]  # G
                pixel_data[byte_idx + 2] = color[2]  # R

        return bytes(header) + bytes(pixel_data)

    def make_chart_image(self, scale=2):
        """生成字符表图片 (返回像素矩阵)"""
        mapping = build_char_mapping()
        row_order = ['R1', 'R2', 'R3', 'R4']

        # vowel.txt 的分行保持原样；alphabet 中没有被 vowel 覆盖的字符
        # 再按原来的四行追加。
        rows_layout = []
        for chars in self.vowel_rows:
            images = [(char, self.char_images[char]) for char in chars]
            rows_layout.append(images)

        row_chars = {}
        for rn in row_order:
            chars = []
            for char, (row_name, idx) in mapping.items():
                if row_name == rn and self.glyph_sources.get(char) == 'alphabet':
                    chars.append((idx, char))
            chars.sort()
            row_chars[rn] = chars
        for rn in row_order:
            images = [(char, self.char_images[char]) for _, char in row_chars[rn]]
            if images:
                rows_layout.append(images)

        padding = 2
        label_w = 12
        measured_rows = []
        for images in rows_layout:
            total_w = label_w + sum(len(img[0]) for _, img in images) + padding * len(images)
            max_h = max(len(img) for _, img in images)
            measured_rows.append((images, total_w, max_h))

        # 总图片尺寸
        total_width = max(row[1] for row in measured_rows) + padding
        total_height = sum(row[2] + padding * 2 for row in measured_rows) + padding

        # 创建白色画布
        canvas = [[1] * total_width for _ in range(total_height)]

        # 绘制每个字符
        y_offset = padding
        for char_images, _, row_h in measured_rows:
            x_offset = label_w + padding
            for char, img in char_images:
                for dy in range(len(img)):
                    for dx in range(len(img[0])):
                        cy = y_offset + dy
                        cx = x_offset + dx
                        if 0 <= cy < total_height and 0 <= cx < total_width:
                            canvas[cy][cx] = img[dy][dx]
                x_offset += len(img[0]) + padding
            y_offset += row_h + padding * 2

        return canvas


def save_bmp(path, pixels, scale=1):
    bmp_data = BMPPixelFont.pixels_to_bmp(
        pixels,
        scale=scale,
        horizontal_padding=HORIZONTAL_PADDING,
    )
    with open(path, 'wb') as f:
        f.write(bmp_data)
    w = len(pixels[0]) * scale + HORIZONTAL_PADDING * 2 if pixels else 0
    h = len(pixels) * scale if pixels else 0
    return w, h


# ============================================================
# 主程序
# ============================================================

def parse_hex_text(hex_strings):
    """将十六进制码点列表转为字符串, 如 ['0391','0398'] -> 'ΑΘ' """
    chars = []
    for h in hex_strings:
        h = h.strip().lstrip('U+').lstrip('u+').lstrip('0x')
        try:
            chars.append(chr(int(h, 16)))
        except ValueError:
            pass
    return ''.join(chars)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    required_font_files = (BMP_FILE, VOWEL_BMP_FILE, VOWEL_MAP_FILE)
    missing = [path for path in required_font_files if not os.path.exists(path)]
    if missing:
        print(f"Error: font file not found: {missing[0]}", file=sys.stderr)
        sys.exit(1)

    font = BMPPixelFont(BMP_FILE, VOWEL_BMP_FILE, VOWEL_MAP_FILE)

    args = sys.argv[1:]
    output = None  # None = 未指定, 稍后确定默认值
    scale = 1
    gap = 2
    line_gap = 2
    max_width = DEFAULT_MAX_WIDTH
    auto_sigma = False
    is_chart = False
    hex_mode = False
    txt_file = None

    i = 0
    text_parts = []
    hex_parts = []
    while i < len(args):
        a = args[i]
        if a == '--chart':
            is_chart = True
            i += 1
        elif a in ('-o', '--output') and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        elif a == '--scale' and i + 1 < len(args):
            scale = int(args[i + 1])
            i += 2
        elif a == '--gap' and i + 1 < len(args):
            gap = int(args[i + 1])
            i += 2
        elif a == '--line-gap' and i + 1 < len(args):
            line_gap = int(args[i + 1])
            i += 2
        elif a == '--max-width' and i + 1 < len(args):
            max_width = int(args[i + 1])
            i += 2
        elif a == '--no-auto-sigma':
            auto_sigma = False
            i += 1
        elif a == '--hex':
            hex_mode = True
            i += 1
            while i < len(args) and not args[i].startswith('-'):
                hex_parts.append(args[i])
                i += 1
        elif a in ('--file',) and i + 1 < len(args):
            txt_file = args[i + 1]
            i += 2
        elif a in ('--help', '-h'):
            print(__doc__)
            return
        else:
            # 检测是否为 .txt 文件
            if a.lower().endswith('.txt') and os.path.exists(a):
                txt_file = a
            elif hex_mode:
                hex_parts.append(a)
            else:
                text_parts.append(a)
            i += 1

    if is_chart:
        out = output or os.path.join(SCRIPT_DIR, 'chart.bmp')
        chart_pixels = font.make_chart_image(scale=2)
        w, h = save_bmp(out, chart_pixels, scale=scale)
        print(f"Chart saved: {out} ({w}x{h})")
        return

    # 读取 .txt 文件
    file_lines = None
    if txt_file:
        with open(txt_file, 'r', encoding='utf-8') as f:
            file_lines = [line.rstrip('\n').rstrip('\r') for line in f.readlines()]
        # 自动输出同名 .bmp
        if output is None:
            base = os.path.splitext(txt_file)[0]
            output = base + '.bmp'

    # 默认输出
    if output is None:
        output = os.path.join(SCRIPT_DIR, 'output.bmp')

    # 组合文本
    if hex_parts:
        text_parts.insert(0, parse_hex_text(hex_parts))

    if file_lines is not None:
        # 多行模式
        lines = file_lines
        if auto_sigma:
            lines = [apply_final_sigma(l) for l in lines]
        pixels = font.render_multiline(lines, gap=gap, line_gap=line_gap, max_width=max_width)
    else:
        text = ' '.join(text_parts)
        if not text:
            if not sys.stdin.isatty():
                text = sys.stdin.read().strip()
            if not text:
                print(__doc__)
                return
        if auto_sigma:
            text = apply_final_sigma(text)
        pixels = font.render_text(text, gap=gap, max_width=max_width, line_gap=line_gap)

    if not pixels:
        print("No renderable characters", file=sys.stderr)
        sys.exit(1)

    w, h = save_bmp(output, pixels, scale=scale)
    print(f"Saved: {output} ({w}x{h})")


if __name__ == '__main__':
    main()
