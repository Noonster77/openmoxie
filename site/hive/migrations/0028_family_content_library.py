from django.db import migrations


FACT_TRIVIA = {
    'Animals': [
        ('What is a group of lions called?', ['pride'], 'A lion pride is usually made up mostly of related females.'),
        ('Which animal carries its home on its back?', ['snail', 'turtle'], 'A snail grows its shell as its body grows.'),
        ('What is the tallest animal in the world?', ['giraffe'], 'A giraffe can be taller than three grown-ups.'),
        ('Which mammal can truly fly?', ['bat'], 'Bats use sound to help navigate in the dark.'),
        ('What do you call a baby goat?', ['kid'], 'Young goats can stand shortly after birth.'),
        ('Which black-and-white animal eats mostly bamboo?', ['panda', 'giant panda'], 'Giant pandas spend much of the day eating.'),
        ('How many legs does a spider have?', ['eight', '8'], 'Spiders are arachnids, not insects.'),
        ('Which animal is known for changing color to blend in?', ['chameleon'], 'Color can also show a chameleon’s mood.'),
        ('What is a baby frog called?', ['tadpole'], 'Tadpoles grow legs as they become frogs.'),
        ('Which sea animal has a hard shell and walks sideways?', ['crab'], 'Most crabs have ten legs, including their claws.'),
        ('What is the largest land animal?', ['african elephant', 'elephant'], 'An elephant uses its trunk to breathe, smell, drink, and grab.'),
        ('Which bird is known for copying sounds and words?', ['parrot'], 'Some parrots can learn many different sounds.'),
        ('What do caterpillars become?', ['butterflies', 'butterfly', 'moths', 'moth'], 'The change is called metamorphosis.'),
        ('Which animal has black and white stripes?', ['zebra'], 'Every zebra has a unique stripe pattern.'),
        ('What is a female chicken called?', ['hen'], 'A male chicken is called a rooster.'),
        ('Which ocean animal has eight arms and can squirt ink?', ['octopus'], 'An octopus can squeeze through very small spaces.'),
        ('What is a dog’s strongest sense?', ['smell', 'sense of smell'], 'A dog’s nose is far more sensitive than a person’s.'),
        ('Which slow animal hangs upside down in trees?', ['sloth'], 'Sloths spend much of their lives in trees.'),
        ('What kind of animal is a Komodo dragon?', ['lizard'], 'The Komodo dragon is the largest living lizard.'),
        ('Which animal builds dams in rivers?', ['beaver'], 'Beaver dams create ponds that shelter many animals.'),
    ],
    'Science': [
        ('What is the star closest to Earth?', ['sun', 'the sun'], 'Sunlight takes about eight minutes to reach Earth.'),
        ('Which planet is closest to the Sun?', ['mercury'], 'Mercury has the shortest year of any planet.'),
        ('What do we call water that falls from clouds?', ['rain'], 'Rain is part of the water cycle.'),
        ('Which organ pumps blood around your body?', ['heart'], 'A heart is a strong muscle.'),
        ('How many planets orbit our Sun?', ['eight', '8'], 'The planets range from rocky worlds to gas giants.'),
        ('What do magnets attract: plastic or iron?', ['iron'], 'Magnets have a north pole and a south pole.'),
        ('What is melted rock beneath Earth’s surface called?', ['magma'], 'Once it reaches the surface it is called lava.'),
        ('Which state of matter keeps its own shape?', ['solid', 'a solid'], 'Solids have a fixed shape and volume.'),
        ('What tool helps us see very tiny things?', ['microscope'], 'Microscopes can reveal cells and microbes.'),
        ('What do plants use sunlight to make?', ['food', 'energy', 'sugar'], 'That process is called photosynthesis.'),
        ('What is the center of an atom called?', ['nucleus'], 'The nucleus contains protons and neutrons.'),
        ('Which planet is called the Red Planet?', ['mars'], 'Iron minerals make the surface of Mars look reddish.'),
        ('What is water vapor turning into liquid called?', ['condensation'], 'Condensation helps form clouds.'),
        ('Which simple machine is a ramp?', ['inclined plane', 'an inclined plane'], 'An inclined plane helps move objects up or down.'),
        ('What travels faster, light or sound?', ['light'], 'That is why lightning is seen before thunder is heard.'),
        ('What is Earth’s natural satellite?', ['moon', 'the moon'], 'The Moon’s gravity helps cause ocean tides.'),
        ('What part of the body contains the brain?', ['head', 'skull'], 'The skull helps protect the brain.'),
        ('What temperature does water freeze at in Celsius?', ['zero', '0', '0 degrees'], 'Water freezes at zero degrees Celsius.'),
        ('Which gas do plants take in from the air?', ['carbon dioxide'], 'Plants use carbon dioxide during photosynthesis.'),
        ('What are the three common states of matter?', ['solid liquid and gas', 'solid, liquid, and gas', 'solids liquids and gases'], 'Heating and cooling can change matter from one state to another.'),
    ],
    'World': [
        ('What is the largest continent?', ['asia'], 'Asia is home to more than half of the world’s people.'),
        ('What is the capital of France?', ['paris'], 'Paris is located along the River Seine.'),
        ('Which country is shaped like a boot?', ['italy'], 'Italy reaches into the Mediterranean Sea.'),
        ('What is the name of the line at zero degrees longitude?', ['prime meridian', 'the prime meridian'], 'The Prime Meridian passes through Greenwich, England.'),
        ('Which continent is the South Pole on?', ['antarctica'], 'Antarctica is the coldest continent.'),
        ('What is the largest hot desert in the world?', ['sahara', 'sahara desert'], 'The Sahara stretches across northern Africa.'),
        ('Which ocean lies between Africa and Australia?', ['indian ocean', 'indian'], 'The Indian Ocean is the third-largest ocean.'),
        ('What is the capital of Japan?', ['tokyo'], 'Tokyo is one of the world’s largest cities.'),
        ('Which river flows through Egypt?', ['nile', 'nile river'], 'The Nile has supported communities for thousands of years.'),
        ('What are the four main compass directions?', ['north south east and west', 'north, south, east, and west'], 'A compass needle points toward magnetic north.'),
        ('Which country is home to the Great Barrier Reef?', ['australia'], 'The reef is made by tiny animals called coral polyps.'),
        ('What is the capital of Canada?', ['ottawa'], 'Ottawa sits on the Ottawa River.'),
        ('Which continent contains Brazil?', ['south america'], 'Brazil is the largest country in South America.'),
        ('What is the smallest continent?', ['australia'], 'Australia is both a country and a continent.'),
        ('What is land completely surrounded by water called?', ['island', 'an island'], 'A group of islands is called an archipelago.'),
        ('Which country has a maple leaf on its flag?', ['canada'], 'The maple leaf has long been a symbol of Canada.'),
        ('What is the capital of Mexico?', ['mexico city'], 'Mexico City is one of North America’s oldest capitals.'),
        ('Which continent is Kenya in?', ['africa'], 'Kenya lies on the equator in East Africa.'),
        ('What do we call a large body of salt water smaller than an ocean?', ['sea', 'a sea'], 'Many seas connect to an ocean.'),
        ('Which direction does the Sun appear to rise from?', ['east', 'the east'], 'Earth’s rotation makes the Sun appear to rise in the east.'),
    ],
    'Words': [
        ('What is the opposite of begin?', ['end', 'finish'], ''),
        ('What is the plural of mouse?', ['mice'], ''),
        ('Which word rhymes with star: car or cup?', ['car'], ''),
        ('What is the past tense of eat?', ['ate'], ''),
        ('What do we call a person who writes a book?', ['author', 'writer'], ''),
        ('Which punctuation mark shows excitement?', ['exclamation mark', 'exclamation point'], ''),
        ('What is the opposite of noisy?', ['quiet', 'silent'], ''),
        ('How many vowels are in the English alphabet?', ['five', '5'], 'The usual vowels are A, E, I, O, and U.'),
        ('What is the first letter of the word robot?', ['r'], ''),
        ('What is a word that names a person, place, or thing?', ['noun', 'a noun'], ''),
        ('What is the plural of child?', ['children'], ''),
        ('Which word means very happy: joyful or gloomy?', ['joyful'], ''),
        ('What is the opposite of empty?', ['full'], ''),
        ('What do we call the main character in a story?', ['protagonist', 'hero'], ''),
        ('Which word rhymes with light: night or leaf?', ['night'], ''),
        ('What is the past tense of swim?', ['swam'], ''),
        ('What do we call a comparison using like or as?', ['simile', 'a simile'], ''),
        ('Which comes first alphabetically: apple or zebra?', ['apple'], ''),
        ('What is the opposite of ancient?', ['modern', 'new'], ''),
        ('How many syllables are in the word banana?', ['three', '3'], 'Ba-na-na has three syllables.'),
    ],
}


