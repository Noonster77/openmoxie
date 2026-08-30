from django.db import migrations, models
import hive.models


CATEGORIES = ['Animals', 'Math', 'Science', 'Silly', 'Words', 'World']
COLLECTIONS = ['Animal antics', 'Food fun', 'Knock-knock', 'Robot giggles', 'School smiles', 'Silly science']


ANIMAL_FACTS = [
    ('blue whale', 'is the largest animal known to have lived', 'A blue whale can be longer than a basketball court.'),
    ('peregrine falcon', 'is the fastest animal during its hunting dive', 'A diving peregrine falcon can exceed 200 miles per hour.'),
    ('cheetah', 'is the fastest land animal', 'A cheetah uses its tail to help steer while sprinting.'),
    ('ostrich', 'is the largest living bird', 'An ostrich cannot fly, but it can run very quickly.'),
    ('giant panda', 'eats bamboo as most of its diet', 'Giant pandas have a wrist bone that works like a thumb.'),
    ('beaver', 'builds dams from branches and mud', 'Beaver dams create wetland habitat for many species.'),
    ('octopus', 'has three hearts and eight arms', 'Two octopus hearts pump blood to the gills.'),
    ('giraffe', 'is the tallest living land animal', 'A giraffe has seven neck bones, the same number as a person.'),
    ('hummingbird', 'can hover and fly backward', 'Hummingbird wings beat in a figure-eight pattern while hovering.'),
    ('bat', 'is the only mammal capable of sustained flight', 'Bat wings are supported by elongated finger bones.'),
    ('emperor penguin', 'is the largest living penguin', 'Emperor penguin parents take turns caring for their chick.'),
    ('axolotl', 'can regrow lost limbs', 'Axolotls keep larval features such as external gills as adults.'),
    ('camel', 'stores fat, not water, in its hump', 'Stored fat helps a camel survive when food is scarce.'),
    ('spider', 'has eight legs and is an arachnid', 'Spiders have two main body sections.'),
    ('honeybee', 'communicates food locations with a waggle dance', 'The dance conveys direction and distance.'),
    ('sea otter', 'often uses a rock as a tool to open shellfish', 'Sea otters may keep a favorite rock in a pouch.'),
    ('chameleon', 'can move its eyes independently', 'A chameleon can watch two directions at once.'),
    ('dolphin', 'breathes air through a blowhole', 'Dolphins are mammals and must surface to breathe.'),
    ('kangaroo', 'carries its young in a pouch', 'A baby kangaroo is called a joey.'),
    ('platypus', 'is an egg-laying mammal with a duck-like bill', 'Platypuses are native to eastern Australia and Tasmania.'),
    ('sloth', 'spends much of its life hanging in trees', 'Long curved claws help a sloth grip branches.'),
    ('electric eel', 'can produce strong electric discharges', 'Electric eels are a kind of knifefish, not true eels.'),
    ('narwhal', 'usually has one long spiral tusk', 'The tusk is an enlarged tooth.'),
    ('leafcutter ant', 'grows fungus using pieces of leaves', 'Leafcutter ants eat the fungus they cultivate.'),
    ('woodpecker', 'uses a strong bill to drill into wood', 'A woodpecker can use drumming to communicate.'),
]


