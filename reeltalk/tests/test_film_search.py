"""test searching for films"""

from django.db.models import Q
from django.test import TestCase

from reeltalk import book_search, models


class FilmSearch(TestCase):
    """look for some films"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""
        cls.first_film = models.Film.objects.create(
            title="Example Film",
            year=2019,
            directors=["Mary Smith"],
            tmdb_id="12345",
        )
        cls.second_film = models.Film.objects.create(
            title="Another Film",
            imdb_id="tt0000001",
            cast=["John Doe"],
        )
        cls.third_film = models.Film.objects.create(
            title="Annoying Film",
            genres=["Drama"],
        )

    def test_search(self):
        """search for a film in the db"""
        # title
        results = book_search.search("Example")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.first_film)

        # director
        results = book_search.search("Mary")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.first_film)

        # cast
        results = book_search.search("John")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.second_film)

        # genre
        results = book_search.search("Drama")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.third_film)

        # tmdb id
        results = book_search.search("12345")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.first_film)

        # imdb id
        results = book_search.search("tt0000001")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.second_film)

    def test_search_empty(self):
        """an empty query returns no results"""
        self.assertEqual(book_search.search(""), [])
        self.assertIsNone(book_search.search("", return_first=True))

    def test_search_return_first(self):
        """return the first match instead of a queryset"""
        result = book_search.search("Example", return_first=True)
        self.assertEqual(result, self.first_film)

    def test_search_with_filters(self):
        """extra filters narrow the results"""
        # all three titles contain "Film"; the filter picks one out
        results = book_search.search("Film", filters=[Q(year=2019)])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.first_film)

        results = book_search.search(
            "Film", filters=[Q(genres__contains=["Drama"])]
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.third_film)

    def test_search_identifiers(self):
        """search by unique identifiers"""
        results = book_search.search_identifiers("12345")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.first_film)

        results = book_search.search_identifiers("tt0000001")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.second_film)

        # no identifier match: None, not an empty queryset
        self.assertIsNone(book_search.search_identifiers("nope"))

    def test_search_identifiers_return_first(self):
        """search by unique identifiers"""
        result = book_search.search_identifiers("12345", return_first=True)
        self.assertEqual(result, self.first_film)

    def test_search_title(self):
        """full text search over title, subtitle, names and genres"""
        results = book_search.search_title("Example", min_confidence=0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.first_film)

        # every title contains the word "Film"
        results = book_search.search_title("Film", min_confidence=0)
        self.assertEqual(len(results), 3)
        self.assertCountEqual(
            results, [self.first_film, self.second_film, self.third_film]
        )

    def test_search_title_return_first(self):
        """sorts by rank"""
        result = book_search.search_title("Example", min_confidence=0, return_first=True)
        self.assertEqual(result, self.first_film)

    def test_format_search_result(self):
        """format a search result"""
        self.first_film.refresh_from_db()
        result = book_search.format_search_result(self.first_film)
        self.assertEqual(result["title"], "Example Film")
        self.assertEqual(result["key"], self.first_film.remote_id)
        self.assertIn("/film/", result["key"])
        self.assertEqual(result["director"], "Mary Smith")
        self.assertEqual(result["year"], "2019")
        self.assertIsNone(result["cover"])

        self.third_film.refresh_from_db()
        result = book_search.format_search_result(self.third_film)
        self.assertEqual(result["title"], "Annoying Film")
        self.assertIsNone(result["director"])
        self.assertIsNone(result["year"])

    def test_search_result(self):
        """a class that stores info about a search result"""
        # there's really not much to test here, it's just a dataclass
        result = book_search.SearchResult(
            title="Title",
            key="https://example.com/film/1",
            director="Director Name",
            year="1850",
        )
        self.assertEqual(result.confidence, 1)
        self.assertEqual(result.title, "Title")
        self.assertIsNone(result.view_link)
        self.assertIsNone(result.cover)
        self.assertEqual(
            result.json(),
            {
                "title": "Title",
                "key": "https://example.com/film/1",
                "view_link": None,
                "director": "Director Name",
                "year": "1850",
                "cover": None,
                "confidence": 1,
            },
        )


class SearchVectorTest(TestCase):
    """check search_vector is computed correctly"""

    def test_search_vector_simple(self):
        """simplest search vector"""
        film = self._create_film("Film", directors=["Mary"])
        self.assertEqual(film.search_vector, "'film':1A 'mary':2C")  # A > C (priority)

    def test_search_vector_all_parts(self):
        """search vector with subtitle, names and genres"""
        film = self._create_film(
            "Film",
            subtitle="Long",
            directors=["Mary"],
            cast=["John"],
            genres=["Drama"],
        )
        self.assertEqual(
            film.search_vector,
            "'drama':5 'film':1A 'john':4C 'long':2B 'mary':3C",
        )

    def test_search_vector_parse_title(self):
        """title is parsed in english"""
        film = self._create_film("Writing")
        self.assertEqual(film.search_vector, "'write':1A")

    def test_search_vector_parse_names(self):
        """names are not stem'd or affected by stop words"""
        film = self._create_film("Writing", directors=["Writes"], cast=["Reads"])
        self.assertEqual(film.search_vector, "'reads':3C 'write':1A 'writes':2C")

    def test_search_vector_parse_title_empty(self):
        """empty parse in English retried as simple title"""
        film = self._create_film("Here We", directors=["John"])
        self.assertEqual(film.search_vector, "'here':1A 'john':3C 'we':2A")

        film = self._create_film("there there")
        self.assertEqual(film.search_vector, "'there':1A,2A")

    def test_search_vector_no_names(self):
        """film with no names gets processed normally"""
        film = self._create_film("Film", genres=["Drama"])
        self.assertEqual(film.search_vector, "'drama':2 'film':1A")

    # n.b.: the following originally from test_posgres.py

    def test_search_vector_on_update(self):
        """make sure that search_vector is being set correctly on edit"""
        film = self._create_film("The Long Goodbye")
        self.assertEqual(film.search_vector, "'goodby':3A 'long':2A")

        film.title = "The Even Longer Goodbye"
        film.save(broadcast=False)
        film.refresh_from_db()
        self.assertEqual(film.search_vector, "'even':2A 'goodby':4A 'longer':3A")

    def test_search_vector_on_director_update(self):
        """update search when a director name changes"""
        film = self._create_film("The Long Goodbye", directors=["The Rays"])
        self.assertEqual(
            film.search_vector, "'goodby':3A 'long':2A 'rays':5C 'the':4C"
        )

        film.directors = ["Jeremy"]
        film.save(broadcast=False)
        film.refresh_from_db()
        self.assertEqual(film.search_vector, "'goodby':3A 'jeremy':4C 'long':2A")

    def test_search_vector_on_director_delete(self):
        """update search when a director is removed"""
        film = self._create_film("The Long Goodbye", directors=["The Rays"])
        self.assertEqual(
            film.search_vector, "'goodby':3A 'long':2A 'rays':5C 'the':4C"
        )

        film.directors = []
        film.save(broadcast=False)
        film.refresh_from_db()
        self.assertEqual(film.search_vector, "'goodby':3A 'long':2A")

    @staticmethod
    def _create_film(title, /, *, subtitle=None, directors=None, cast=None, genres=None):
        """quickly create a film"""
        film = models.Film.objects.create(
            title=title,
            subtitle=subtitle,
            directors=directors or [],
            cast=cast or [],
            genres=genres or [],
        )
        film.refresh_from_db()
        return film


