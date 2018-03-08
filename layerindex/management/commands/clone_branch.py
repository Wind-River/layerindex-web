"""Clone a branch
Django does not support cloning directly but documents the best way to do it:
https://docs.djangoproject.com/en/1.8/topics/db/queries/#copying-model-instances
"""

from django.core.management.base import BaseCommand, CommandError
from layerindex.models import Branch

class Command(BaseCommand):
    help = 'Clone an existing branch and give it a new name'

    def add_arguments(self, parser):
        parser.add_argument('--branch', action='store', dest='branch',
                            required=True, help='The branch to clone')
        parser.add_argument('--bitbake_branch', action='store', dest='bitbake_branch',
                            required=False, help='The branch to clone')
        parser.add_argument('--name', action='store', dest='name',
                            required=True, help='The name of the cloned branch')
        parser.add_argument('--description', action='store', dest='description',
                            required=True, help='The description of the cloned branch')

    def handle(self, *args, **options):
        branch = Branch.objects.get(name=options['branch'])
        branch.name = options['name']
        branch.short_description = options['description']

        # By default the bitbake branch will match the branch name
        branch.bitbake_branch = options.get('bitbake_branch')
        if branch.bitbake_branch is None:
            branch.bitbake_branch = options['name']

        # Setting primary key to none will give the clone a new pk on save
        branch.pk = None
        branch.save()