PUN_JOKES = [
    ('Animal antics', 'Why did the cow cross the road?', 'To get to the udder side.'),
    ('Animal antics', 'What do you call a bear with no teeth?', 'A gummy bear.'),
    ('Animal antics', 'What do you call an alligator in a vest?', 'An investigator.'),
    ('Animal antics', 'Why are fish so smart?', 'Because they live in schools.'),
    ('Animal antics', 'What do you call a pig that knows karate?', 'A pork chop.'),
    ('Animal antics', 'Why did the duck get a time-out?', 'It kept using fowl language.'),
    ('Animal antics', 'What do you call a rabbit who tells jokes?', 'A funny bunny.'),
    ('Animal antics', 'What do you call a snail on a ship?', 'A snailor.'),
    ('Animal antics', 'Why do bees have sticky hair?', 'Because they use honeycombs.'),
    ('Animal antics', 'What do you call a sheep covered in chocolate?', 'A candy baa.'),
    ('Food fun', 'Why did the banana go to the doctor?', 'It was not peeling well.'),
    ('Food fun', 'What kind of room has no doors or windows?', 'A mushroom.'),
    ('Food fun', 'Why did the cookie go to the nurse?', 'It felt crummy.'),
    ('Food fun', 'What did one plate say to the other?', 'Dinner is on me.'),
    ('Food fun', 'Why did the orange stop rolling?', 'It ran out of juice.'),
    ('Food fun', 'What is a ghost’s favorite fruit?', 'Boo-berries.'),
    ('Food fun', 'What do you call cheese that is not yours?', 'Nacho cheese.'),
    ('Food fun', 'Why did the tomato blush?', 'It saw the salad dressing.'),
    ('Food fun', 'What does a lemon say when it answers the phone?', 'Yellow!'),
    ('Food fun', 'Why did the melon jump into the lake?', 'It wanted to be a watermelon.'),
    ('School smiles', 'Why was the pencil so calm?', 'It knew how to draw a deep breath.'),
    ('School smiles', 'Why did the music teacher need a ladder?', 'To reach the high notes.'),
    ('School smiles', 'Why was the broom late for school?', 'It over-swept.'),
    ('School smiles', 'What is a math teacher’s favorite dessert?', 'Pi.'),
    ('School smiles', 'Why did the crayon quit arguing?', 'It wanted to draw a line under it.'),
    ('School smiles', 'What did the paper say to the pencil?', 'Write on!'),
    ('School smiles', 'Why did the student bring a flashlight to class?', 'To brighten the subject.'),
    ('School smiles', 'Why was the equal sign so humble?', 'It knew it was no greater than anyone else.'),
    ('School smiles', 'What do librarians take fishing?', 'Bookworms.'),
    ('School smiles', 'Why did the clock get sent to the principal?', 'It kept tocking in class.'),
    ('Robot giggles', 'Why did the robot take a vacation?', 'It needed to recharge.'),
    ('Robot giggles', 'What is a robot’s favorite kind of music?', 'Heavy metal.'),
    ('Robot giggles', 'Why was the robot tired after lunch?', 'It had too many bytes.'),
    ('Robot giggles', 'What do robots wear in winter?', 'Re-boots.'),
    ('Robot giggles', 'Why did the robot visit the bank?', 'To check its cache.'),
    ('Robot giggles', 'How does a robot eat salsa?', 'With microchips.'),
    ('Robot giggles', 'Why did the computer sneeze?', 'It had a virus.'),
    ('Robot giggles', 'What did the robot say to the magnet?', 'I am attracted to you.'),
    ('Robot giggles', 'Why are robots good at road trips?', 'They always follow directions.'),
    ('Robot giggles', 'How did the robot cross the river?', 'In a row-bot.'),
    ('Silly science', 'Why did the sun go to school?', 'To get a little brighter.'),
    ('Silly science', 'What did one volcano say to the other?', 'I lava you.'),
    ('Silly science', 'Why is the moon good at parties?', 'It goes through every phase.'),
    ('Silly science', 'What is an astronaut’s favorite key?', 'The space bar.'),
    ('Silly science', 'Why did the bicycle fall over?', 'It was two-tired.'),
    ('Silly science', 'What did the ocean say to the beach?', 'Nothing. It just waved.'),
    ('Silly science', 'Why can you not give Elsa a balloon?', 'Because she will let it go.'),
    ('Silly science', 'What kind of tree fits in your hand?', 'A palm tree.'),
    ('Silly science', 'Why did the picture go to jail?', 'It was framed.'),
    ('Silly science', 'What did zero say to eight?', 'Nice belt!'),
]


