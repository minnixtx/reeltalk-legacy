"""Replace the book domain (Book/Work/Edition/Author + import machinery) with
a flat Film model, migrating existing data over: one film per work (reusing
the default edition's id so /book/<id> links keep working as /film/<id>),
statuses/shelves/lists re-pointed at the films.

Irreversible: the book tables and their data are dropped.
"""

import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
import pgtrigger.compiler
import pgtrigger.migrations
import reeltalk.models.activitypub_mixin
import reeltalk.models.fields
from django.conf import settings
from django.db import migrations, models
from reeltalk.settings import BASE_URL


def create_films_from_books(apps, schema_editor):
    """Create films from works/editions and repoint all book-domain foreign
    keys at them in place. Builds a scratch mapping table used by
    copy_m2m_rows."""

    with schema_editor.connection.cursor() as cursor:
        # Scratch mapping: every work/edition -> the film it became
        cursor.execute(
            """
            CREATE TEMP TABLE reeltalk_film_migration_map (
                work_id integer,
                edition_id integer,
                film_id integer NOT NULL
            )
            """
        )

        # Orphaned editions (no parent work) become films with their own id
        cursor.execute(
            """
            INSERT INTO reeltalk_film (
                id, created_date, updated_date, remote_id, title, sort_title,
                subtitle, description, year, runtime, genres, directors, "cast",
                poster, origin_id, tmdb_id, imdb_id, search_vector,
                last_edited_by_id
            )
            SELECT
                ed.book_ptr_id,
                b.created_date,
                now(),
                NULL,
                b.title,
                lower(regexp_replace(b.title, '^(the|a|an) ', '')),
                b.subtitle,
                b.description,
                EXTRACT(YEAR FROM COALESCE(
                    b.published_date, b.first_published_date))::integer,
                NULL,
                '{}', '{}', '{}',
                b.cover,
                b.origin_id,
                NULL, NULL, NULL,
                b.last_edited_by_id
            FROM reeltalk_edition ed
            JOIN reeltalk_book b ON b.id = ed.book_ptr_id
            WHERE ed.parent_work_id IS NULL
            """
        )
        cursor.execute(
            """
            INSERT INTO reeltalk_film_migration_map (work_id, edition_id, film_id)
            SELECT NULL, ed.book_ptr_id, ed.book_ptr_id
            FROM reeltalk_edition ed
            WHERE ed.parent_work_id IS NULL
            """
        )

        # One film per work. The film reuses the default edition's id so old
        # /book/<edition-id> links keep working as /film/<id>; childless works
        # fall back to the work's own id, or a fresh sequence id if that
        # collides with an orphaned-edition film.
        cursor.execute(
            """
            CREATE TEMP TABLE film_plan AS
            SELECT
                w.book_ptr_id AS work_id,
                COALESCE(de.edition_id, w.book_ptr_id) AS preferred_film_id
            FROM reeltalk_work w
            LEFT JOIN (
                SELECT DISTINCT ON (parent_work_id) parent_work_id, book_ptr_id AS edition_id
                FROM reeltalk_edition
                WHERE parent_work_id IS NOT NULL
                ORDER BY parent_work_id, edition_rank DESC NULLS LAST, book_ptr_id ASC
            ) de ON de.parent_work_id = w.book_ptr_id
            """
        )
        cursor.execute(
            """
            UPDATE film_plan
            SET preferred_film_id = nextval('reeltalk_film_id_seq')
            WHERE preferred_film_id IN (SELECT id FROM reeltalk_film)
            """
        )
        cursor.execute(
            """
            INSERT INTO reeltalk_film (
                id, created_date, updated_date, remote_id, title, sort_title,
                subtitle, description, year, runtime, genres, directors, "cast",
                poster, origin_id, tmdb_id, imdb_id, search_vector,
                last_edited_by_id
            )
            SELECT
                p.preferred_film_id,
                wb.created_date,
                now(),
                NULL,
                COALESCE(NULLIF(deb.title, ''), wb.title),
                lower(regexp_replace(
                    COALESCE(NULLIF(deb.title, ''), wb.title), '^(the|a|an) ', '')),
                COALESCE(deb.subtitle, wb.subtitle),
                COALESCE(NULLIF(deb.description, ''), wb.description),
                EXTRACT(YEAR FROM COALESCE(
                    deb.published_date, deb.first_published_date,
                    wb.first_published_date))::integer,
                NULL,
                COALESCE(wb.subjects, '{}'),
                '{}', '{}',
                deb.cover,
                COALESCE(deb.origin_id, wb.origin_id),
                NULL, NULL, NULL,
                COALESCE(deb.last_edited_by_id, wb.last_edited_by_id)
            FROM film_plan p
            JOIN reeltalk_work w ON w.book_ptr_id = p.work_id
            JOIN reeltalk_book wb ON wb.id = w.book_ptr_id
            LEFT JOIN (
                SELECT DISTINCT ON (e.parent_work_id) e.book_ptr_id, e.parent_work_id
                FROM reeltalk_edition e
                WHERE e.parent_work_id IS NOT NULL
                ORDER BY e.parent_work_id, e.edition_rank DESC NULLS LAST, e.book_ptr_id ASC
            ) de ON de.parent_work_id = w.book_ptr_id
            LEFT JOIN reeltalk_book deb ON deb.id = de.book_ptr_id
            """
        )

        # Map works and their editions to the films they became
        cursor.execute(
            """
            INSERT INTO reeltalk_film_migration_map (work_id, edition_id, film_id)
            SELECT work_id, NULL, preferred_film_id FROM film_plan
            """
        )
        cursor.execute(
            """
            INSERT INTO reeltalk_film_migration_map (work_id, edition_id, film_id)
            SELECT p.work_id, ed.book_ptr_id, p.preferred_film_id
            FROM film_plan p
            JOIN reeltalk_edition ed ON ed.parent_work_id = p.work_id
            """
        )

        # Deduplicate rows that will collide once editions of the same work
        # become one film: a film can only be on a shelf or in a list once.
        cursor.execute(
            """
            DELETE FROM reeltalk_shelfbook s
            USING reeltalk_film_migration_map m1, reeltalk_film_migration_map m2,
                  reeltalk_shelfbook s2
            WHERE s.book_id = m1.edition_id
              AND s2.book_id = m2.edition_id
              AND m1.film_id = m2.film_id
              AND s.shelf_id = s2.shelf_id
              AND s.id > s2.id
            """
        )
        cursor.execute(
            """
            DELETE FROM reeltalk_listitem l
            USING reeltalk_film_migration_map m1, reeltalk_film_migration_map m2,
                  reeltalk_listitem l2
            WHERE l.edition_id = m1.edition_id
              AND l2.edition_id = m2.edition_id
              AND m1.film_id = m2.film_id
              AND l.book_list_id = l2.book_list_id
              AND (l2."order" < l."order" OR (l2."order" = l."order" AND l2.id < l.id))
            """
        )

        # Repoint book-domain foreign keys at the new films in place. The new
        # values are always ids that still exist in reeltalk_edition (default
        # or orphaned edition ids), so the old FK constraints stay satisfied
        # until the columns are renamed and retargeted below.
        for table, column in (
            ("reeltalk_shelfbook", "book_id"),
            ("reeltalk_listitem", "edition_id"),
            ("reeltalk_comment", "book_id"),
            ("reeltalk_review", "book_id"),
            ("reeltalk_quotation", "book_id"),
        ):
            cursor.execute(
                f"""
                UPDATE {table} t
                SET {column} = m.film_id
                FROM reeltalk_film_migration_map m
                WHERE t.{column} = m.edition_id
                """
            )

        # Fill in remote_id (normally set by a post_save signal that does not
        # run for data migrations)
        cursor.execute(
            "UPDATE reeltalk_film SET remote_id = %s || id::text WHERE remote_id IS NULL",
            [f"{BASE_URL}/film/"],
        )