class SearchVectorUpdates(TestCase):
    """look for films as they change"""  # functional tests of the above

    def setUp(self):
        """we need basic test data and mocks"""
        self.film = models.Film.objects.create(
            title="First Film of Work",
            subtitle="Some Extra Words Are Good",
            directors=["Name"],
            cast=["Alias"],
        )
        self.film.refresh_from_db()

    def test_search_after_changed_metadata(self):
        """film found after updating metadata"""
        self.assertEqual(self.film, self._search_first("First"))  # title
        self.assertEqual(self.film, self._search_first("Good"))  # subtitle
        self.assertEqual(self.film, self._search_first("Name"))  # director
        self.assertEqual(self.film, self._search_first("Alias"))  # cast

        self.film.title = "Second Film of Work"
        self.film.subtitle = "Fewer Words Are Better"
        self.film.genres = ["Wondrous Bunch"]
        self.film.save(broadcast=False)

        self.assertEqual(self.film, self._search_first("Second"))  # title new
        self.assertEqual(self.film, self._search_first("Fewer"))  # subtitle new
        self.assertEqual(self.film, self._search_first("Wondrous"))  # genre new

        self.assertFalse(self._search_first("First"))  # title old
        self.assertFalse(self._search_first("Good"))  # subtitle old
        self.assertFalse(self._search_first("Some"))  # subtitle old

    def test_search_after_director_remove(self):
        """film not found via removed director"""
        self.assertEqual(self.film, self._search_first("Name"))

        self.film.directors = []
        self.film.save(broadcast=False)

        self.assertFalse(self._search("Name"))
        self.assertEqual(self.film, self._search_first("Film"))

    def test_search_after_director_add(self):
        """film found by newly-added director"""
        self.assertFalse(self._search("Mozilla"))

        self.film.directors = ["Name", "Mozilla"]
        self.film.save(broadcast=False)

        self.assertEqual(self.film, self._search_first("Mozilla"))
        self.assertEqual(self.film, self._search_first("Name"))

    def test_search_after_updated_director_name(self):
        """film found under new director name"""
        self.assertEqual(self.film, self._search_first("Name"))
        self.assertEqual(self.film, self._search_first("Alias"))
        self.assertFalse(self._search("Identifier"))
        self.assertFalse(self._search("Another"))

        self.film.directors = ["Identifier"]
        self.film.cast = ["Another"]
        self.film.save(broadcast=False)

        self.assertFalse(self._search("Name"))
        self.assertEqual(self.film, self._search_first("Identifier"))
        self.assertEqual(self.film, self._search_first("Another"))
        self.assertEqual(self.film, self._search_first("Work"))

    def _search_first(self, query):
        """wrapper around search"""
        return self._search(query, return_first=True)

    @staticmethod
    def _search(query, *, return_first=False):
        """wrapper around search"""
        return book_search.search(
            query, min_confidence=0, return_first=return_first
        )