SCIENCE_FACTS = [
    ('gravity', 'pulls objects toward Earth', 'Gravity gives objects weight near Earth.'),
    ('photosynthesis', 'lets plants use light to make sugar', 'Photosynthesis also releases oxygen.'),
    ('evaporation', 'changes liquid water into water vapor', 'Evaporation is part of the water cycle.'),
    ('condensation', 'changes water vapor into liquid water', 'Condensation helps form clouds and dew.'),
    ('oxygen', 'is the gas people need for cellular respiration', 'Oxygen makes up about 21 percent of Earth’s atmosphere.'),
    ('carbon dioxide', 'is the gas plants take in for photosynthesis', 'Carbon dioxide contains one carbon atom and two oxygen atoms.'),
    ('nucleus', 'is the central part of an atom containing protons and neutrons', 'Electrons occupy regions around the nucleus.'),
    ('electron', 'is the negatively charged subatomic particle', 'Electrons are much less massive than protons.'),
    ('friction', 'resists motion between touching surfaces', 'Friction lets shoes grip the ground.'),
    ('inertia', 'describes an object resisting a change in motion', 'Inertia is part of Newton’s first law of motion.'),
    ('Mars', 'is the planet called the Red Planet', 'Iron minerals give Mars its rusty color.'),
    ('Jupiter', 'is the largest planet in our solar system', 'Jupiter is a gas giant.'),
    ('Mercury', 'is the planet closest to the Sun', 'Mercury completes an orbit in about 88 Earth days.'),
    ('Venus', 'is the hottest planet in our solar system', 'A thick carbon-dioxide atmosphere traps heat on Venus.'),
    ('Neptune', 'is the farthest major planet from the Sun', 'Neptune takes about 165 Earth years to orbit the Sun.'),
    ('Moon', 'is Earth’s natural satellite', 'The Moon’s gravity helps produce ocean tides.'),
    ('light', 'travels faster than sound', 'Lightning is seen before its thunder is heard.'),
    ('solid', 'has a fixed shape and fixed volume', 'Particles in a solid vibrate around fixed positions.'),
    ('liquid', 'has a fixed volume but takes its container’s shape', 'Liquid particles can move past one another.'),
    ('gas', 'expands to fill its container', 'Gas particles are widely spaced compared with a liquid.'),
    ('heart', 'pumps blood through the body', 'The human heart has four chambers.'),
    ('lungs', 'move oxygen into the blood and remove carbon dioxide', 'Tiny air sacs in lungs are called alveoli.'),
    ('skeleton', 'supports the body and protects organs', 'An adult human skeleton usually has 206 bones.'),
    ('microscope', 'makes very small objects easier to see', 'Compound light microscopes use more than one lens.'),
    ('thermometer', 'measures temperature', 'Digital thermometers use electronic sensors.'),
]


WORLD_FACTS = [
    ('France', 'Paris'), ('Japan', 'Tokyo'), ('Canada', 'Ottawa'), ('Mexico', 'Mexico City'),
    ('Brazil', 'Brasília'), ('Australia', 'Canberra'), ('New Zealand', 'Wellington'), ('Italy', 'Rome'),
    ('Spain', 'Madrid'), ('Portugal', 'Lisbon'), ('Ireland', 'Dublin'), ('Norway', 'Oslo'),
    ('Sweden', 'Stockholm'), ('Finland', 'Helsinki'), ('Denmark', 'Copenhagen'), ('Iceland', 'Reykjavík'),
    ('Greece', 'Athens'), ('Egypt', 'Cairo'), ('Kenya', 'Nairobi'), ('Morocco', 'Rabat'),
    ('India', 'New Delhi'), ('South Korea', 'Seoul'), ('Thailand', 'Bangkok'), ('Argentina', 'Buenos Aires'),
    ('Chile', 'Santiago'),
]


WORD_FACTS = [
    ('mice', 'the plural of mouse', 'Mouse has an irregular plural.'),
    ('children', 'the plural of child', 'Child has an irregular plural.'),
    ('geese', 'the plural of goose', 'Goose changes its vowel in the plural.'),
    ('teeth', 'the plural of tooth', 'Tooth has an irregular plural.'),
    ('feet', 'the plural of foot', 'Foot has an irregular plural.'),
    ('ran', 'the past tense of run', 'Run is an irregular verb.'),
    ('ate', 'the past tense of eat', 'Eat is an irregular verb.'),
    ('wrote', 'the past tense of write', 'Write is an irregular verb.'),
    ('sang', 'the past tense of sing', 'Sing is an irregular verb.'),
    ('swam', 'the past tense of swim', 'Swim is an irregular verb.'),
    ('noun', 'a word naming a person, place, thing, or idea', 'A proper noun names a particular person, place, or thing.'),
    ('verb', 'a word expressing an action or state', 'A sentence usually needs a verb.'),
    ('adjective', 'a word that describes a noun', 'Adjectives can describe qualities such as size or color.'),
    ('adverb', 'a word that often describes a verb, adjective, or another adverb', 'Many, but not all, adverbs end in L Y.'),
    ('synonym', 'a word with the same or nearly the same meaning as another', 'Big and large are synonyms in many contexts.'),
    ('antonym', 'a word with an opposite meaning', 'Hot and cold are antonyms.'),
    ('simile', 'a comparison using like or as', 'A simile says one thing is like another.'),
    ('metaphor', 'a comparison that says one thing is another', 'Metaphors are not meant literally.'),
    ('author', 'a person who writes a book or other work', 'An author can write fiction or nonfiction.'),
    ('paragraph', 'a group of related sentences', 'A new paragraph usually begins on a new line.'),
    ('question mark', 'the punctuation placed after a direct question', 'A question mark looks like a curved hook over a dot.'),
    ('apostrophe', 'the mark used in contractions such as can’t', 'An apostrophe can also show possession.'),
    ('alphabetical order', 'an arrangement following the order of letters', 'Dictionaries place words in alphabetical order.'),
    ('homophone', 'a word that sounds like another word but differs in meaning', 'Sea and see are homophones.'),
    ('syllable', 'a spoken word part built around a vowel sound', 'Banana has three syllables.'),
]


