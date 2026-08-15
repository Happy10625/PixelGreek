import struct
import unicodedata
import unittest

import pixel_greek


class BMPPixelFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = pixel_greek.BMPPixelFont(pixel_greek.BMP_FILE)
        cls.vowel_chars = [char for row in cls.font.vowel_rows for char in row]

    def test_every_vowel_mapping_has_a_vowel_glyph(self):
        self.assertEqual(len(self.font.vowel_rows), 27)
        self.assertEqual(len(self.vowel_chars), 198)
        self.assertEqual(len(self.vowel_chars), len(set(self.vowel_chars)))
        for char in self.vowel_chars:
            with self.subTest(char=char):
                self.assertIn(char, self.font.char_images)
                self.assertEqual(self.font.glyph_sources[char], 'vowel')
                self.assertEqual(len(self.font.char_images[char]), 19)

    def test_every_basic_alphabet_character_remains_available(self):
        expected = set(pixel_greek.UPPER + pixel_greek.LOWER + [pixel_greek.SIGMA_FINAL])
        self.assertEqual(len(expected), 49)
        self.assertTrue(expected.issubset(self.font.char_images))

    def test_vowel_sheet_overrides_conflicting_basic_letters(self):
        for char in 'αεηιουω':
            with self.subTest(char=char):
                self.assertEqual(self.font.glyph_sources[char], 'vowel')
        self.assertEqual(self.font.glyph_sources['β'], 'alphabet')

    def test_documented_glyph_widths(self):
        expected_widths = {
            'ά': 7,
            'ἔ': 6,
            'ἴ': 6,
            'ὔ': 7,
            '·': 4,
            'Ἀ': 13,
            'Ἰ': 9,
        }
        for char, width in expected_widths.items():
            with self.subTest(char=char):
                self.assertEqual(len(self.font.get_char(char)[0]), width)

    def test_punctuation_widths_and_unknown_fallback(self):
        for char in ',.·;᾿῾´`!':
            with self.subTest(char=char):
                self.assertEqual(len(self.font.get_char(char)[0]), 4)
        self.assertEqual(len(self.font.get_char('῀')[0]), 7)

        ordinary_exclamation = self.font.get_char('!')
        unknown = self.font.get_char('☃')
        self.assertEqual(len(unknown[0]), 7)
        self.assertEqual(len(unknown), len(ordinary_exclamation))
        for unknown_row, exclamation_row in zip(unknown, ordinary_exclamation):
            self.assertEqual(unknown_row[:4], exclamation_row)
            self.assertEqual(unknown_row[4:], [1, 1, 1])

    def test_uppercase_vowels_are_cut_at_eighteen_pixel_intervals(self):
        raw_sheet = pixel_greek.BMPPixelFont(
            pixel_greek.VOWEL_BMP_FILE,
            vowel_bmp_path=None,
            vowel_map_path=None,
        )
        second_upper_x = pixel_greek.VOWEL_X + pixel_greek.VOWEL_UPPER_X_STEP
        expected = raw_sheet._extract_region(
            second_upper_x,
            pixel_greek.VOWEL_UPPER_Y,
            second_upper_x + 12,
            pixel_greek.VOWEL_UPPER_Y + pixel_greek.VOWEL_ROW_HEIGHT - 1,
        )
        self.assertEqual(self.font.get_char('Ἄ'), expected)
        self.assertEqual(pixel_greek.VOWEL_UPPER_X_STEP, 18)
        self.assertEqual(pixel_greek.VOWEL_LOWER_X_STEP, 12)

    def test_decomposed_polytonic_text_is_normalized(self):
        decomposed = unicodedata.normalize('NFD', 'ἄ')
        self.assertEqual(self.font._text_mats(decomposed), [self.font.get_char('ἄ')])

    def test_only_leading_spaces_before_uppercase_use_five_pixels(self):
        self.assertEqual(len(self.font._text_mats(' Ἀ')[0][0]), 5)
        self.assertEqual(len(self.font._text_mats(' ἀ')[0][0]), 7)
        self.assertEqual(len(self.font._text_mats('ἀ Ἀ')[1][0]), 7)

    def test_bmp_has_three_final_pixel_white_borders(self):
        bmp = self.font.pixels_to_bmp(
            [[0]],
            scale=2,
            horizontal_padding=pixel_greek.HORIZONTAL_PADDING,
        )
        self.assertEqual(struct.unpack_from('<i', bmp, 18)[0], 8)
        row = bmp[54:78]
        colors = [tuple(row[x:x + 3]) for x in range(0, 24, 3)]
        self.assertEqual(colors, [(255, 255, 255)] * 3 + [(0, 0, 0)] * 2 + [(255, 255, 255)] * 3)


if __name__ == '__main__':
    unittest.main()
