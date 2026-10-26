"""Regression checks for request parsing and restricted image decoders."""
import bz2
import io
import json
import zlib
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from .models import KnowledgeEntry, TeamMember
from .uploads import image_content_type


class ImageDecoderTests(SimpleTestCase):
    def image(self, image_format, size=(4, 4)):
        output = io.BytesIO()
        Image.new('RGB', size, color='green').save(output, format=image_format)
        output.seek(0)
        return output

    def test_supported_formats_are_verified(self):
        for suffix, image_format, mime in [('jpg', 'JPEG', 'image/jpeg'), ('png', 'PNG', 'image/png'),
                                           ('gif', 'GIF', 'image/gif'), ('webp', 'WEBP', 'image/webp')]:
            with self.subTest(suffix=suffix):
                self.assertEqual(image_content_type(self.image(image_format), 'tower.'+suffix), mime)

    def test_renamed_unsupported_image_cannot_select_another_decoder(self):
        for image_format in ['TIFF', 'BMP']:
            with self.subTest(image_format=image_format), self.assertRaises(ValidationError):
                image_content_type(self.image(image_format), 'tower.jpg')

    def test_image_signature_must_match_its_filename(self):
        with self.assertRaises(ValidationError):
            image_content_type(self.image('PNG'), 'tower.jpg')

    def test_invalid_images_are_validation_errors(self):
        with self.assertRaises(ValidationError):
            image_content_type(io.BytesIO(b'not an image'), 'tower.png')

    def test_decompression_bomb_warning_is_rejected_before_decode(self):
        source = self.image('PNG')
        with patch.object(Image, 'MAX_IMAGE_PIXELS', 10), self.assertRaises(ValidationError):
            image_content_type(source, 'tower.png')


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RequestParsingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.writer = get_user_model().objects.create_user('parser-writer', password='Local-parser-check-2026')
        TeamMember.objects.create(user=cls.writer, role='member')

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.writer)

    def test_json_charset_cannot_select_a_compression_decoder(self):
        payload = json.dumps({'title': 'Compressed reference', 'category': 'general'}).encode()
        for charset, data in [('bz2_codec', bz2.compress(payload)), ('zlib_codec', zlib.compress(payload))]:
            with self.subTest(charset=charset):
                response = self.client.post('/api/knowledge/', data, content_type='application/json; charset='+charset)
                self.assertEqual(response.status_code, 400)
        self.assertFalse(KnowledgeEntry.objects.exists())

    def test_unknown_charset_is_rejected_without_server_error(self):
        response = self.client.post('/api/knowledge/', b'{}', content_type='application/json; charset=unknown-charset')
        self.assertEqual(response.status_code, 400)

    def test_utf8_json_remains_writable(self):
        response = self.client.post('/api/knowledge/', json.dumps({'title': 'Wiring reference', 'category': 'wiring', 'body': 'Vérification'}).encode(), content_type='application/json; charset=utf-8')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(KnowledgeEntry.objects.get().body, 'Vérification')

    def test_oversized_accept_header_has_bounded_parser_work(self):
        from rest_framework.negotiation import _MediaType
        for media_type, expected_status in [('application/json', 200), ('text/unsupported', 406)]:
            with self.subTest(media_type=media_type), patch('rest_framework.negotiation._MediaType', wraps=_MediaType) as parser:
                response = self.client.get('/api/bootstrap/', HTTP_ACCEPT=(media_type+',')*1000)
                self.assertEqual(response.status_code, expected_status)
                self.assertLessEqual(parser.call_count, 66)

    def test_normal_json_accept_header_still_works(self):
        self.assertEqual(self.client.get('/api/bootstrap/', HTTP_ACCEPT='application/json').status_code, 200)
