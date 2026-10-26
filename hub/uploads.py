"""Validate only the raster image formats accepted by the workspace."""
import warnings
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

IMAGE_FORMATS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.gif': 'GIF', '.webp': 'WEBP'}
IMAGE_TYPES = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'GIF': 'image/gif', 'WEBP': 'image/webp'}


def image_content_type(source, filename):
    """Check the file signature with its declared decoder and reject oversized images."""
    image_format = IMAGE_FORMATS.get(Path(filename).suffix.lower())
    if not image_format:
        raise ValidationError('Use a JPEG, PNG, GIF or WebP image.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(source, formats=[image_format]) as image:
                image.verify()
                return IMAGE_TYPES[image.format]
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError('The selected image is invalid, too large or does not match its filename.')