SILLY_RIDDLES = [
    ('a towel', 'gets wetter while it dries you', 'A towel absorbs water as it dries something else.'),
    ('a clock', 'has hands and a face but no arms or eyes', 'Clock hands point to the time.'),
    ('a bottle', 'has a neck but no head', 'The narrow upper part of a bottle is called its neck.'),
    ('a piano', 'has keys but cannot open a lock', 'Pressing piano keys makes hammers strike strings.'),
    ('a river', 'runs but never walks', 'River water flows downhill under gravity.'),
    ('a needle', 'has an eye but cannot see', 'Thread passes through the eye of a sewing needle.'),
    ('a shoe', 'has a tongue but cannot taste', 'A shoe tongue sits beneath its laces.'),
    ('a comb', 'has teeth but cannot bite', 'Comb teeth separate and arrange strands of hair.'),
    ('a mushroom', 'is a room with no doors or windows in a classic pun', 'The word mushroom ends with the sound of room.'),
    ('an egg', 'must be broken before it can be used for cooking', 'Cracking opens an eggshell.'),
    ('a shadow', 'follows you in light but makes no sound', 'A shadow forms when an object blocks light.'),
    ('a map', 'can show cities without houses and rivers without water', 'A map uses symbols to represent places.'),
    ('a stamp', 'travels around the world while staying on an envelope', 'Postage stamps show that mailing fees were paid.'),
    ('a keyboard', 'has a space bar but serves no drinks', 'The space bar inserts a blank space.'),
    ('a candle', 'becomes shorter as it works', 'Candle wax is consumed as the wick burns.'),
    ('a sponge', 'is full of holes but can hold water', 'A sponge’s pores trap water.'),
    ('an umbrella', 'goes up when the rain comes down', 'An open umbrella redirects falling rain.'),
    ('your age', 'goes up and never comes down', 'Age increases as time passes.'),
    ('a secret', 'is harder to keep after you share it', 'Sharing information means more people know it.'),
    ('silence', 'is broken when you say its name', 'Speaking creates sound, ending silence.'),
    ('a cold', 'can be caught but not thrown', 'Catch a cold is an idiom for becoming sick.'),
    ('a joke', 'can crack people up without making a crack', 'Crack up can mean laugh hard.'),
    ('a calendar', 'has many dates but never goes to dinner', 'A calendar date is a day, not a social outing.'),
    ('a book', 'has a spine but no bones', 'The spine is the bound edge of a book.'),
    ('a ruler', 'can measure a foot but has no toes', 'A foot is also a unit equal to twelve inches.'),
]