KNOCK_WORDS = [
    ('Lettuce', 'Lettuce in, it is chilly out here!'), ('Boo', 'Do not cry, it is only a joke!'),
    ('Tank', 'You are welcome!'), ('Olive', 'Olive you very much!'), ('Cow says', 'No, a cow says moo!'),
    ('Atch', 'Bless you!'), ('Who', 'Is there an owl in here?'), ('Annie', 'Annie body home?'),
    ('Nobel', 'No bell, so I knocked!'), ('Canoe', 'Canoe come out and play?'),
    ('Dishes', 'Dishes the police, open up!'), ('Needle', 'Needle little help opening the door.'),
    ('Wooden shoe', 'Wooden shoe like to hear another joke?'), ('Butter', 'Butter open up, it is cold!'),
    ('Ice cream', 'Ice cream if you do not let me in!'), ('A little old lady', 'I did not know you could yodel!'),
    ('Harry', 'Harry up and answer the door!'), ('Radio', 'Radio not, here I come!'),
    ('Justin', 'Justin time for dinner!'), ('Orange', 'Orange you glad I knocked?'),
    ('Alpaca', 'Alpaca the snacks, you bring the juice!'), ('Luke', 'Luke through the window and see!'),
    ('Ya', 'Yahoo! I am happy to see you!'), ('Figs', 'Figs the doorbell, it is broken!'),
    ('Robin', 'Robin you! Hand over the cookies!'), ('Spell', 'W-H-O.'),
    ('A broken pencil', 'Never mind, it is pointless.'), ('Water', 'Water you waiting for? Let me in!'),
    ('Howard', 'Howard you like another joke?'), ('Honey bee', 'Honey bee a dear and open the door?'),
    ('Donut', 'Donut forget to smile today!'), ('Snow', 'Snow use, I forgot my name!'),
    ('Cargo', 'Car go beep beep!'), ('Interrupting cow', 'MOO!'),
    ('Mikey', 'Mikey will not fit, please open the door!'), ('Peas', 'Peas let me come inside!'),
    ('Avenue', 'Avenue heard this joke before?'), ('Banana', 'Banana split, so I came over!'),
    ('Weekend', 'Weekend do anything if we work together!'), ('Etch', 'Bless you again!'),
    ('Ken', 'Ken I come in?'), ('Teddy', 'Teddy is not a person, it is a bear!'),
    ('Wanda', 'Wanda go outside and play?'), ('Gorilla', 'Gorilla me a sandwich, please!'),
    ('Hatch', 'Bless you! That was a big sneeze.'), ('Adore', 'Adore is between us. Please open it!'),
    ('A herd', 'A herd you were home!'), ('Ketchup', 'Ketchup with me and I will tell you!'),
    ('Amos', 'A mosquito just bit me!'), ('Europe', 'No, you are a person!'),
]


