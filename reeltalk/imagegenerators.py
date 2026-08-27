"""Generators for all the different thumbnail sizes"""

from imagekit import ImageSpec, register
from imagekit.processors import ResizeToFit


class FilmXSmallWebp(ImageSpec):
    """Handles XSmall size in Webp format"""

    processors = [ResizeToFit(80, 80)]
    format = "WEBP"
    options = {"quality": 95}


class FilmXSmallJpg(ImageSpec):
    """Handles XSmall size in Jpeg format"""

    processors = [ResizeToFit(80, 80)]
    format = "JPEG"
    options = {"quality": 95}


class FilmSmallWebp(ImageSpec):
    """Handles Small size in Webp format"""

    processors = [ResizeToFit(100, 100)]
    format = "WEBP"
    options = {"quality": 95}


class FilmSmallJpg(ImageSpec):
    """Handles Small size in Jpeg format"""

    processors = [ResizeToFit(100, 100)]
    format = "JPEG"
    options = {"quality": 95}


class FilmMediumWebp(ImageSpec):
    """Handles Medium size in Webp format"""

    processors = [ResizeToFit(150, 150)]
    format = "WEBP"
    options = {"quality": 95}


class FilmMediumJpg(ImageSpec):
    """Handles Medium size in Jpeg format"""

    processors = [ResizeToFit(150, 150)]
    format = "JPEG"
    options = {"quality": 95}


class FilmLargeWebp(ImageSpec):
    """Handles Large size in Webp format"""

    processors = [ResizeToFit(200, 200)]
    format = "WEBP"
    options = {"quality": 95}


class FilmLargeJpg(ImageSpec):
    """Handles Large size in Jpeg format"""

    processors = [ResizeToFit(200, 200)]
    format = "JPEG"
    options = {"quality": 95}


class FilmXLargeWebp(ImageSpec):
    """Handles XLarge size in Webp format"""

    processors = [ResizeToFit(250, 250)]
    format = "WEBP"
    options = {"quality": 95}


class FilmXLargeJpg(ImageSpec):
    """Handles XLarge size in Jpeg format"""

    processors = [ResizeToFit(250, 250)]
    format = "JPEG"
    options = {"quality": 95}


class FilmXxLargeWebp(ImageSpec):
    """Handles XxLarge size in Webp format"""

    processors = [ResizeToFit(500, 500)]
    format = "WEBP"
    options = {"quality": 95}


class FilmXxLargeJpg(ImageSpec):
    """Handles XxLarge size in Jpeg format"""

    processors = [ResizeToFit(500, 500)]
    format = "JPEG"
    options = {"quality": 95}


register.generator("film:xsmall:webp", FilmXSmallWebp)
register.generator("film:xsmall:jpg", FilmXSmallJpg)
register.generator("film:small:webp", FilmSmallWebp)
register.generator("film:small:jpg", FilmSmallJpg)
register.generator("film:medium:webp", FilmMediumWebp)
register.generator("film:medium:jpg", FilmMediumJpg)
register.generator("film:large:webp", FilmLargeWebp)
register.generator("film:large:jpg", FilmLargeJpg)
register.generator("film:xlarge:webp", FilmXLargeWebp)
register.generator("film:xlarge:jpg", FilmXLargeJpg)
register.generator("film:xxlarge:webp", FilmXxLargeWebp)
register.generator("film:xxlarge:jpg", FilmXxLargeJpg)