EXTRA_JOKES = [
    ('Animal antics', 'Why did the owl invite friends over?', 'It did not want to be owl by itself.'),
    ('Animal antics', 'What do frogs order with lunch?', 'French flies.'),
    ('Animal antics', 'Why was the cat a good musician?', 'It had perfect purr-cussion.'),
    ('Animal antics', 'What do you call a sleeping bull?', 'A bulldozer.'),
    ('Animal antics', 'Why did the turtle cross the playground?', 'To get to the other slide.'),
    ('Animal antics', 'What is a snake’s favorite subject?', 'Hiss-tory.'),
    ('Animal antics', 'Why did the pony whisper?', 'It was a little hoarse.'),
    ('Animal antics', 'What kind of dog loves taking a bath?', 'A shampoo-dle.'),
    ('Food fun', 'Why did the grape stop in the road?', 'It ran out of juice.'),
    ('Food fun', 'What do you call a sad strawberry?', 'A blueberry.'),
    ('Food fun', 'Why did the bread apply for a job?', 'It needed to earn some dough.'),
    ('Food fun', 'What kind of music do balloons dislike?', 'Pop music.'),
    ('Food fun', 'Why was the cupcake good at school?', 'It was a smartie.'),
    ('Food fun', 'What did the baby corn ask the parent corn?', 'Where is pop corn?'),
    ('Food fun', 'Why did the egg hide?', 'It was a little chicken.'),
    ('Food fun', 'What do you call pasta that tells jokes?', 'A silly-ghetti.'),
    ('Robot giggles', 'Why did the robot sit in the shade?', 'It needed to cool its processors.'),
    ('Robot giggles', 'What is a robot’s favorite snack?', 'Computer chips.'),
    ('Robot giggles', 'Why did the robot bring a pencil?', 'It wanted to draw a conclusion.'),
    ('Robot giggles', 'How does a robot say goodbye?', 'It waves its data.'),
    ('Robot giggles', 'Why was the robot good at hide-and-seek?', 'It knew every byte-sized hiding place.'),
    ('Robot giggles', 'What game do robots play at recess?', 'Tag, you are I T.'),
    ('Robot giggles', 'Why did the robot read the dictionary?', 'It wanted better word processing.'),
    ('Robot giggles', 'What did one battery say to the other?', 'I feel positively charged.'),
    ('School smiles', 'Why did the notebook look confident?', 'It had all the right lines.'),
    ('School smiles', 'Why was the math book worried?', 'It had too many problems.'),
    ('School smiles', 'Why did the ruler get promoted?', 'It always measured up.'),
    ('School smiles', 'What is a teacher’s favorite nation?', 'Expla-nation.'),
    ('School smiles', 'Why did the eraser feel useful?', 'It made mistakes disappear.'),
    ('School smiles', 'Why was the history book so relaxed?', 'Its problems were all in the past.'),
    ('School smiles', 'What did the calculator say to the student?', 'You can count on me.'),
    ('School smiles', 'Why did the globe get invited everywhere?', 'It was well-rounded.'),
    ('Silly science', 'Why did the atom cross the road?', 'It wanted to bond with the other side.'),
    ('Silly science', 'Why are chemists good at solving problems?', 'They have all the solutions.'),
    ('Silly science', 'What did the thermometer say during summer?', 'I need a degree of shade.'),
    ('Silly science', 'Why did gravity get invited to the party?', 'It brought everyone together.'),
    ('Silly science', 'Why did the cell bring a suitcase?', 'It was ready to divide and travel.'),
    ('Silly science', 'What is a physicist’s favorite season?', 'Spring, because it has potential energy.'),
    ('Silly science', 'Why was the moon short on money?', 'It was down to its last quarter.'),
    ('Silly science', 'What did Earth say after a long day?', 'I need to unwind and rotate.'),
]


def _fact_questions(category, rows):
    templates = [
        'Which answer {clue}?', 'Can you name what {clue}?',
        'What is known because it {clue}?', 'Think carefully: what {clue}?',
    ]
    for answer, clue, fact in rows:
        accepted = [answer.lower()]
        article_free = answer.lower().removeprefix('a ').removeprefix('an ').removeprefix('the ')
        if article_free != answer.lower():
            accepted.append(article_free)
        for template in templates:
            yield category, template.format(clue=clue), accepted, fact


