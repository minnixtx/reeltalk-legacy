"""Generate preview images"""

from django.core.management.base import BaseCommand

from reeltalk import models, preview_images


class Command(BaseCommand):
    """Creates previews for existing objects"""

    help = "Generate preview images"

    def add_arguments(self, parser):
        """options for how the command is run"""
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            help="Generates images for ALL types: site, users and books. Can use a lot of computing power.",
        )

    def handle(self, *args, **options):
        """generate preview images"""
        self.stdout.write(
            "   | Hello! I will be generating preview images for your instance."
        )
        if options["all"]:
            self.stdout.write(
                "🧑‍🎨 ⎨ This might take quite long if your instance has a lot of books and users."
            )
            self.stdout.write("   | ✧ Thank you for your patience ✧")
        else:
            self.stdout.write("🧑‍🎨 ⎨ I will only generate the instance preview image.")
            self.stdout.write("   | ✧ Be right back! ✧")

        # Site
        self.stdout.write("   → Site preview image: ", ending="")
        preview_images.generate_site_preview_image_task.delay()
        self.stdout.write(" OK 🖼")

        if options["all"]:
            # Users
            users = models.User.objects.filter(
                local=True,
                is_active=True,
            )
            self.stdout.write(
                "   → User preview images ({}): ".format(len(users)), ending=""
            )
            for user in users:
                preview_images.generate_user_preview_image_task.delay(user.id)
                self.stdout.write(".", ending="")
            self.stdout.write(" OK 🖼")

            # Books
            book_ids = (
                models.Book.objects.select_subclasses()
                .filter()
                .values_list("id", flat=True)
            )

            self.stdout.write(
                "   → Book preview images ({}): ".format(len(book_ids)), ending=""
            )
            for book_id in book_ids:
                preview_images.generate_edition_preview_image_task.delay(book_id)
                self.stdout.write(".", ending="")
            self.stdout.write(" OK 🖼")

        self.stdout.write("🧑‍🎨 ⎨ I’m all done! ✧ Enjoy ✧")