def copy_m2m_rows(apps, schema_editor):
    """Re-point status mentions and user blocked lists onto the films via the
    scratch mapping table, then drop the table."""

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO reeltalk_status_mention_films (status_id, film_id)
            SELECT DISTINCT s.status_id, m.film_id
            FROM reeltalk_status_mention_books s
            JOIN reeltalk_film_migration_map m ON s.edition_id = m.edition_id
            """
        )
        cursor.execute(
            """
            INSERT INTO reeltalk_user_blocked_films (user_id, film_id)
            SELECT DISTINCT b.user_id, m.film_id
            FROM reeltalk_user_blocked_books b
            JOIN reeltalk_film_migration_map m
                ON b.work_id = m.work_id AND m.edition_id IS NULL
            """
        )
        cursor.execute("DROP TABLE reeltalk_film_migration_map")


class Migration(migrations.Migration):

    dependencies = [
        ('reeltalk', '0246_film_default_shelves'),
    ]

    operations = [
        # --- new film models -------------------------------------------------
        migrations.CreateModel(
            name='Film',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('remote_id', reeltalk.models.fields.RemoteIdField(max_length=255, null=True, validators=[reeltalk.models.fields.validate_remote_id])),
                ('title', reeltalk.models.fields.TextField(max_length=255)),
                ('sort_title', reeltalk.models.fields.CharField(blank=True, max_length=255, null=True)),
                ('subtitle', reeltalk.models.fields.TextField(blank=True, max_length=255, null=True)),
                ('description', reeltalk.models.fields.HtmlField(blank=True, null=True)),
                ('year', reeltalk.models.fields.IntegerField(blank=True, null=True)),
                ('runtime', reeltalk.models.fields.IntegerField(blank=True, null=True)),
                ('genres', reeltalk.models.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('directors', reeltalk.models.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('cast', reeltalk.models.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None)),
                ('poster', reeltalk.models.fields.ImageField(blank=True, null=True, upload_to='posters/')),
                ('origin_id', models.CharField(blank=True, max_length=255, null=True)),
                ('tmdb_id', reeltalk.models.fields.CharField(blank=True, max_length=255, null=True)),
                ('imdb_id', reeltalk.models.fields.CharField(blank=True, max_length=255, null=True)),
                ('search_vector', django.contrib.postgres.search.SearchVectorField(null=True)),
                ('last_edited_by', reeltalk.models.fields.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            bases=(reeltalk.models.activitypub_mixin.ObjectMixin, models.Model),
        ),
        migrations.CreateModel(
            name='MergedFilm',
            fields=[
                ('deleted_id', models.IntegerField(primary_key=True, serialize=False)),
                ('merged_into', reeltalk.models.fields.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='absorbed', to='reeltalk.film')),
            ],
        ),
        migrations.AddIndex(
            model_name='film',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='reeltalk_fi_search__59400e_gin'),
        ),
        migrations.AddIndex(
            model_name='film',
            index=django.contrib.postgres.indexes.BloomIndex(fields=['origin_id', 'remote_id', 'tmdb_id', 'imdb_id'], name='reeltalk_fi_origin__b876c1_bloom'),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='film',
            trigger=pgtrigger.compiler.Trigger(name='update_search_vector_on_film_edit', sql=pgtrigger.compiler.UpsertTriggerSql(func='\n                    SELECT\n                        -- title, with priority A (parse in English, default to simple if empty)\n                        setweight(COALESCE(nullif(\n                            to_tsvector(\'english\', new.title), \'\'),\n                            to_tsvector(\'simple\', new.title)), \'A\') ||\n\n                        -- subtitle, with priority B\n                        setweight(to_tsvector(\'english\', COALESCE(new.subtitle, \'\')), \'B\') ||\n\n                        -- directors and cast names, with priority C\n                        setweight(to_tsvector(\'simple\', COALESCE(\n                            array_to_string(COALESCE(new.directors, \'{}\'), \' \') || \' \' ||\n                            array_to_string(COALESCE(new."cast", \'{}\'), \' \'), \'\')), \'C\') ||\n\n                        -- genres, with lowest priority D\n                        setweight(to_tsvector(\'english\', COALESCE(\n                            array_to_string(COALESCE(new.genres, \'{}\'), \' \'), \'\')), \'D\')\n\n                        INTO new.search_vector;\n                    RETURN new;\n                ', hash='989ab29528090eb8bd6d6496bd4f846d8008fe11', operation='INSERT OR UPDATE OF "title", "subtitle", "directors", "cast", "genres", "search_vector"', pgid='pgtrigger_update_search_vector_on_film_edit_e5c11', table='reeltalk_film', when='BEFORE')),
        ),
        # --- data: create films and repoint book-domain FKs in place ---------
        migrations.RunPython(
            create_films_from_books,
            reverse_code=migrations.RunPython.noop,
        ),
        # --- rename book-domain columns and retarget their FKs ---------------
        migrations.RenameModel(
            old_name="ShelfBook",
            new_name="ShelfFilm",
        ),
        migrations.RenameField(
            model_name='shelffilm',
            old_name='book',
            new_name='film',
        ),
        migrations.AlterField(
            model_name='shelffilm',
            name='film',
            field=reeltalk.models.fields.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reeltalk.film'),
        ),
        migrations.RenameField(
            model_name='listitem',
            old_name='edition',
            new_name='film',
        ),
        migrations.RenameField(
            model_name='listitem',
            old_name='book_list',
            new_name='film_list',
        ),
        migrations.AlterField(
            model_name='listitem',
            name='film',
            field=reeltalk.models.fields.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reeltalk.film'),
        ),
        migrations.RenameField(
            model_name='comment',
            old_name='book',
            new_name='film',
        ),
        migrations.AlterField(
            model_name='comment',
            name='film',
            field=reeltalk.models.fields.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reeltalk.film'),
        ),
        migrations.RenameField(
            model_name='review',
            old_name='book',
            new_name='film',
        ),
        migrations.AlterField(
            model_name='review',
            name='film',
            field=reeltalk.models.fields.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reeltalk.film'),
        ),
        migrations.RenameField(
            model_name='quotation',
            old_name='book',
            new_name='film',
        ),
        migrations.AlterField(
            model_name='quotation',
            name='film',
            field=reeltalk.models.fields.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reeltalk.film'),
        ),
        # --- M2M re-pointing ---------------------------------------------------
        migrations.AddField(
            model_name='status',
            name='mention_films',
            field=reeltalk.models.fields.TagField(related_name='mention_film', to='reeltalk.film'),
        ),
        migrations.AddField(
            model_name='user',
            name='blocked_films',
            field=models.ManyToManyField(related_name='blocked_by', to='reeltalk.film'),
        ),
        migrations.RunPython(
            copy_m2m_rows,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='status',
            name='mention_books',
        ),
        migrations.RemoveField(
            model_name='user',
            name='blocked_books',
        ),
        # --- List/Shelf M2M target change (state-only, explicit through) ------
        migrations.RemoveField(
            model_name='list',
            name='editions',
        ),
        migrations.AddField(
            model_name='list',
            name='films',
            field=models.ManyToManyField(through='reeltalk.ListItem', through_fields=('film_list', 'film'), to='reeltalk.film'),
        ),
        migrations.RemoveField(
            model_name='shelf',
            name='books',
        ),
        migrations.AddField(
            model_name='shelf',
            name='films',
            field=models.ManyToManyField(through='reeltalk.ShelfFilm', through_fields=('shelf', 'film'), to='reeltalk.film'),
        ),
        # --- field removals on surviving models --------------------------------
        migrations.RemoveField(
            model_name='comment',
            name='progress',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='progress_mode',
        ),
        migrations.RemoveField(
            model_name='quotation',
            name='position',
        ),
        migrations.RemoveField(
            model_name='quotation',
            name='endposition',
        ),
        migrations.RemoveField(
            model_name='quotation',
            name='position_mode',
        ),
        migrations.RemoveField(
            model_name='notification',
            name='related_import',
        ),
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('FAVORITE', 'Favorite'), ('BOOST', 'Boost'), ('REPLY', 'Reply'), ('MENTION', 'Mention'), ('TAG', 'Tag'), ('FOLLOW', 'Follow'), ('FOLLOW_REQUEST', 'Follow Request'), ('USER_EXPORT', 'User Export'), ('ADD', 'Add'), ('REPORT', 'Report'), ('LINK_DOMAIN', 'Link Domain'), ('INVITE_REQUEST', 'Invite Request'), ('INVITE', 'Invite'), ('ACCEPT', 'Accept'), ('JOIN', 'Join'), ('LEAVE', 'Leave'), ('REMOVE', 'Remove'), ('GROUP_PRIVACY', 'Group Privacy'), ('GROUP_NAME', 'Group Name'), ('GROUP_DESCRIPTION', 'Group Description'), ('MOVE', 'Move')], max_length=255),
        ),
        # --- drop auto M2M through tables of doomed models ---------------------
        migrations.RemoveField(
            model_name='book',
            name='authors',
        ),
        migrations.RemoveField(
            model_name='edition',
            name='shelves',
        ),
        migrations.RemoveField(
            model_name='findmissingcoversjob',
            name='editions',
        ),
        migrations.RemoveField(
            model_name='findmissingcoversjob',
            name='found_covers',
        ),
        migrations.RemoveField(
            model_name='suggestionlist',
            name='works',
        ),
        migrations.RemoveField(
            model_name='suggestionlistitem',
            name='endorsement',
        ),
        # --- delete old book-domain models (children before parents) -----------
        migrations.DeleteModel(
            name='UserImportBook',
        ),
        migrations.DeleteModel(
            name='UserImportPost',
        ),
        migrations.DeleteModel(
            name='UserImportRelationship',
        ),
        migrations.DeleteModel(
            name='ReeltalkImportJob',
        ),
        migrations.DeleteModel(
            name='ImportItem',
        ),
        migrations.DeleteModel(
            name='ImportJob',
        ),
        migrations.DeleteModel(
            name='ProgressUpdate',
        ),
        migrations.DeleteModel(
            name='ReadThrough',
        ),
        migrations.DeleteModel(
            name='FileLink',
        ),
        migrations.DeleteModel(
            name='FindMissingCoversJob',
        ),
        migrations.DeleteModel(
            name='SeriesBook',
        ),
        migrations.DeleteModel(
            name='SuggestionListItem',
        ),
        migrations.DeleteModel(
            name='SuggestionList',
        ),
        migrations.DeleteModel(
            name='MergedSeries',
        ),
        migrations.DeleteModel(
            name='Series',
        ),
        migrations.DeleteModel(
            name='Edition',
        ),
        migrations.DeleteModel(
            name='Work',
        ),
        migrations.DeleteModel(
            name='MergedBook',
        ),
        migrations.DeleteModel(
            name='Book',
        ),
        migrations.DeleteModel(
            name='MergedAuthor',
        ),
        migrations.DeleteModel(
            name='Author',
        ),
    ]
