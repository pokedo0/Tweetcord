import os
import sys
import unittest
from unittest.mock import patch

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.classes import ParsedTweet

class MockTweet:
    def __init__(self, media=None):
        self.media = media or []

class TestParsedTweet(unittest.TestCase):
    def setUp(self):
        # Intercept and simulate the translation function t() to prevent a missing key error from being thrown
        self.patcher = patch('core.classes.t', side_effect=lambda key, **kwargs: f"Mock({key})")
        self.mock_t = self.patcher.start()
        
        # Create a basic ParsedTweet instance using a dict
        self.source_dict = {
            'tweet': {
                'raw_text': {'text': None},
                'author': {'screen_name': 'test_user'},
                'media': {'all': []},
                'translation': {'text': None, 'source_lang': 'en'}
            }
        }
        self.parsed_tweet = ParsedTweet(self.source_dict)
        
    def tearDown(self):
        # Stop interception after the test ends
        self.patcher.stop()

    def test_get_text_priority(self):
        """Test that get_text prioritizes translated text over raw text."""
        self.parsed_tweet.text = "Original Text"
        self.parsed_tweet.trans_text = "Translated Text"
        self.parsed_tweet.trans_lang = "en"
        
        # Should return translated text (which is a formatted string in get_translated_text)
        result, is_simplified = self.parsed_tweet.get_text()
        self.assertIn("Translated Text", result)
        # Confirmed call to Mock translation
        self.assertIn("Mock(class.parsed_tweet.trans_text)", result) 
        self.assertFalse(is_simplified)
        
        # Should return original text if translation is missing
        self.parsed_tweet.trans_text = None
        result, is_simplified = self.parsed_tweet.get_text()
        self.assertEqual(result, "Original Text")
        self.assertFalse(is_simplified)

    def test_get_text_none(self):
        """Test get_text when both text and trans_text are None."""
        self.parsed_tweet.text = None
        self.parsed_tweet.trans_text = None
        self.assertIsNone(self.parsed_tweet.get_text())

    def test_simplified_content_threshold(self):
        """Test that _simplified_content correctly identifies content over threshold."""
        # SIMPLIFIED_THRESHOLD is 400
        # MAX_DESCRIPTION_LENGTH is 650
        # To trigger truncation, we need text visible length > 650
        short_text = "A" * 100
        long_text = "A" * 700
        
        # Short text should not be simplified
        result, is_simplified = self.parsed_tweet._simplified_content(short_text)
        self.assertEqual(result, short_text)
        self.assertFalse(is_simplified)
        
        # Long text should be simplified (is_simplified becomes True if > 400)
        result, is_simplified = self.parsed_tweet._simplified_content(long_text)
        self.assertTrue(is_simplified)
        self.assertTrue(len(result) < len(long_text))
        self.assertTrue(result.endswith("..."))

    def test_get_text_simplified(self):
        """Test get_text with simplified_content=True."""
        long_text = "A" * 700
        self.parsed_tweet.text = long_text
        
        result, is_simplified = self.parsed_tweet.get_text(simplified_content=True)
        self.assertTrue(is_simplified)
        self.assertTrue(len(result) < 700)

    def test_rt_translation_preservation(self):
        """Test that RT information is preserved in trans_text when it's an RT."""
        rt_source_dict = {
            'tweet': {
                'raw_text': {'text': 'Original Text'},
                'author': {'screen_name': 'original_author'},
                'reposted_by': {'screen_name': 'retweeter'},
                'media': {'all': []},
                'translation': {'text': 'Translated Text', 'source_lang': 'en'}
            }
        }
        rt_parsed_tweet = ParsedTweet(rt_source_dict)
        
        # Check if RT prefix is added to both text and trans_text
        self.assertEqual(rt_parsed_tweet.text, "RT @original_author: Original Text")
        self.assertEqual(rt_parsed_tweet.trans_text, "RT @original_author: Translated Text")
        
        # Verify get_text output contains the RT prefix
        result, _ = rt_parsed_tweet.get_text()
        self.assertIn("RT @original_author:", result)
        self.assertIn("Translated Text", result)

    def test_get_quote_text_repro(self):
        """Test get_quote_text with the new simplified logic."""
        self.parsed_tweet.quote.text = "Quote Content"
        self.parsed_tweet.text = "Main Content"
        
        # Test with main text included
        result = self.parsed_tweet.get_quote_text(include_main_text=True)
        # result should be (content, is_simplified)
        self.assertIsInstance(result, tuple)
        content, _ = result
        self.assertIn("Main Content", content)
        self.assertIn("> Quote Content", content)
        self.assertNotIn("('Main Content', False)", content)

    def test_translation_filter_tier1_zh_family(self):
        """Tier 1: source_lang='zh' + target_lang starts with 'zh' -> skip translation."""
        source = {
            'tweet': {
                'raw_text': {'text': '永远支持talk君老师'},
                'author': {'screen_name': 'test_user'},
                'media': {'all': []},
                'translation': {'text': '永远支持talk君老师', 'source_lang': 'zh', 'target_lang': 'zh-cn'}
            }
        }
        pt = ParsedTweet(source)
        self.assertIsNone(pt.trans_text)

        # zh -> zh-tw should also be skipped
        source['tweet']['translation']['target_lang'] = 'zh-tw'
        pt2 = ParsedTweet(source)
        self.assertIsNone(pt2.trans_text)

    def test_translation_filter_tier2_exact_lang_match(self):
        """Tier 2: source_lang exactly matches target_lang -> skip translation."""
        source = {
            'tweet': {
                'raw_text': {'text': 'Hello world'},
                'author': {'screen_name': 'test_user'},
                'media': {'all': []},
                'translation': {'text': 'Hello world', 'source_lang': 'en', 'target_lang': 'en'}
            }
        }
        pt = ParsedTweet(source)
        self.assertIsNone(pt.trans_text)

    def test_translation_filter_tier3_text_identical(self):
        """Tier 3: translated text identical to original -> skip (fallback)."""
        source = {
            'tweet': {
                'raw_text': {'text': 'some text here'},
                'author': {'screen_name': 'test_user'},
                'media': {'all': []},
                'translation': {'text': 'some text here', 'source_lang': 'unknown', 'target_lang': 'ja'}
            }
        }
        pt = ParsedTweet(source)
        self.assertIsNone(pt.trans_text)

    def test_translation_filter_keeps_valid_translation(self):
        """Valid translation (different lang, different text) should be kept."""
        source = {
            'tweet': {
                'raw_text': {'text': 'Hello world'},
                'author': {'screen_name': 'test_user'},
                'media': {'all': []},
                'translation': {'text': '你好世界', 'source_lang': 'en', 'target_lang': 'zh-cn'}
            }
        }
        pt = ParsedTweet(source)
        self.assertEqual(pt.trans_text, '你好世界')

    def test_translation_filter_quote(self):
        """Quote translation should also be filtered by three-tier logic."""
        source = {
            'tweet': {
                'raw_text': {'text': 'Main text'},
                'author': {'screen_name': 'test_user'},
                'media': {'all': []},
                'translation': {'text': '主文本', 'source_lang': 'en', 'target_lang': 'zh-cn'},
                'quote': {
                    'raw_text': {'text': '中文引用内容'},
                    'author': {'name': 'Quoter', 'screen_name': 'quoter', 'url': 'https://x.com/quoter'},
                    'url': 'https://x.com/quoter/status/1',
                    'translation': {'text': '中文引用内容', 'source_lang': 'zh', 'target_lang': 'zh-cn'}
                }
            }
        }
        pt = ParsedTweet(source)
        # Main tweet translation should be kept (en -> zh-cn, different text)
        self.assertEqual(pt.trans_text, '主文本')
        # Quote translation should be skipped (zh -> zh-cn, tier 1)
        self.assertIsNone(pt.quote.trans_text)

if __name__ == '__main__':
    unittest.main()
