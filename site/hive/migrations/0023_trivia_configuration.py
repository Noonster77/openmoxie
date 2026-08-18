from django.db import migrations, models


QUESTIONS = [
    ('Animals', 'What is a baby kangaroo called?', ['joey'], 'A baby kangaroo can fit inside its mother’s pouch.'),
    ('Animals', 'Which animal is the fastest on land?', ['cheetah'], 'A cheetah can run faster than a car driving through a neighborhood.'),
    ('Animals', 'How many arms does an octopus have?', ['eight', '8'], 'Octopuses have three hearts.'),
    ('Animals', 'What is the largest animal on Earth?', ['blue whale', 'whale'], 'A blue whale’s heart is about the size of a small car.'),
    ('Animals', 'Which bird cannot fly but is an excellent swimmer?', ['penguin'], 'Penguins use their wings like flippers underwater.'),
    ('Science', 'What planet is famous for its rings?', ['saturn'], 'Saturn has thousands of icy ring pieces.'),
    ('Science', 'What force pulls things toward the ground?', ['gravity'], 'Gravity also keeps the Moon moving around Earth.'),
    ('Science', 'What is frozen water called?', ['ice'], 'Water gets bigger when it freezes.'),
    ('Science', 'What gas do people need to breathe?', ['oxygen'], 'Plants help put oxygen into the air.'),
    ('Science', 'Which part of a plant usually grows underground?', ['root', 'roots'], 'Roots drink up water and help hold a plant steady.'),
    ('Math', 'What is twelve plus eight?', ['twenty', '20'], ''),
    ('Math', 'How many sides does a hexagon have?', ['six', '6'], 'The cells in a honeycomb are hexagons.'),
    ('Math', 'What is half of eighteen?', ['nine', '9'], ''),
    ('Math', 'If you have three pairs of socks, how many socks is that?', ['six', '6'], ''),
    ('Math', 'What number comes next: five, ten, fifteen, what?', ['twenty', '20'], ''),
    ('World', 'What is the largest ocean on Earth?', ['pacific', 'pacific ocean'], 'The Pacific Ocean is bigger than all the land on Earth combined.'),
    ('World', 'Which direction is opposite of east?', ['west'], ''),
    ('World', 'What do we call a scientist who studies stars and space?', ['astronomer'], 'Astronomers use light to learn what distant stars are made of.'),
    ('World', 'On which continent would you find Egypt?', ['africa'], 'Egypt is home to pyramids built thousands of years ago.'),
    ('World', 'What imaginary line goes around the middle of Earth?', ['equator'], 'Places near the equator are warm throughout the year.'),
    ('Words', 'What is the opposite of enormous?', ['tiny', 'small', 'little'], ''),
    ('Words', 'Which word rhymes with moon: spoon or sock?', ['spoon'], ''),
    ('Words', 'What do we call a word that means the same as another word?', ['synonym'], 'Big and large are synonyms.'),
    ('Words', 'What punctuation mark goes at the end of a question?', ['question mark'], ''),
    ('Words', 'What is the past tense of run?', ['ran'], ''),
    ('Silly', 'If a purple elephant wore two hats, how many hats would it wear?', ['two', '2'], 'That elephant would be extremely fashionable.'),
    ('Silly', 'Which would be better for soup: a spoon or a shoe?', ['spoon'], 'Shoes are excellent at walking and terrible at soup.'),
    ('Silly', 'If a robot hiccups three times and then twice more, how many hiccups is that?', ['five', '5'], 'Robot hiccups probably sound like beep, boop, burp.'),
    ('Silly', 'Which is more likely to fit in your pocket: a marble or a mountain?', ['marble'], 'A pocket-sized mountain would make hiking very convenient.'),
    ('Silly', 'What would melt first in sunshine: an ice cube or a rock?', ['ice cube', 'ice'], 'Unless it is a chocolate rock. Then all bets are off.'),
]


def seed_questions(apps, schema_editor):
    TriviaQuestion = apps.get_model('hive', 'TriviaQuestion')
    for category, question, answers, fact in QUESTIONS:
        TriviaQuestion.objects.update_or_create(
            question=question,
            defaults={'category': category, 'accepted_answers': answers, 'fun_fact': fact, 'enabled': True},
        )


class Migration(migrations.Migration):
    dependencies = [('hive', '0022_speaker_command_uses_cached_names')]
    operations = [
        migrations.AddField(model_name='moxiedevice', name='trivia_categories', field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name='moxiedevice', name='trivia_question_count', field=models.PositiveSmallIntegerField(default=10)),
        migrations.CreateModel(name='TriviaQuestion', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('category', models.CharField(db_index=True, max_length=60)),
            ('question', models.TextField()),
            ('accepted_answers', models.JSONField(default=list)),
            ('fun_fact', models.TextField(blank=True, default='')),
            ('enabled', models.BooleanField(db_index=True, default=True)),
        ], options={'ordering': ['category', 'question']}),
        migrations.RunPython(seed_questions, migrations.RunPython.noop),
    ]