def seed_overhaul(apps, schema_editor):
    Device = apps.get_model('hive', 'MoxieDevice')
    Question = apps.get_model('hive', 'TriviaQuestion')
    Joke = apps.get_model('hive', 'Joke')
    Chat = apps.get_model('hive', 'SinglePromptChat')
    Response = apps.get_model('hive', 'GlobalResponse')

    # Blank means use the provider/model selected in Setup. Administrators can
    # then set a real per-conversation override without legacy defaults silently
    # defeating LM Studio or OpenRouter configuration.
    Chat.objects.filter(model__in=['gpt-3.5-turbo', 'gpt-4o-mini']).update(model='')

    for device in Device.objects.all():
        if not device.trivia_categories:
            device.trivia_categories = CATEGORIES
        device.joke_collections = (device.robot_config or {}).get('joke_collections') or COLLECTIONS
        device.save(update_fields=['trivia_categories', 'joke_collections'])

    questions = []
    questions.extend(_fact_questions('Animals', ANIMAL_FACTS))
    questions.extend(_fact_questions('Science', SCIENCE_FACTS))
    questions.extend(_fact_questions('Words', WORD_FACTS))
    questions.extend(_fact_questions('Silly', SILLY_RIDDLES))
    for country, capital in WORLD_FACTS:
        fact = f'{capital} is the capital of {country}.'
        answers = [capital.lower()]
        ascii_answer = capital.lower().replace('í', 'i').replace('á', 'a')
        if ascii_answer not in answers:
            answers.append(ascii_answer)
        questions.extend([
            ('World', f'What is the capital of {country}?', answers, fact),
            ('World', f'Name the city that serves as the capital of {country}.', answers, fact),
            ('World', f'Which capital city belongs to {country}?', answers, fact),
            ('World', f'Travel trivia: {country} has which capital?', answers, fact),
        ])
    for number in range(100):
        left = 12 + number
        right = number % 12 + 2
        if number % 4 == 0:
            question, answer = f'Bonus math {number + 1}: What is {left} plus {right}?', left + right
        elif number % 4 == 1:
            question, answer = f'Bonus math {number + 1}: What is {left} minus {right}?', left - right
        elif number % 4 == 2:
            question, answer = f'Bonus math {number + 1}: What is {right} times {number % 9 + 2}?', right * (number % 9 + 2)
        else:
            answer = number % 10 + 2
            question = f'Bonus math {number + 1}: What is {right * answer} divided by {right}?'
        questions.append(('Math', question, [str(answer)], f'The answer is {answer}.'))
    for category, question, answers, fact in questions:
        Question.objects.get_or_create(
            question=question,
            defaults={'category': category, 'accepted_answers': answers, 'fun_fact': fact, 'enabled': True},
        )
    for collection, setup, punchline in EXTRA_JOKES:
        Joke.objects.get_or_create(
            setup=setup,
            defaults={'collection': collection, 'punchline': punchline, 'enabled': True},
        )

    Chat.objects.update_or_create(
        module_id='OPENMOXIE_REASONING', content_id='default',
        defaults={
            'name': 'OpenMoxie Reasoning Mode', 'source_version': 1,
            'model': '', 'max_history': 20, 'max_volleys': 9999,
            'max_tokens': 1200, 'temperature': 0.2, 'question_probability': 0.0,
            'prompt': (
                'You are Moxie in careful reasoning mode. Solve the user’s complex question accurately. '
                'Think through assumptions and calculations before answering, but do not reveal hidden chain-of-thought. '
                'Give a clear spoken summary of the answer and the key reasons. Say when information is uncertain.'
            ),
            'opener': 'Reasoning mode is ready. Ask me a complex question. I may take a couple of minutes to think carefully.',
        },
    )
    Response.objects.update_or_create(
        name='Start Reasoning Mode',
        defaults={
            'pattern': r'^(?:(?:moxie|moxy|foxy|boxy|oxy)[, ]+)?(?:please )?(?:(?:start|open|turn on|use|enter)(?: careful)? reasoning(?: mode)?|reasoning mode)[.!]?$',
            'action': 2, 'response_text': 'Reasoning mode is ready. Ask me a complex question.',
            'module_id': 'OPENMOXIE_REASONING', 'content_id': 'default',
            'sort_key': 110, 'source_version': 1,
        },
    )


class Migration(migrations.Migration):
    dependencies = [('hive', '0031_restore_fast_homework_responses')]
    operations = [
        migrations.AlterField(
            model_name='singlepromptchat', name='model',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='hiveconfiguration', name='chat_api_key',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='moxiedevice', name='trivia_categories',
            field=models.JSONField(blank=True, default=hive.models.default_trivia_categories),
        ),
        migrations.AddField(
            model_name='moxiedevice', name='joke_collections',
            field=models.JSONField(blank=True, default=hive.models.default_joke_collections),
        ),
        migrations.AddField(
            model_name='moxiedevice', name='reasoning_effort',
            field=models.CharField(default='high', max_length=20),
        ),
        migrations.AddField(
            model_name='moxiedevice', name='reasoning_max_tokens',
            field=models.PositiveIntegerField(default=1200),
        ),
        migrations.AddField(
            model_name='moxiedevice', name='reasoning_interludes',
            field=models.CharField(default='mixed', max_length=20),
        ),
        migrations.AddField(
            model_name='moxiedevice', name='reasoning_model',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.RunPython(seed_overhaul, migrations.RunPython.noop),
    ]