def seed_library(apps, schema_editor):
    TriviaQuestion = apps.get_model('hive', 'TriviaQuestion')
    Joke = apps.get_model('hive', 'Joke')

    questions = []
    for number in range(1, 41):
        questions.append(('Math', f'What is {number} plus {number + 3}?', [str(number * 2 + 3)], ''))
    for number in range(1, 31):
        left, right = number + 12, number % 8 + 2
        questions.append(('Math', f'What is {left} minus {right}?', [str(left - right)], ''))
    for number in range(30):
        left, right = number % 10 + 2, number // 10 + 3
        questions.append(('Math', f'What is {left} times {right}?', [str(left * right)], ''))
    for number in range(20):
        divisor, answer = number % 8 + 2, number % 9 + 2
        questions.append(('Math', f'What is {divisor * answer} divided by {divisor}?', [str(answer)], ''))
    for category, items in FACT_TRIVIA.items():
        questions.extend((category, question, answers, fact) for question, answers, fact in items)

    for category, question, answers, fact in questions:
        TriviaQuestion.objects.get_or_create(
            question=question,
            defaults={'category': category, 'accepted_answers': answers, 'fun_fact': fact, 'enabled': True},
        )

    for collection, setup, punchline in PUN_JOKES:
        Joke.objects.get_or_create(
            setup=setup,
            defaults={'collection': collection, 'punchline': punchline, 'enabled': True},
        )
    for word, punchline in KNOCK_WORDS:
        setup = f'Knock, knock! Who is there? {word}. {word} who?'
        Joke.objects.get_or_create(
            setup=setup,
            defaults={'collection': 'Knock-knock', 'punchline': punchline, 'enabled': True},
        )


class Migration(migrations.Migration):
    dependencies = [('hive', '0027_alpha_parent_tools')]
    operations = [migrations.RunPython(seed_library, migrations.RunPython.noop)]
